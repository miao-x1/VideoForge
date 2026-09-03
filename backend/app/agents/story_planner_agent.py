"""StoryPlannerAgent:作品级故事规划(Agent 决策层)。

职责(任务书第三节):把用户的模糊创意推理为故事结构——
主题 / logline / 核心冲突 / 结局基调 / 故事节拍链(因果) / 人物弧光。
输出写入 ProjectState.story_state 与 project_info,供后续:
- ScriptAgent 基于节拍与弧光写脚本
- CharacterAgent 基于弧光建立人物档案
- ShotPlanner 基于节拍拆镜头并维护因果连续性

不产出台词、不产出画面 prompt(那是 Script/Storyboard 阶段的职责)。
"""
from __future__ import annotations

from ..core.logging import logger
from ..director.project_state import CharacterArc, StoryBeat
from ..models.state import VideoGenerationState
from .base import BaseAgent


class StoryPlannerAgent(BaseAgent):
    name = "story_planning"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        ps = state.get_or_create_project_state()
        if ps.story_state.beats and not force:
            logger.info("故事规划已存在(beats=%d),跳过", len(ps.story_state.beats))
            return
        if state.requirement is None:
            raise RuntimeError("StoryPlannerAgent 缺少上游 requirement")

        context = self._build_context(state)
        data = await self.llm.generate(task="story_planning", context=context)

        # 作品基础信息
        ps.project_info.title = data.get("title") or state.requirement.topic
        ps.project_info.genre = state.requirement.genre or ps.project_info.genre
        ps.project_info.duration_target = state.duration
        ps.project_info.aspect_ratio = state.aspect_ratio

        # 故事节拍链
        beats: list[StoryBeat] = []
        for i, raw in enumerate(data.get("beats") or []):
            beats.append(StoryBeat(
                beat_id=raw.get("beat_id") or f"beat_{i + 1:02d}",
                name=raw.get("name") or f"节拍{i + 1}",
                summary=raw.get("summary", ""),
                emotion=raw.get("emotion", ""),
                scene_refs=raw.get("scene_refs") or [],
            ))
        # 人物弧光:character_id 以 requirement.characters 顺序为准,与 CharacterAgent 对齐
        req_names = [c.name for c in state.requirement.characters]
        arcs: list[CharacterArc] = []
        for i, raw in enumerate(data.get("character_arcs") or []):
            cid = raw.get("character_id") or f"character_{i + 1:03d}"
            arcs.append(CharacterArc(
                character_id=cid,
                arc_summary=raw.get("arc_summary", ""),
                start_state=raw.get("start_state", ""),
                end_state=raw.get("end_state", ""),
            ))
        ps.story_state.theme = data.get("theme", "")
        ps.story_state.logline = data.get("logline", "")
        ps.story_state.core_conflict = data.get("core_conflict", "")
        ps.story_state.ending_tone = data.get("ending_tone", "")
        ps.story_state.beats = beats
        ps.story_state.character_arcs = arcs
        ps.touch()
        logger.info(
            "故事规划完成: title=%s beats=%d arcs=%d conflict=%s",
            ps.project_info.title, len(beats), len(arcs), ps.story_state.core_conflict,
        )

    @staticmethod
    def _build_context(state: VideoGenerationState) -> dict:
        context: dict = {
            "user_input": state.user_input,
            "duration": state.duration,
            "style": state.style,
            "aspect_ratio": state.aspect_ratio,
            "requirement": state.requirement.model_dump() if state.requirement else None,
        }
        if state.creative_intent:
            context["creative_intent"] = state.creative_intent.model_dump()
        if state.multimodal_context:
            context["multimodal_context"] = state.multimodal_context
        return context
