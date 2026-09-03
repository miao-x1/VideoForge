"""语义描述抽取:用 LLM 从脚本/需求生成视频语义摘要,用于 Embedding。"""
from __future__ import annotations

from typing import Optional

from ..core.logging import logger
from ..models.state import VideoGenerationState
from ..providers.llm.base import LLMProvider


class SemanticExtractor:
    """从 Pipeline 产物生成适合 Embedding 的语义描述文本。"""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def extract(self, state: VideoGenerationState) -> str:
        """生成视频语义描述摘要。"""
        parts = []
        if state.requirement:
            parts.append(f"主题: {state.requirement.topic}")
            parts.append(f"风格: {state.requirement.style}")
            parts.append(f"题材: {state.requirement.genre}")
            if state.requirement.characters:
                chars = ", ".join(c.name for c in state.requirement.characters)
                parts.append(f"角色: {chars}")

        if state.script:
            parts.append(f"标题: {state.script.title}")
            parts.append(f"Hook: {state.script.hook}")
            for scene in state.script.scenes:
                if scene.voiceover:
                    parts.append(scene.voiceover)
                elif scene.visual:
                    parts.append(scene.visual)

        if not parts:
            return state.user_input

        # 尝试用 LLM 生成更精炼的语义摘要
        try:
            raw = "\n".join(parts)
            data = await self.llm.generate(task="semantic_summary", context={"raw_content": raw})
            return data.get("summary", raw)
        except Exception as e:
            logger.warning("语义摘要 LLM 调用失败,使用原始拼接: %s", e)
            return "\n".join(parts)
