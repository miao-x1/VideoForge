"""LLM Provider 工厂:按 settings.llm_provider 返回对应实现。

新增真实 Provider 步骤:
1. 在本包新增 xxx_llm.py 实现 LLMProvider
2. 在 core/config.py 的 llm_provider Literal 里加入对应字面量
3. 在下方 get_llm_provider() 加分发分支
Agent / Orchestrator 无需改动。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.logging import logger
from .base import LLMProvider
from .mock_llm import MockLLMProvider


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "dashscope":
        key = settings.llm_api_key or settings.dashscope_api_key
        if not key:
            logger.warning("LLM_PROVIDER=dashscope 但未配置 API Key,回退 Mock")
            return MockLLMProvider()
        # 延迟 import,未启用 dashscope 时不需要 openai 包
        from .dashscope_llm import DashScopeLLMProvider
        return DashScopeLLMProvider()
    return MockLLMProvider()


__all__ = ["LLMProvider", "get_llm_provider"]
