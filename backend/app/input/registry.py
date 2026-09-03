"""输入类型注册与路由:根据 InputSource.type 分发到对应 InputProcessor。"""
from __future__ import annotations

from typing import Dict

from ..providers.llm.base import LLMProvider
from .base import InputProcessor, InputSource, InputPayload
from .text_input import TextProcessor
from .image_input import ImageProcessor
from .url_input import URLProcessor
from .video_input import VideoProcessor


_processors: Dict[str, InputProcessor] | None = None


def init_processors(llm: LLMProvider) -> None:
    global _processors
    _processors = {
        "text": TextProcessor(),
        "image": ImageProcessor(llm=llm),
        "url": URLProcessor(),
        "video": VideoProcessor(llm=llm),
    }


def get_processor(source_type: str) -> InputProcessor:
    if _processors is None:
        raise RuntimeError("InputProcessor 未初始化,请先调用 init_processors()")
    proc = _processors.get(source_type)
    if proc is None:
        raise ValueError(f"不支持的输入类型: {source_type}")
    return proc


async def process_all(sources: list[InputSource]) -> list[InputPayload]:
    """批量处理多个输入源,返回理解结果列表。"""
    payloads = []
    for src in sources:
        proc = get_processor(src.type.value)
        payload = await proc.process(src)
        payloads.append(payload)
    return payloads
