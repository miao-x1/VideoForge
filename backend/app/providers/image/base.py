"""Image Provider 抽象接口。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, *, prompt: str, save_path: str, width: int = 1280, height: int = 720) -> str:
        """根据 prompt 生成图片并保存到 save_path,返回保存路径。"""
