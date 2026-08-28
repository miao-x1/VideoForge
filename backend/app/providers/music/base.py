"""Music Provider 抽象接口。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MusicProvider(ABC):
    @abstractmethod
    async def generate(self, *, save_path: str, duration: int, mood: str = "light") -> str:
        """生成指定时长、指定情绪的背景音乐并保存,返回路径。"""
