"""图片输入处理器:调用 LLM 多模态能力理解图片,输出文本描述。"""
from __future__ import annotations

import os

from ..core.logging import logger
from ..providers.llm.base import LLMProvider
from .base import InputProcessor, InputSource, InputPayload, InputType


class ImageProcessor(InputProcessor):
    name = "image"

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def process(self, source: InputSource) -> InputPayload:
        image_path = source.content
        if not os.path.isfile(image_path):
            logger.warning("图片文件不存在: %s", image_path)
            return InputPayload(
                type=InputType.IMAGE,
                raw_content=image_path,
                processed_content=f"[图片文件不存在: {os.path.basename(image_path)}]",
            )
        try:
            desc = await self.llm.describe_image(image_path)
            return InputPayload(
                type=InputType.IMAGE,
                raw_content=image_path,
                processed_content=desc,
            )
        except NotImplementedError:
            logger.info("当前 LLM 不支持图片理解,跳过")
            return InputPayload(
                type=InputType.IMAGE,
                raw_content=image_path,
                processed_content=f"[图片已上传: {os.path.basename(image_path)},LLM 暂不支持图片理解]",
            )
