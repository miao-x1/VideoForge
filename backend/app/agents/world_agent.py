"""WorldAgent:世界观与视觉风格管理(Agent 决策层,任务书第五节)。

建立并维护 World Bible(时代/地域/建筑/天气/时间/道具/场景设定)
与 Style Bible(画面风格/摄影/色调/光线基调/全片负面约束)。
之后所有镜头的环境与视觉参数都必须以这两份 Bible 为基线,
ShotPlanner 在此基础上做场景级细化(如同一场景保持阴雨傍晚一致)。
"""
from __future__ import annotations

from ..core.logging import logger
from ..models.state import VideoGenerationState
from ..schemas.bible import StyleBible, WorldBible
from .base import BaseAgent


class WorldAgent(BaseAgent):
    name = "world_bible"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        ps = state.get_or_create_project_state()
        if ps.world_state.bible is not None and ps.style_state.bible is not None and not force:
            logger.info("World/Style Bible 已存在,跳过")
            return
        if state.requirement is None:
            raise RuntimeError("WorldAgent 缺少上游 requirement")

        context = self._build_context(state)
        data = await self.llm.generate(task="world_bible", context=context)

        raw_world = data.get("world") or {}
        raw_style = data.get("style") or {}
        # 场景条目兜底:LLM 漏返时用 requirement.scenes 补齐,保证场景基线可读取
        if not raw_world.get("scenes"):
            raw_world["scenes"] = [
                {
                    "scene_key": f"scene_{i + 1:02d}",
                    "name": sc.location,
                    "location": sc.location,
                    "description": sc.description,
                }
                for i, sc in enumerate(state.requirement.scenes)
            ]
            if raw_world["scenes"]:
                logger.info("LLM 未返回场景设定,已用 requirement.scenes 补 %d 条", len(raw_world["scenes"]))

        ps.world_state.bible = WorldBible(**raw_world)
        ps.style_state.bible = StyleBible(**raw_style)
        ps.touch()
        logger.info(
            "World/Style Bible 建立完成: era=%s region=%s scenes=%d style=%s palette=%s",
            ps.world_state.bible.era, ps.world_state.bible.region,
            len(ps.world_state.bible.scenes),
            ps.style_state.bible.visual_style, ps.style_state.bible.color_palette,
        )

    @staticmethod
    def _build_context(state: VideoGenerationState) -> dict:
        context: dict = {
            "requirement": state.requirement.model_dump(),
            "creative_intent": state.creative_intent.model_dump() if state.creative_intent else None,
            "duration": state.duration,
            "style": state.style,
            "aspect_ratio": state.aspect_ratio,
        }
        if state.spec:
            from .prompt_compiler import PromptCompiler
            visual = PromptCompiler.compile_visual_directives(state.spec)
            if visual:
                context["visual_directives"] = visual
        return context
