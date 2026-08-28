"""Voice Provider 工厂。"""
from __future__ import annotations

import logging

from ...core.config import settings
from .base import VoiceProvider
from .mock_voice import MockVoiceProvider

logger = logging.getLogger("ai_video_agent")


def get_voice_provider() -> VoiceProvider:
    if settings.voice_provider == "dashscope":
        try:
            from .dashscope_voice import DashScopeVoiceProvider
            return DashScopeVoiceProvider()
        except Exception as e:
            logger.warning("DashScope Voice Provider 初始化失败,回退 Mock: %s", e)
            return MockVoiceProvider()
    return MockVoiceProvider()
