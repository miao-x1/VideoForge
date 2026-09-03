"""Music Provider 工厂。

生产环境使用 AmbientMusicProvider（程序化环境音）。
Mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.exceptions import ProviderNotConfiguredError
from ...core.logging import logger
from .base import MusicProvider


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


def get_music_provider() -> MusicProvider:
    if settings.music_provider == "ambient":
        from .ambient_music import AmbientMusicProvider
        logger.info("Music Provider: ambient (程序化环境音)")
        return AmbientMusicProvider()

    if settings.music_provider == "mock":
        if not _is_mock_allowed():
            raise ProviderNotConfiguredError(
                "music",
                "MUSIC_PROVIDER=mock 但当前为生产环境 (APP_ENV=production)。",
            )
        from .mock_music import MockMusicProvider
        logger.warning("Music Provider: mock (测试模式)")
        return MockMusicProvider()

    raise ProviderNotConfiguredError("music", f"未知 MUSIC_PROVIDER: {settings.music_provider}")
