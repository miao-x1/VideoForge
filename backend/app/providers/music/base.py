"""Music Provider 抽象接口。"""
from __future__ import annotations

from abc import abstractmethod

from ..base import ModelProvider


class MusicProvider(ModelProvider):
    """音乐生成模型 Provider 抽象(对应任务书 MusicModelProvider)。"""

    provider_type = "music"

    @abstractmethod
    async def generate(self, *, save_path: str, duration: int, mood: str = "light") -> str:
        """生成指定时长、指定情绪的背景音乐并保存,返回路径。"""


# 任务书语义别名: MusicModelProvider 即 MusicProvider
MusicModelProvider = MusicProvider
