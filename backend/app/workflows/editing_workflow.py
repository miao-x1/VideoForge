"""EditingWorkflow:把镜头片段合成为成片(固定剪辑步骤)。

固定步骤:定位 BGM → 应用剪辑决策单(editing_state:顺序/转场)
→ 版本化输出路径 → 调用 VideoAssembler 合成
→ 写回 state.video_path / 版本历史 / editing_state 成片台账。

剪辑"决策"(镜头顺序/转场/节奏)由 EditingPlanner Agent 产出,
本 Workflow 只负责按决策单执行合成;无决策单时回退叙事顺序(legacy)。
技术质检(时长/分辨率/音轨)与时间轴构建仍由 Orchestrator 在合成后处理。
"""
from __future__ import annotations

import os

from ..core.config import storage_dir
from ..core.logging import logger
from ..director.project_state import AssetEntry
from ..models.state import VideoGenerationState
from ..schemas.storyboard import StoryboardShot
from ..video.assembly import VideoAssembler
from .base import BaseWorkflow


class EditingWorkflow(BaseWorkflow):
    name = "editing_workflow"

    def __init__(self, assembler: VideoAssembler) -> None:
        self.assembler = assembler

    async def run(self, state: VideoGenerationState) -> str:
        """执行合成,返回成片路径。"""
        if state.storyboard is None:
            raise RuntimeError("EditingWorkflow 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        ps.generation_state.current_stage = "editing"

        video_dir = storage_dir("videos")
        # 版本化输出:首次 {task_id}.mp4,之后 _v2/_v3...,旧版本不覆盖
        next_version = len(state.video_versions) + 1
        file_name = (
            f"{state.task_id}.mp4"
            if next_version == 1 else f"{state.task_id}_v{next_version}.mp4"
        )
        output_path = os.path.join(str(video_dir), file_name)
        title = state.script.title if state.script else state.task_id

        # BGM 定位:优先资产台账,回退命名约定(兼容旧任务)
        bgm_path = ""
        if ps.audio_state.bgm_asset_id:
            for asset in ps.asset_state.assets:
                if asset.asset_id == ps.audio_state.bgm_asset_id:
                    bgm_path = asset.path
                    break
        if not bgm_path:
            bgm_path = next(
                (a for a in state.assets if a.endswith(f"{state.task_id}_bgm.wav")),
                "",
            )

        # 应用剪辑决策单:镜头顺序 + 转场覆盖(不改写 storyboard 叙事真相,只影响本次合成)
        ordered_shots = self.ordered_shots(state)
        n_shots = len(state.storyboard.shots)
        n_clips = sum(1 for s in ordered_shots if s.video_path)
        try:
            await self.assembler.assemble(
                shots=ordered_shots,
                bgm_path=bgm_path,
                output_path=output_path,
                title=title,
            )
        except Exception as e:
            raise RuntimeError(
                f"Assembly 失败(shots={n_shots}, clips={n_clips}, output={output_path}): {e}"
            ) from e

        state.video_path = output_path
        state.record_video_version(
            output_path,
            reason="初始合成" if next_version == 1 else "局部修改重合成",
        )

        # 剪辑台账:成片资产登记(顺序/转场/来源已由 EditingPlanner 写入)
        editing = ps.editing_state
        if not editing.shot_order:
            editing.shot_order = list(range(n_shots))
        if not editing.decision_source:
            editing.decision_source = "legacy"
        final_asset_id = f"{state.task_id}_final_v{next_version}"
        editing.final_video_asset_id = final_asset_id
        ps.asset_state.add(AssetEntry(
            asset_id=final_asset_id,
            type="video",
            path=output_path,
            source_provider=getattr(self.assembler, "name", "assembler"),
            metadata={
                "role": "final", "version": str(next_version),
                "decision_source": editing.decision_source,
                "order": ">".join(str(i) for i in editing.shot_order),
            },
        ))
        ps.touch()
        logger.info("视频合成完成(v%d, source=%s): %s",
                    next_version, editing.decision_source, output_path)
        return output_path

    @staticmethod
    def ordered_shots(state: VideoGenerationState) -> list[StoryboardShot]:
        """按剪辑决策单产出合成用镜头序列(顺序重排 + 转场覆盖)。

        - decision_source=agent:按 shot_order 重排,转场取 transitions 边界决策
        - 无决策单(legacy):叙事原序,转场沿用 shot.transition 字段
        始终返回 shot 的副本(model_copy),storyboard 叙事真相不被改写。
        """
        ps = state.get_or_create_project_state()
        editing = ps.editing_state
        shots = state.storyboard.shots
        n = len(shots)

        order = editing.shot_order
        if editing.decision_source != "agent" or sorted(order) != list(range(n)):
            return list(shots)

        ordered: list[StoryboardShot] = []
        for pos, idx in enumerate(order):
            shot = shots[idx]
            updates: dict = {}
            # 边界转场:key 以"叙事序号"记录,应用在合成序列的相邻镜头上
            key_in = f"{order[pos - 1]}->{idx}" if pos > 0 else ""
            trans = editing.transitions.get(key_in)
            if pos == 0:
                updates["transition"] = "cut"  # 首镜硬切开场
            elif trans:
                updates["transition"] = trans
            ordered.append(shot.model_copy(update=updates) if updates else shot)
        return ordered
