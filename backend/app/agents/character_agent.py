"""CharacterAgent:人物设定管理(Agent 决策层,任务书第四节)。

建立并维护 Character Bible:每个人物的身份/性格/外貌/发型/服装/关系/背景。
后续每个镜头生成前,ShotPlanner / PromptCompiler 都必须读取 Bible,
保证同一人物在不同镜头、不同场景中形象一致(配合角色参考图资产做 R2V/I2V)。

本阶段(Phase 3)只负责建立档案;角色参考图资产绑定在图片生成阶段(Phase 5)接入。
"""
from __future__ import annotations

from ..core.logging import logger
from ..director.project_state import StoryState
from ..models.state import VideoGenerationState
from ..schemas.bible import CharacterBible
from .base import BaseAgent


class CharacterAgent(BaseAgent):
    name = "character_bible"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        ps = state.get_or_create_project_state()
        if ps.character_state.bibles and not force:
            logger.info("Character Bible 已存在(characters=%d),跳过", len(ps.character_state.bibles))
            return
        if state.requirement is None:
            raise RuntimeError("CharacterAgent 缺少上游 requirement")

        context = self._build_context(state, ps.story_state)
        data = await self.llm.generate(task="character_bible", context=context)

        raw_chars = data.get("characters") or []
        req_names = [c.name for c in state.requirement.characters]
        count = 0
        for i, raw in enumerate(raw_chars):
            if not raw.get("name"):
                continue
            raw["character_id"] = raw.get("character_id") or f"character_{i + 1:03d}"
            # 视觉关键词兜底:LLM 漏给时从外貌/服装提取,保证一致性提示不为空
            if not raw.get("visual_keywords"):
                fallbacks = [raw.get("appearance", ""), raw.get("hairstyle", ""), raw.get("clothing", "")]
                raw["visual_keywords"] = [v for v in fallbacks if v][:3]
            bible = CharacterBible(**raw)
            ps.character_state.upsert_bible(bible)
            count += 1

        # 防御:LLM 漏掉 requirement 中的人物时,用需求侧简介补占位档案,保证后续可读取
        existing_names = {b.name for b in ps.character_state.bibles}
        for i, name in enumerate(req_names):
            if name in existing_names:
                continue
            ps.character_state.upsert_bible(CharacterBible(
                character_id=f"character_{i + 1:03d}",
                name=name,
                identity=state.requirement.characters[i].description,
            ))
            count += 1
            logger.warning("LLM 未返回人物档案,已用需求侧信息补占位: %s", name)

        ps.touch()
        logger.info("Character Bible 建立完成: %d 个人物(%s)", count, ", ".join(b.name for b in ps.character_state.bibles))

    @staticmethod
    def _build_context(state: VideoGenerationState, story: StoryState) -> dict:
        context: dict = {
            "requirement": state.requirement.model_dump(),
            "creative_intent": state.creative_intent.model_dump() if state.creative_intent else None,
        }
        if story.beats:
            context["story"] = {
                "theme": story.theme,
                "logline": story.logline,
                "core_conflict": story.core_conflict,
                "beats": [b.model_dump() for b in story.beats],
                "character_arcs": [a.model_dump() for a in story.character_arcs],
            }
        return context
