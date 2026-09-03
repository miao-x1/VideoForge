"""Image Provider 工厂:按 settings.image_provider 返回对应实现。

生产环境强制使用真实 Provider，初始化失败时抛出 ProviderUnavailableError。
Mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from ...core.logging import logger
from .base import ImageProvider


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


def get_image_provider() -> ImageProvider:
    if settings.image_provider == "dashscope":
        key = settings.llm_api_key or settings.dashscope_api_key
        if not key:
            raise ProviderNotConfiguredError(
                "image",
                "IMAGE_PROVIDER=dashscope 但未配置 API Key",
            )
        try:
            from .dashscope_image import DashScopeImageProvider
            logger.info("Image Provider: dashscope (model=%s)", settings.image_model)
            return DashScopeImageProvider()
        except Exception as e:
            raise ProviderUnavailableError("image", f"DashScope Image Provider 初始化失败: {e}") from e

    if settings.image_provider == "mock":
        if not _is_mock_allowed():
            raise ProviderNotConfiguredError(
                "image",
                "IMAGE_PROVIDER=mock 但当前为生产环境 (APP_ENV=production)。",
            )
        from .mock_image import MockImageProvider
        logger.warning("Image Provider: mock (测试模式)")
        return MockImageProvider()

    raise ProviderNotConfiguredError("image", f"未知 IMAGE_PROVIDER: {settings.image_provider}")


__all__ = ["ImageProvider", "get_image_provider"]
