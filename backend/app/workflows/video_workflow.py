"""VideoWorkflow:为分镜生成动态视频片段。

固定步骤(每个镜头):
1. 读取镜头规划(shot_state.desired_mode / ref_asset_ids / desired_duration)
2. 汇总参考素材(用户上传参考图 + 角色参考图资产)
3. ShotRouter 逐镜头决策生成模式(t2v / i2v / r2v / first_last)
4. 按决策组装 ModelRequest(image_path 可空 → 放开 T2V 路径),调用 VideoModelProvider
5. 失败时交 FailureAnalysisAgent 决策修复动作(add_keyframe/retry/switch_model),
   按决策执行固定修复步骤后重试(限次);无修复路径则抛错升级
6. 写回 shot.video_path / state.assets,登记 asset_state 与 generation_state 决策台账

模式/模型的"选择"与"失败怎么修"是决策(Agent/Router),本 Workflow 只执行固定步骤。
"""
from __future__ import annotations

import os
from typing import Awaitable, Callable, Optional

from ..core.config import storage_dir
from ..core.exceptions import ProviderError
from ..core.logging import logger
from ..director.project_state import AssetEntry, GenerationDecision
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.video.base import ModelRequest, VideoModelProvider
from ..router.shot_router import decide_video_mode
from .base import BaseWorkflow

# 模型切换回调签名:返回 True=已切到新厂商,False=无备选厂商
ModelSwitcher = Callable[[VideoGenerationState, int, str], Awaitable[bool]]


class VideoWorkflow(BaseWorkflow):
    name = "video_workflow"

    def __init__(
        self,
        video: VideoModelProvider,
        *,
        failure_analyzer=None,
        image_workflow=None,
        model_switcher: Optional[ModelSwitcher] = None,
    ) -> None:
        self.video = video
        self.failure_analyzer = failure_analyzer  # FailureAnalysisAgent(决策层)
        self.image_workflow = image_workflow      # 用于 add_keyframe 修复动作
        self.model_switcher = model_switcher      # orchestrator 提供的切厂商回调

    async def run(self, state: VideoGenerationState) -> None:
        if state.storyboard is None:
            raise RuntimeError("VideoWorkflow 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        ps.generation_state.current_stage = "video"

        shots = state.storyboard.shots
        n_shots = len(shots)
        user_refs = self._user_reference_paths(state)
        if user_refs:
            logger.info("R2V 参考素材: %d 张用户参考图可注入视频生成", len(user_refs))

        total_duration = 0
        for i, shot in enumerate(shots):
            await self.generate_shot(state, i, user_reference_paths=user_refs)
            total_duration += shot.duration

        # 末尾镜头补齐目标时长(时间轴层面;实际片段时长由模型能力决定)
        target = state.duration or total_duration
        if total_duration < target and shots:
            shots[-1].duration = max(shots[-1].duration + (target - total_duration), 2)
            logger.info("末尾镜头补齐时长至 %ds(目标成片 %ds)", shots[-1].duration, target)

        n_clips = sum(1 for s in shots if s.video_path)
        logger.info("视频片段生成完成: %d/%d 镜, 时间轴总时长 %ds", n_clips, n_shots, target)

    async def generate_shot(
        self,
        state: VideoGenerationState,
        shot_index: int,
        *,
        user_reference_paths: list[str] | None = None,
    ) -> None:
        """生成(或重新生成)单个镜头的动态片段。

        失败修复闭环:Provider 报错 → FailureAnalysisAgent 决策 → 执行修复动作 → 重试,
        直到成功或决策 abort(无自动修复路径,抛错升级到阶段失败处理)。
        局部重生成/质检修复均复用此入口,自动获得同一套闭环。
        """
        assert state.storyboard is not None
        user_refs = user_reference_paths if user_reference_paths is not None else self._user_reference_paths(state)
        ps = state.get_or_create_project_state()

        while True:
            latest = ps.generation_state.latest_decision(shot_index)
            attempt = (latest.attempt + 1) if latest is not None else 1
            try:
                await self._attempt_generation(state, shot_index, attempt, user_refs)
                return
            except ProviderError as e:
                mode_before = latest.mode if latest else (ps.shot_state.get(shot_index).desired_mode if ps.shot_state.get(shot_index) else "")
                if self.failure_analyzer is None:
                    self._record_failure(ps, shot_index, attempt, mode_before, e)
                    raise
                decision = self.failure_analyzer.analyze_generation_failure(
                    shot_index=shot_index,
                    error_code=e.error_code,
                    error_message=getattr(e, "message", str(e)),
                    mode=getattr(e, "_video_mode", mode_before),
                    provider=getattr(e, "provider", getattr(self.video, "name", "video")),
                    attempt=attempt,
                )
                self._record_failure(ps, shot_index, attempt, mode_before, e, repair=decision.action)
                logger.warning(
                    "shot%d 第 %d 次生成失败(%s): %s",
                    shot_index, attempt, e.error_code, decision.reason,
                )
                if decision.should_abort or not decision.repairable:
                    raise
                handled = await self._execute_repair(state, shot_index, decision, user_refs)
                if not handled:
                    # 修复动作无可用资源(如无备选厂商):升级失败
                    raise

    async def _attempt_generation(
        self,
        state: VideoGenerationState,
        shot_index: int,
        attempt: int,
        user_reference_paths: list[str],
    ) -> None:
        """单次生成尝试:模式决策 + 调用 Provider + 台账(不含重试逻辑)。"""
        shots = state.storyboard.shots
        shot = shots[shot_index]
        n_shots = len(shots)
        ps = state.get_or_create_project_state()
        shot_entry = ps.shot_state.get(shot_index)

        desired_mode = (shot_entry.desired_mode if shot_entry else "") or shot.desired_mode
        desired_duration = shot_entry.desired_duration if shot_entry else (shot.duration or 5)

        # ---- 素材就位情况 ----
        has_first_frame = bool(shot.image_path) and os.path.exists(shot.image_path)
        next_shot = shots[shot_index + 1] if shot_index + 1 < n_shots else None
        last_frame = (
            next_shot.image_path
            if next_shot is not None and next_shot.image_path
            and os.path.exists(next_shot.image_path)
            else None
        )
        references = self._collect_references(state, shot_index, user_reference_paths)

        # ---- 逐镜头模式决策(确定性、可审计) ----
        caps = self.video.capabilities
        decision = decide_video_mode(
            desired_mode=desired_mode,
            has_first_frame=has_first_frame,
            has_last_frame=bool(last_frame),
            has_references=bool(references),
            caps=caps,
        )
        if not decision.feasible:
            err = ProviderError(
                "video",
                f"镜头 {shot_index+1} 无法生成: {decision.reason}",
                error_code="MODE_UNSUPPORTED",
            )
            setattr(err, "_video_mode", desired_mode)
            raise err

        duration = max(1, min(int(desired_duration or 5), caps.max_duration))
        clips_dir = storage_dir("clips")
        clip_path = os.path.join(str(clips_dir), f"{state.task_id}_shot{shot_index}.mp4")

        state.append_log(
            TaskStatus.GENERATING_ASSETS,
            f"正在生成第 {shot_index+1}/{n_shots} 个镜头动态片段({decision.mode.upper()}, 第{attempt}次)",
        )
        logger.info(
            "shot%d 模式决策: mode=%s first=%s last=%s refs=%d attempt=%d — %s",
            shot_index, decision.mode, decision.use_first_frame,
            decision.use_last_frame, len(references), attempt, decision.reason,
        )

        try:
            resp = await self.video.generate(ModelRequest(
                image_path=shot.image_path if decision.use_first_frame else None,
                prompt=shot.video_prompt or shot.image_prompt,
                save_path=clip_path,
                duration=duration,
                aspect_ratio=state.aspect_ratio or "9:16",
                last_frame_path=last_frame if decision.use_last_frame else None,
                reference_paths=references if decision.use_references else None,
            ))
        except ProviderError as e:
            setattr(e, "_video_mode", decision.mode)
            raise

        shot.video_path = resp.video_path
        state.model_used = resp.model
        if clip_path not in state.assets:
            state.assets.append(clip_path)

        # ---- 台账:决策记录 + 资产登记 + 进度 ----
        ps.generation_state.record_decision(GenerationDecision(
            shot_index=shot_index,
            provider=getattr(self.video, "name", "video"),
            model=resp.model,
            mode=decision.mode,
            reference_asset_ids=[a for a in (shot_entry.ref_asset_ids if shot_entry else [])],
            attempt=attempt,
            reason=decision.reason,
            status="succeeded",
        ))
        ps.generation_state.mark_shot(shot_index, ok=True)
        ps.asset_state.add(AssetEntry(
            asset_id=f"{state.task_id}_clip_{shot_index}",
            type="video",
            path=resp.video_path,
            shot_index=shot_index,
            source_provider=resp.model,
            metadata={"mode": decision.mode, "duration": str(resp.duration), "attempt": str(attempt)},
        ))
        if shot_entry is not None:
            shot_entry.status = "generated"
        ps.touch()
        logger.info("shot%d 动态片段生成成功(mode=%s, %ds, attempt=%d): %s",
                    shot_index, decision.mode, resp.duration, attempt, resp.video_path)

    async def _execute_repair(
        self, state: VideoGenerationState, shot_index: int, decision, user_refs: list[str],
    ) -> bool:
        """执行 FailureAnalysisAgent 决策的修复动作(固定步骤)。返回是否可重试。"""
        from ..agents.failure_analysis_agent import (
            ACTION_ADD_KEYFRAME, ACTION_REGENERATE_PROMPT, ACTION_RETRY, ACTION_SWITCH_MODEL,
        )

        if decision.action == ACTION_RETRY:
            return True  # 直接重试,下一轮 while 自动进行

        if decision.action == ACTION_ADD_KEYFRAME:
            if self.image_workflow is None:
                logger.warning("shot%d 决策为 add_keyframe 但未注入 ImageWorkflow", shot_index)
                return False
            state.append_log(TaskStatus.GENERATING_ASSETS, f"自动修复:补生成镜头 {shot_index+1} 关键帧后重试")
            await self.image_workflow.generate_shot(state, shot_index)
            if decision.force_mode:
                self._force_shot_mode(state, shot_index, decision.force_mode)
            return True

        if decision.action == ACTION_REGENERATE_PROMPT:
            # 内容修复:强制参考图模式(若有参考素材)并清除旧片段,下一轮重新生成
            if decision.force_mode:
                self._force_shot_mode(state, shot_index, decision.force_mode)
            state.append_log(TaskStatus.GENERATING_ASSETS, f"自动修复:按内容质检意见重生成镜头 {shot_index+1}")
            return True

        if decision.action == ACTION_SWITCH_MODEL:
            if self.model_switcher is None:
                logger.warning("shot%d 决策为 switch_model 但未提供切换回调", shot_index)
                return False
            switched = await self.model_switcher(state, shot_index, decision.reason)
            if not switched:
                logger.warning("shot%d 无备选厂商可切换,修复终止", shot_index)
                return False
            return True

        return False

    @staticmethod
    def _force_shot_mode(state: VideoGenerationState, shot_index: int, mode: str) -> None:
        """覆盖镜头期望模式(修复决策要求,如补帧后强制 i2v、人物问题强制 r2v)。"""
        shot = state.storyboard.shots[shot_index]
        shot.desired_mode = mode
        ps = state.get_or_create_project_state()
        entry = ps.shot_state.get(shot_index)
        if entry is not None:
            entry.desired_mode = mode
        ps.touch()

    @staticmethod
    def _record_failure(
        ps, shot_index: int, attempt: int, mode: str, error: ProviderError, *, repair: str = "",
    ) -> None:
        """失败台账:记录失败决策(attempt 与后续成功记录配对,可审计修复链)。"""
        ps.generation_state.record_decision(GenerationDecision(
            shot_index=shot_index,
            provider=getattr(error, "provider", ""),
            model="",
            mode=mode,
            attempt=attempt,
            reason=f"{error.error_code}: {getattr(error, 'message', str(error))}"
                   + (f" | 修复动作={repair}" if repair else ""),
            status="failed",
        ))
        ps.generation_state.mark_shot(shot_index, ok=False)
        entry = ps.shot_state.get(shot_index)
        if entry is not None:
            entry.status = "failed"
        ps.touch()

    # ============================ 参考素材 ============================

    @staticmethod
    def _user_reference_paths(state: VideoGenerationState) -> list[str]:
        """用户上传的参考图(subject/style/scene/camera/action 用途)。"""
        return [
            s.content for s in (state.input_sources or [])
            if s.type == "image" and os.path.exists(s.content)
        ]

    @staticmethod
    def _collect_references(
        state: VideoGenerationState,
        shot_index: int,
        user_reference_paths: list[str] | None,
    ) -> list[str]:
        """汇总本镜参考素材:用户参考图 + 角色参考图资产(去重、必须存在)。"""
        ps = state.get_or_create_project_state()
        refs: list[str] = list(user_reference_paths or [])
        shot_entry = ps.shot_state.get(shot_index)
        if shot_entry is not None:
            for asset_id in shot_entry.ref_asset_ids:
                for asset in ps.asset_state.assets:
                    if asset.asset_id == asset_id and os.path.exists(asset.path):
                        refs.append(asset.path)
        # 去重保序
        seen: set[str] = set()
        return [p for p in refs if not (p in seen or seen.add(p))]
