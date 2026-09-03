"""Version Store:为 Pipeline 关键产物保留版本历史。

支持:
- 记录每次产物变更(script/storyboard/prompt)
- 查看版本历史
- 恢复历史版本
- 比较版本差异(简单文本 diff)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.logging import logger


@dataclass
class VersionEntry:
    """单个版本记录。"""

    version: int
    timestamp: float
    node_id: str
    node_type: str
    data: Any  # 产物快照
    label: str = ""
    reason: str = ""  # 变更原因

    def to_dict(self, include_data: bool = False) -> dict:
        d = {
            "version": self.version,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "reason": self.reason,
        }
        if include_data:
            d["data"] = self.data
        return d


class VersionStore:
    """版本历史存储。"""

    def __init__(self) -> None:
        self._versions: Dict[str, List[VersionEntry]] = {}

    def save(self, node_id: str, node_type: str, data: Any, label: str = "", reason: str = "") -> int:
        """保存一个新版本,返回版本号。"""
        if node_id not in self._versions:
            self._versions[node_id] = []
        version = len(self._versions[node_id]) + 1
        entry = VersionEntry(
            version=version,
            timestamp=time.time(),
            node_id=node_id,
            node_type=node_type,
            data=data,
            label=label,
            reason=reason,
        )
        self._versions[node_id].append(entry)
        logger.info("版本保存: %s v%d (%s)", node_id, version, reason or label)
        return version

    def get_history(self, node_id: str, include_data: bool = False) -> List[dict]:
        """获取节点版本历史。"""
        entries = self._versions.get(node_id, [])
        return [e.to_dict(include_data=include_data) for e in entries]

    def get_version(self, node_id: str, version: int) -> Optional[VersionEntry]:
        """获取特定版本。"""
        entries = self._versions.get(node_id, [])
        for e in entries:
            if e.version == version:
                return e
        return None

    def get_latest(self, node_id: str) -> Optional[VersionEntry]:
        """获取最新版本。"""
        entries = self._versions.get(node_id, [])
        return entries[-1] if entries else None

    def restore(self, node_id: str, version: int) -> Optional[Any]:
        """恢复指定版本的数据。"""
        entry = self.get_version(node_id, version)
        if entry:
            logger.info("版本恢复: %s v%d", node_id, version)
            return entry.data
        return None

    def list_nodes(self) -> List[str]:
        """列出有版本历史的节点。"""
        return list(self._versions.keys())


version_store = VersionStore()
