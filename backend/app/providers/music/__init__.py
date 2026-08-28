"""Music Provider 工厂。"""
from __future__ import annotations

import logging

from ...core.config import settings
from .base import MusicProvider
from .mock_music import MockMusicProvider

logger = logging.getLogger("ai_video_agent")


def get_music_provider() -> MusicProvider:
    if settings.music_provider == "ambient":
        try:
            from .ambient_music import AmbientMusicProvider
            return AmbientMusicProvider()
        except Exception as e:
            logger.warning("Ambient Music Provider 初始化失败,回退 Mock: %s", e)
            return MockMusicProvider()
    return MockMusicProvider()
