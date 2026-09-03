"""LLM Provider 工厂:按 settings.llm_provider 返回对应实现。

生产环境强制使用真实 Provider，缺少 API Key 时抛出 ProviderNotConfiguredError。
Mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.exceptions import ProviderNotConfiguredError
from ...core.logging import logger
from .base import LLMProvider


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "dashscope":
        key = settings.llm_api_key or settings.dashscope_api_key
        if not key:
            raise ProviderNotConfiguredError(
                "llm",
                "LLM_PROVIDER=dashscope 但未配置 LLM_API_KEY / DASHSCOPE_API_KEY",
            )
        from .dashscope_llm import DashScopeLLMProvider
        logger.info("LLM Provider: dashscope (model=%s)", settings.llm_model)
        return DashScopeLLMProvider()

    if settings.llm_provider == "mock":
        if not _is_mock_allowed():
            raise ProviderNotConfiguredError(
                "llm",
                "LLM_PROVIDER=mock 但当前为生产环境 (APP_ENV=production)。"
                "请在 .env 设置 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 以启用 Mock。",
            )
        from .mock_llm import MockLLMProvider
        logger.warning("LLM Provider: mock (测试模式)")
        return MockLLMProvider()

    raise ProviderNotConfiguredError("llm", f"未知 LLM_PROVIDER: {settings.llm_provider}")


__all__ = ["LLMProvider", "get_llm_provider"]
