"""QualityJudgeAgent:内容级质检 Agent(任务书第 9 节"AI 不是生成完就结束")。

与 video/quality.py 的纯技术校验(时长/分辨率/文件存在/音轨)分工:
- 技术校验:机器可验的硬指标,失败确定性修复(补素材/重合成)
- 内容质检(本 Agent):这个镜头"拍得对不对"——
  * character_consistency: 出场人物是否都在 Character Bible 中(跨镜人物一致)
  * scene_consistency: 地点/时段/光线是否与 scene_state 一致(跨镜场景一致)
  * continuity: 因果链字段完整、与相邻镜头的衔接关系成立
  * action: 镜头动作/画面描述非空且与情绪匹配
  * asset_ready: 画面素材(关键帧或动态片段)已就位

当前为确定性规则判定(mock/真实 LLM 均可跑);视觉 LLM 接入点:
describe_image(keyframe) 与 Bible 视觉关键词比对(Phase 8+ 视觉模型阶段)。
质检报告写入 quality_state,不通过的镜头交 FailureAnalysisAgent 决策修复。
"""
from __future__ import annotations

import os

from ..core.logging import logger
from ..director.project_state import QualityCheck, QualityReport
from ..models.state import VideoGenerationState
from .base import BaseAgent


class QualityJudgeAgent(BaseAgent):
    name = "quality_judge"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        """对所有已有画面素材的镜头做内容质检,报告写入 quality_state。"""
        if state.storyboard is None:
            return
        ps = state.get_or_create_project_state()
        judged: list[QualityReport] = []
        for i, shot in enumerate(state.storyboard.shots):
            has_visual = (shot.video_path and os.path.exists(shot.video_path)) or (
                shot.image_path and os.path.exists(shot.image_path)
            )
            if not has_visual:
                continue  # 素材未生成的镜头不评(技术校验/失败闭环负责)
            report = self.judge_shot(state, i, force_attempt=force)
            ps.quality_state.add_report(report)
            judged.append(report)
        passed = sum(1 for r in judged if r.passed)
        logger.info(
            "内容质检完成: %d 镜通过 / %d 镜评 / 失败镜头 %s",
            passed, len(judged), ps.quality_state.failed_shots,
        )

    def judge_shot(self, state: VideoGenerationState, shot_index: int, *, force_attempt: bool = False) -> QualityReport:
        """评判单个镜头(确定性规则;force_attempt 仅用于强制重评时占位)。"""
        assert state.storyboard is not None
        ps = state.get_or_create_project_state()
        shot = state.storyboard.shots[shot_index]
        shot_entry = ps.shot_state.get(shot_index)

        prior = ps.quality_state.latest_for_shot(shot_index)
        attempt = (prior.attempt + 1) if prior else 1

        checks: list[QualityCheck] = []
        issues: list[str] = []

        # 1) 人物一致性:出场人物必须在 Character Bible 中
        bible_names = {b.name for b in ps.character_state.bibles}
        unknown = [n for n in shot.characters if n and n not in bible_names]
        if shot.characters and unknown:
            checks.append(QualityCheck(
                dimension="character_consistency", passed=False,
                note=f"出场人物 {unknown} 不在 Character Bible 中,跨镜一致性无保障",
            ))
            issues.append(f"人物不一致:{','.join(unknown)} 不在 Bible")
        elif shot.characters:
            checks.append(QualityCheck(
                dimension="character_consistency", passed=True,
                note=f"出场人物 {shot.characters} 均与 Bible 一致",
            ))

        # 2) 场景一致性:地点/时段/光线与 scene_state 记录一致
        scene_entry = ps.scene_state.get(shot.scene_id)
        if scene_entry is not None and shot.location:
            consistent = (
                (not scene_entry.location or scene_entry.location in shot.location or shot.location in scene_entry.location)
                and (not scene_entry.time_of_day or scene_entry.time_of_day == shot.time_of_day)
            )
            if consistent:
                checks.append(QualityCheck(
                    dimension="scene_consistency", passed=True,
                    note=f"地点/时段与场景态一致({shot.location}/{shot.time_of_day})",
                ))
            else:
                checks.append(QualityCheck(
                    dimension="scene_consistency", passed=False,
                    note=f"场景漂移:镜头={shot.location}/{shot.time_of_day} vs 场景态={scene_entry.location}/{scene_entry.time_of_day}",
                ))
                issues.append("场景与相邻镜头不一致(地点/时段漂移)")

        # 3) 连续性:因果链字段完整(非首镜必须有 continuity_in 与因果说明)
        continuity_ok = bool(shot.continuity_out) and (
            shot_index == 0 or bool(shot.continuity_in and shot.causal_note)
        )
        checks.append(QualityCheck(
            dimension="continuity", passed=continuity_ok,
            note="因果链字段完整" if continuity_ok else "缺少 continuity_in/causal_note,镜头衔接断裂",
        ))
        if not continuity_ok:
            issues.append("镜头连续性字段缺失")

        # 4) 动作/画面:描述非空
        action_ok = bool((shot.character_action or shot.visual_description or "").strip())
        checks.append(QualityCheck(
            dimension="action", passed=action_ok,
            note="画面动作描述完整" if action_ok else "画面/动作描述为空",
        ))
        if not action_ok:
            issues.append("镜头动作描述缺失")

        # 5) 素材就位
        has_visual = (shot.video_path and os.path.exists(shot.video_path)) or (
            shot.image_path and os.path.exists(shot.image_path)
        )
        checks.append(QualityCheck(
            dimension="asset_ready", passed=has_visual,
            note="画面素材已就位" if has_visual else "画面素材缺失",
        ))
        if not has_visual:
            issues.append("画面素材未生成")

        passed = not issues
        if shot_entry is not None:
            shot_entry.status = "verified" if passed else "failed"

        return QualityReport(
            shot_index=shot_index,
            attempt=attempt,
            passed=passed,
            checks=checks,
            issues=issues,
            judge_note="镜头内容质检通过" if passed else f"发现 {len(issues)} 个问题",
            repair_hint="" if passed else "按问题清单重编译 prompt 并重新生成该镜头",
        )
