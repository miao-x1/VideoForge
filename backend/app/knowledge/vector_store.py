"""Milvus 向量存储:连接管理 + Collection CRUD。

使用 Milvus Lite 本地文件模式,无需 Docker。
生产环境可切换到 Milvus 集群(修改 milvus_uri 配置)。
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from ..core.config import settings, STORAGE_ROOT
from ..core.logging import logger

COLLECTION = "video_embeddings"


class VectorStore:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        # 确保路径加入 sys.path(解决 pymilvus 导入问题)
        site_packages = os.path.join(
            os.path.dirname(sys.executable), "Lib", "site-packages"
        )
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)
        from pymilvus import MilvusClient
        uri = settings.milvus_uri or str(STORAGE_ROOT / "milvus.db")
        os.makedirs(os.path.dirname(uri), exist_ok=True)
        self._client = MilvusClient(uri)
        self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        """确保 video_embeddings collection 存在(VARCHAR 主键,支持字符串 task_id)。"""
        from pymilvus import DataType
        client = self._client
        if not client.has_collection(COLLECTION):
            schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
            schema.add_field("user_id", DataType.VARCHAR, max_length=128)
            schema.add_field("semantic_description", DataType.VARCHAR, max_length=2048)
            schema.add_field("metadata", DataType.VARCHAR, max_length=8192)
            client.create_collection(collection_name=COLLECTION, schema=schema)
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="vector", metric_type="COSINE", index_type="FLAT",
            )
            client.create_index(collection_name=COLLECTION, index_params=index_params)
            client.load_collection(COLLECTION)
            logger.info("Milvus collection '%s' 已创建 (dim=%d, pk=VARCHAR)", COLLECTION, settings.embedding_dim)

    def insert(
        self,
        video_id: str,
        user_id: str,
        embedding: List[float],
        semantic_description: str,
        metadata: Dict[str, Any],
    ) -> None:
        client = self._get_client()
        # 同一任务重复索引(局部重生成后)时先删旧向量,保证检索指向当前版本
        self.delete_by_video(video_id)
        client.insert(COLLECTION, [{
            "id": video_id,
            "vector": embedding,
            "user_id": user_id,
            "semantic_description": semantic_description,
            "metadata": json.dumps(metadata, ensure_ascii=False),
        }])
        logger.info("向量已插入: video_id=%s", video_id)

    def search(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """向量检索,返回 Top-K 结果(按相似度排序)。"""
        client = self._get_client()
        client.load_collection(COLLECTION)
        results = client.search(
            COLLECTION,
            [query_embedding],
            limit=top_k,
            output_fields=["user_id", "semantic_description", "metadata"],
            filter=f'user_id == "{user_id}"',
        )
        hits = []
        if results and results[0]:
            for hit in results[0]:
                entity = hit.get("entity", {})
                metadata = {}
                raw_meta = entity.get("metadata", "{}")
                if isinstance(raw_meta, str):
                    try:
                        metadata = json.loads(raw_meta)
                    except json.JSONDecodeError:
                        pass
                hits.append({
                    "video_id": hit.get("id"),
                    "score": hit.get("distance"),
                    "semantic_description": entity.get("semantic_description", ""),
                    "metadata": metadata,
                })
        return hits

    def delete_by_video(self, video_id: str) -> None:
        """删除指定视频的向量记录。"""
        client = self._get_client()
        client.delete(COLLECTION, filter=f'id == "{video_id}"')


vector_store = VectorStore()
