"""EditingPlannerAgent:剪辑决策 Agent(任务书第 7 节)。

在素材生成完成、合成之前决策"成片怎么剪":
- shot_order:镜头顺序(默认叙事顺序;强节奏/倒叙需求可调整,必须保持因果链完整)
- transitions:每个镜头边界的转场决策(key="from->to"),
  依据镜头情绪与因果关系:冲突/惊讶点 cut 硬切,情绪沉淀 dissolve,默认 fade
- pacing_note:节奏决策(哪里快切堆叠、哪里留白长镜头)
决策写入 editing_state,decision_source="agent";
EditingWorkflow 只负责按决策单执行合成,不做创作判断。
"""
from __future__ import annotations

from ..core.logging import logger
from ..models.state import VideoGenerationState
from .base import BaseAgent


class EditingPlannerAgent(BaseAgent):
    name = "editing_planning"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        if state.storyboard is None:
            raise RuntimeError("EditingPlannerAgent 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        if ps.editing_state.decision_source == "agent" and not force:
            logger.info("剪辑决策已存在(agent),跳过")
            return

        context = self._build_context(state)
        data = await self.llm.generate(task="editing_planning", context=context)

        n_shots = len(state.storyboard.shots)

        # 镜头顺序:LLM 决策,校验必须是 0..n-1 的合法排列,否则回退叙事顺序
        order = data.get("shot_order") or []
        if sorted(order) == list(range(n_shots)):
            ps.editing_state.shot_order = order
        else:
            ps.editing_state.shot_order = list(range(n_shots))

        # 转场决策:边界 key "from->to",LLM 产出 + 规则兜底
        transitions = self._build_transitions(state, data.get("transitions") or {})
        ps.editing_state.transitions = transitions
        ps.editing_state.pacing_note = data.get("pacing_note", "") or self._infer_pacing(state)
        ps.editing_state.decision_source = "agent"
        ps.touch()
        logger.info(
            "剪辑决策完成: order=%s transitions=%d pacing=%s",
            ps.editing_state.shot_order, len(transitions), ps.editing_state.pacing_note[:40],
        )

    @staticmethod
    def _build_context(state: VideoGenerationState) -> dict:
        ps = state.get_or_create_project_state()
        shots = []
        for i, shot in enumerate(state.storyboard.shots):
            shots.append({
                "shot_index": i,
                "scene_id": shot.scene_id,
                "emotion": shot.emotion,
                "emotion_end": shot.emotion_end,
                "transition": shot.transition,
                "duration": shot.duration,
                "causal_note": shot.causal_note,
                "visual_description": shot.visual_description,
            })
        return {
            "shots": shots,
            "beats": [b.model_dump() for b in ps.story_state.beats],
            "target_duration": state.duration,
            "genre": ps.project_info.genre or "",
        }

    def _build_transitions(self, state: VideoGenerationState, llm_transitions: dict) -> dict[str, str]:
        """合并 LLM 转场决策与规则兜底:按情绪/因果决定每个边界。

        规则(确定性兜底):
        - 紧张/冲突/惊讶/幽默 节拍边界 → cut(硬切,节奏快)
        - 悲伤/平静/情绪沉淀 → dissolve(叠化,留白)
        - 其余 → fade(淡入淡出,安全默认)
        LLM 明确给出的边界以 LLM 为准。
        """
        shots = state.storyboard.shots
        transitions: dict[str, str] = {}
        cut_emotions = {"tension", "surprise", "humor", "紧张", "冲突", "惊讶", "高能"}
        dissolve_emotions = {"sad", "calm", "悲伤", "遗憾", "平静", "虐心"}
        for i in range(len(shots) - 1):
            key = f"{i}->{i + 1}"
            llm_value = str(llm_transitions.get(key) or "").lower()
            if llm_value in ("fade", "cut", "dissolve", "slide"):
                transitions[key] = llm_value
                continue
            end_emotion = (shots[i].emotion_end or shots[i].emotion or "").lower()
            if any(e in end_emotion for e in cut_emotions):
                transitions[key] = "cut"
            elif any(e in end_emotion for e in dissolve_emotions):
                transitions[key] = "dissolve"
            else:
                transitions[key] = shots[i].transition or "fade"
        return transitions

    @staticmethod
    def _infer_pacing(state: VideoGenerationState) -> str:
        """无 LLM 产出时的节奏兜底:情绪密集段快切,开场/结尾留白。"""
        n = len(state.storyboard.shots)
        if n <= 3:
            return "全片匀速叙事"
        return f"开场镜头留白铺垫,中段(2-{max(n - 1, 2)})按情绪节拍推进,结尾镜头收束"
