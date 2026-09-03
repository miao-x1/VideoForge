"""Embedding 生成:OpenAI 兼容接口(DashScope text-embedding-v3)。

生产环境强制使用真实 API，无 API Key 或 API 失败时抛出异常。
Mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import List

from ..core.config import settings
from ..core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from ..core.logging import logger


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


class EmbeddingProvider:
    """Embedding 生成器,使用真实 API。"""

    def __init__(self) -> None:
        self._client = None
        self._mock = False
        api_key = settings.llm_api_key or settings.dashscope_api_key
        if not api_key:
            if _is_mock_allowed():
                logger.warning("Embedding: 测试模式,使用 Mock 向量")
                self._mock = True
                return
            raise ProviderNotConfiguredError("embedding", "未配置 API Key (LLM_API_KEY / DASHSCOPE_API_KEY)")
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=settings.llm_base_url, timeout=30)
            logger.info("Embedding Provider: dashscope (model=%s)", settings.embedding_model)
        except Exception as e:
            if _is_mock_allowed():
                logger.warning("Embedding: openai 包不可用,测试模式降级到 Mock: %s", e)
                self._mock = True
                return
            raise ProviderUnavailableError("embedding", f"openai 包不可用: {e}") from e

    async def embed(self, text: str) -> List[float]:
        """生成文本的 Embedding 向量。"""
        if self._mock:
            return self._mock_embed(text)
        if self._client is None:
            raise ProviderUnavailableError("embedding", "Embedding client 未初始化")

        def _call() -> List[float]:
            resp = self._client.embeddings.create(
                model=settings.embedding_model,
                input=text,
            )
            return resp.data[0].embedding

        try:
            return await asyncio.to_thread(_call)
        except Exception as e:
            raise ProviderUnavailableError("embedding", f"Embedding API 调用失败: {e}") from e

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 Embedding。"""
        return [await self.embed(t) for t in texts]

    @staticmethod
    def _mock_embed(text: str) -> List[float]:
        """确定性 Mock 向量:从文本 hash 生成(仅测试环境)。"""
        h = hashlib.sha256(text.encode()).digest()
        dim = settings.embedding_dim
        vec = []
        for i in range(dim):
            byte_val = h[i % len(h)]
            vec.append((byte_val / 255.0) * 2 - 1)
        return vec


embedding_provider = EmbeddingProvider()
