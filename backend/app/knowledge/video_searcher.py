"""视频检索器:自然语言查询 → Embedding → 向量检索 → 返回结果。"""
from __future__ import annotations

from typing import List, Dict, Any

from ..core.logging import logger
from .embedding_provider import embedding_provider
from .vector_store import vector_store


class VideoSearcher:
    """自然语言检索历史视频,按语义相似度排序。"""

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """搜索与查询语义最相似的历史视频。

        返回格式: [{video_id, score, semantic_description, metadata}]
        """
        embedding = await embedding_provider.embed(query)
        results = vector_store.search(
            query_embedding=embedding,
            user_id=user_id,
            top_k=top_k,
        )
        logger.info("视频检索: query=%s user=%s results=%d", query[:30], user_id, len(results))
        return results


video_searcher = VideoSearcher()
