"""Workflow Registry:加载并索引所有已接入的 ComfyUI Workflow。

目录约定:
  workflows/<family>/<name>.json          官方模板(UI Format)
  workflows/<family>/<name>.config.json   业务输入声明与注入点
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.core.logging import logger
from .schemas import WORKFLOWS_ROOT, WorkflowConfig


class WorkflowNotFoundError(Exception):
    """请求的 Workflow 不存在。"""


class WorkflowRegistry:
    def __init__(self, root: Path = WORKFLOWS_ROOT) -> None:
        self.root = root
        self._configs: dict[str, WorkflowConfig] = {}
        self._dirs: dict[str, Path] = {}
        self._workflows: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        for config_path in self.root.rglob("*.config.json"):
            try:
                config = WorkflowConfig(**json.loads(config_path.read_text(encoding="utf-8")))
                workflow_path = config_path.parent / config.file
                if not workflow_path.exists():
                    logger.warning("Workflow 文件缺失,跳过: %s", workflow_path)
                    continue
                self._configs[config.workflow_id] = config
                self._dirs[config.workflow_id] = config_path.parent
            except Exception as e:
                logger.warning("Workflow 配置加载失败 %s: %s", config_path, e)

    def list_workflows(self) -> list[WorkflowConfig]:
        return list(self._configs.values())

    def get(self, workflow_id: str) -> WorkflowConfig:
        config = self._configs.get(workflow_id)
        if config is None:
            raise WorkflowNotFoundError(f"Workflow 不存在: {workflow_id}")
        return config

    def find_by_category(self, category: str) -> Optional[WorkflowConfig]:
        for config in self._configs.values():
            if config.category == category:
                return config
        return None

    def load_workflow(self, workflow_id: str) -> dict:
        """加载并缓存 Workflow JSON(UI Format)。"""
        if workflow_id not in self._workflows:
            config = self.get(workflow_id)
            path = self._dirs[workflow_id] / config.file
            self._workflows[workflow_id] = json.loads(path.read_text(encoding="utf-8"))
        return self._workflows[workflow_id]


workflow_registry = WorkflowRegistry()
