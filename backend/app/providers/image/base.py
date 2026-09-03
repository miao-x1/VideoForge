"""Image Provider 抽象接口。"""
from __future__ import annotations

from abc import abstractmethod

from ..base import ModelProvider


class ImageProvider(ModelProvider):
    """图片生成模型 Provider 抽象(对应任务书 ImageModelProvider)。"""

    provider_type = "image"

    @abstractmethod
    async def generate(self, *, prompt: str, save_path: str, width: int = 1280, height: int = 720) -> str:
        """根据 prompt 生成图片并保存到 save_path,返回保存路径。"""


# 任务书语义别名: ImageModelProvider 即 ImageProvider
ImageModelProvider = ImageProvider
