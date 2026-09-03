"""ScriptAgent:根据 StructuredRequirement 生成完整短视频脚本。"""
from __future__ import annotations

from ..models.state import VideoGenerationState
from ..schemas.script import VideoScript
from .base import BaseAgent


class ScriptAgent(BaseAgent):
    name = "script"

    async def run(self, state: VideoGenerationState, *, feedback: str | None = None) -> None:
        if state.requirement is None:
            raise RuntimeError("ScriptAgent 缺少上游 requirement")
        context = {"requirement": state.requirement.model_dump()}

        # 作品级设定注入(Agent 决策结果):故事节拍/人物弧光/Character Bible/World/Style Bible
        # 脚本必须基于故事规划与人物档案展开,保证叙事因果与人物一致性
        ps = state.project_state
        if ps is not None:
            if ps.story_state.beats:
                context["story"] = {
                    "theme": ps.story_state.theme,
                    "logline": ps.story_state.logline,
                    "core_conflict": ps.story_state.core_conflict,
                    "ending_tone": ps.story_state.ending_tone,
                    "beats": [b.model_dump() for b in ps.story_state.beats],
                    "character_arcs": [a.model_dump() for a in ps.story_state.character_arcs],
                }
            if ps.character_state.bibles:
                arc_by_id = {a.character_id: a for a in ps.story_state.character_arcs}
                context["characters"] = [
                    {
                        "character_id": b.character_id,
                        "name": b.name,
                        "identity": b.identity,
                        "personality": b.personality,
                        "appearance": b.appearance,
                        "clothing": b.clothing,
                        "relations": [r.model_dump() for r in b.relations],
                        "background": b.background,
                        "arc": arc_by_id[b.character_id].model_dump() if b.character_id in arc_by_id else None,
                    }
                    for b in ps.character_state.bibles
                ]
            if ps.world_state.bible is not None:
                context["world"] = ps.world_state.bible.model_dump()
            if ps.style_state.bible is not None:
                context["style_bible"] = ps.style_state.bible.model_dump()

        # 传递视觉参数,确保脚本中的 visual 字段保留用户的光照/色彩/风格意图
        if state.spec:
            from .prompt_compiler import PromptCompiler
            visual_directives = PromptCompiler.compile_visual_directives(state.spec)
            if visual_directives:
                context["visual_directives"] = visual_directives

        # Decision Loop:用户重新生成时表达"哪里不满意",注入 LLM 上下文定向修改
        if feedback:
            context["user_feedback"] = feedback

        data = await self.llm.generate(task="script", context=context)
        state.script = VideoScript(**data)
