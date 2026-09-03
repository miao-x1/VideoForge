"""Dependency Graph:跟踪 Pipeline 节点间的依赖关系。

当上游节点发生变化时,计算受影响的下游节点,支持局部重生成。

依赖关系:
  creative_intent → script → storyboard → prompt_engineering → media → assembly
  
Asset 依赖:
  storyboard ← asset (reference image)
  prompt_engineering ← asset (style reference)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from ..core.logging import logger


@dataclass
class GraphNode:
    """依赖图节点。"""

    node_id: str  # e.g. "script", "storyboard", "shot_0", "shot_1"
    node_type: str  # script | storyboard | prompt | media | assembly | asset
    label: str = ""
    version: int = 1
    locked: bool = False
    dependencies: Set[str] = field(default_factory=set)  # 依赖的上游 node_id
    dependents: Set[str] = field(default_factory=set)  # 依赖此节点的下游 node_id

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "version": self.version,
            "locked": self.locked,
            "dependencies": sorted(self.dependencies),
            "dependents": sorted(self.dependents),
        }


class DependencyGraph:
    """Pipeline 依赖图:计算变更影响范围,支持局部重生成。"""

    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._init_pipeline_edges()

    def _init_pipeline_edges(self) -> None:
        """初始化标准 Pipeline 依赖链。"""
        pipeline = [
            ("creative_intent", "creative_intent", "创意理解"),
            ("script", "script", "脚本"),
            ("storyboard", "storyboard", "分镜"),
            ("prompt_engineering", "prompt", "Prompt 编译"),
            ("media", "media", "素材生成"),
            ("assembly", "assembly", "视频合成"),
        ]
        for nid, ntype, label in pipeline:
            self._nodes[nid] = GraphNode(node_id=nid, node_type=ntype, label=label)

        # 标准依赖链
        self.add_edge("creative_intent", "script")
        self.add_edge("script", "storyboard")
        self.add_edge("storyboard", "prompt_engineering")
        self.add_edge("prompt_engineering", "media")
        self.add_edge("media", "assembly")

    def add_edge(self, upstream: str, downstream: str) -> None:
        """添加依赖边:downstream 依赖 upstream。"""
        if upstream not in self._nodes:
            self._nodes[upstream] = GraphNode(node_id=upstream, node_type="custom")
        if downstream not in self._nodes:
            self._nodes[downstream] = GraphNode(node_id=downstream, node_type="custom")
        self._nodes[upstream].dependents.add(downstream)
        self._nodes[downstream].dependencies.add(upstream)

    def add_shot_node(self, shot_index: int, depends_on: str = "storyboard") -> None:
        """添加分镜级别的节点(每个 shot 独立追踪)。"""
        shot_id = f"shot_{shot_index}"
        prompt_id = f"prompt_{shot_index}"
        media_id = f"media_{shot_index}"
        self._nodes.setdefault(shot_id, GraphNode(node_id=shot_id, node_type="shot", label=f"镜头 {shot_index + 1}"))
        self._nodes.setdefault(prompt_id, GraphNode(node_id=prompt_id, node_type="prompt_shot", label=f"Prompt {shot_index + 1}"))
        self._nodes.setdefault(media_id, GraphNode(node_id=media_id, node_type="media_shot", label=f"素材 {shot_index + 1}"))
        self.add_edge(depends_on, shot_id)
        self.add_edge(shot_id, prompt_id)
        self.add_edge(prompt_id, media_id)

    def compute_affected(self, changed_node: str) -> List[str]:
        """计算受影响的下游节点(BFS)。"""
        if changed_node not in self._nodes:
            return []
        affected: List[str] = []
        visited: Set[str] = {changed_node}
        queue: List[str] = [changed_node]
        while queue:
            current = queue.pop(0)
            node = self._nodes[current]
            for dep in node.dependents:
                if dep not in visited:
                    if not self._nodes[dep].locked:
                        affected.append(dep)
                        visited.add(dep)
                        queue.append(dep)
                    else:
                        logger.info("节点 %s 已锁定,跳过", dep)
        return affected

    def compute_affected_detail(self, changed_node: str) -> dict:
        """计算受影响节点详情,返回受影响和不受影响的分类。"""
        affected = self.compute_affected(changed_node)
        affected_set = set(affected)
        unaffected: List[str] = []
        for nid, node in self._nodes.items():
            if nid != changed_node and nid not in affected_set:
                unaffected.append(nid)
        return {
            "changed": changed_node,
            "affected": affected,
            "unaffected": sorted(unaffected),
            "affected_labels": [self._nodes[a].label or a for a in affected],
            "unaffected_labels": [self._nodes[u].label or u for u in sorted(unaffected)],
        }

    def lock_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            self._nodes[node_id].locked = True

    def unlock_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            self._nodes[node_id].locked = False

    def bump_version(self, node_id: str) -> int:
        """节点版本号 +1,返回新版本号。"""
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(node_id=node_id, node_type="custom")
        self._nodes[node_id].version += 1
        return self._nodes[node_id].version

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
        }


dependency_graph = DependencyGraph()
