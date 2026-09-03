"""Voice Provider 工厂。

生产环境强制使用真实 Provider，初始化失败时抛出 ProviderUnavailableError。
Mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from ...core.logging import logger
from .base import VoiceProvider


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


def get_voice_provider() -> VoiceProvider:
    if settings.voice_provider == "dashscope":
        key = settings.llm_api_key or settings.dashscope_api_key
        if not key:
            raise ProviderNotConfiguredError(
                "voice",
                "VOICE_PROVIDER=dashscope 但未配置 API Key",
            )
        try:
            from .dashscope_voice import DashScopeVoiceProvider
            logger.info("Voice Provider: dashscope (model=%s)", settings.tts_model)
            return DashScopeVoiceProvider()
        except Exception as e:
            raise ProviderUnavailableError("voice", f"DashScope Voice Provider 初始化失败: {e}") from e

    if settings.voice_provider == "mock":
        if not _is_mock_allowed():
            raise ProviderNotConfiguredError(
                "voice",
                "VOICE_PROVIDER=mock 但当前为生产环境 (APP_ENV=production)。",
            )
        from .mock_voice import MockVoiceProvider
        logger.warning("Voice Provider: mock (测试模式)")
        return MockVoiceProvider()

    raise ProviderNotConfiguredError("voice", f"未知 VOICE_PROVIDER: {settings.voice_provider}")
