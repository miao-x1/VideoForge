"""视频索引器:视频生成完成后,提取元数据 + 语义描述 + Embedding,写入 Milvus。"""
from __future__ import annotations

import json

from sqlalchemy import select

from ..core.logging import logger
from ..db.database import async_session
from ..db.models import TaskRecord
from ..models.state import VideoGenerationState
from ..providers.llm.base import LLMProvider
from .embedding_provider import embedding_provider
from .metadata_extractor import extract_metadata
from .semantic_extractor import SemanticExtractor
from .vector_store import vector_store


class VideoIndexer:
    """视频生成完成后自动索引:元数据 → 语义描述 → Embedding → Milvus。"""

    def __init__(self, llm: LLMProvider) -> None:
        self.semantic_extractor = SemanticExtractor(llm=llm)

    async def index(self, state: VideoGenerationState) -> None:
        """索引视频到向量库。"""
        if not state.video_path:
            logger.info("视频未生成完成,跳过索引: task=%s", state.task_id)
            return

        # 1. 提取元数据
        metadata = extract_metadata(state)
        logger.info("视频元数据提取完成: task=%s title=%s", state.task_id, metadata["title"])

        # 2. 生成语义描述
        semantic_desc = await self.semantic_extractor.extract(state)
        logger.info("语义描述生成完成: task=%s len=%d", state.task_id, len(semantic_desc))

        # 3. 生成 Embedding
        embedding = await embedding_provider.embed(semantic_desc)
        logger.info("Embedding 生成完成: task=%s dim=%d", state.task_id, len(embedding))

        # 4. 写入 Milvus
        vector_store.insert(
            video_id=state.task_id,
            user_id=state.user_id,
            embedding=embedding,
            semantic_description=semantic_desc,
            metadata=metadata,
        )
        logger.info("视频索引完成: task=%s", state.task_id)
