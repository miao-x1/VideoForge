"""图生视频(I2V)Provider 工厂。

根据 settings.i2v_provider 切换 mock / dashscope,与 image/voice/music 工厂模式一致。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.logging import logger
from .base import VideoProvider


def get_video_provider() -> VideoProvider:
    """返回 I2V Provider 实例。"""
    provider = settings.i2v_provider
    logger.info("使用 I2V Provider: %s (model=%s)", provider, settings.i2v_model)
    if provider == "dashscope":
        from .dashscope_i2v import DashScopeI2VProvider
        return DashScopeI2VProvider()
    if provider == "mock":
        from .mock_i2v import MockI2VProvider
        return MockI2VProvider()
    raise ValueError(f"未知 i2v_provider: {provider}")
