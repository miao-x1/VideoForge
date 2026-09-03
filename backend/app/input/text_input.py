"""文本输入处理器:直接透传用户文本。"""
from __future__ import annotations

from .base import InputProcessor, InputSource, InputPayload, InputType


class TextProcessor(InputProcessor):
    name = "text"

    async def process(self, source: InputSource) -> InputPayload:
        return InputPayload(
            type=InputType.TEXT,
            raw_content=source.content,
            processed_content=source.content,
        )
