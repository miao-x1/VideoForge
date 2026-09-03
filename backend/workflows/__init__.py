"""Workflow 层:Agent 与 ComfyUI 之间的隔离层。

架构:
  Agent(业务参数) → Capability Router(选 Workflow) → Registry(定位) 
  → Adapter(业务参数→Workflow参数) → ComfyService(云端调用) → ComfyUI → Model

Agent 永远不接触 Workflow JSON / 节点 ID / KSampler 等底层细节。
"""
from .schemas import WorkflowConfig
from .registry import workflow_registry, WorkflowRegistry

__all__ = ["WorkflowConfig", "workflow_registry", "WorkflowRegistry"]
