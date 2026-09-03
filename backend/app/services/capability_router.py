"""Capability Router:任务类型 → Workflow。

Agent 只声明业务任务类型(text_to_video / image_to_video / reference_to_video / ...),
由本模块选择具体 Workflow。Agent 不感知节点与模型细节。
"""
from __future__ import annotations

from typing import Optional

from app.core.logging import logger
from workflows.registry import workflow_registry, WorkflowNotFoundError
from workflows.schemas import WorkflowConfig


class WorkflowNotAvailableError(Exception):
    """该任务类型当前没有可用的 Workflow。"""


# 任务类型 → 默认 Workflow ID
TASK_TYPE_TO_WORKFLOW = {
    "text_to_video": "minimax_h3_t2v_v1",
    "image_to_video": "minimax_h3_i2v_v1",
    "reference_to_video": "minimax_h3_r2v_v1",
}


def select_workflow(
    task_type: str,
    *,
    preferred_workflow: Optional[str] = None,
) -> WorkflowConfig:
    """根据任务类型选择 Workflow。

    Args:
        task_type: 业务任务类型(text_to_video/image_to_video/reference_to_video)
        preferred_workflow: 指定 Workflow ID(专业用户手动选择)

    Returns:
        WorkflowConfig

    Raises:
        WorkflowNotAvailableError: 无可用 Workflow
    """
    if preferred_workflow:
        try:
            config = workflow_registry.get(preferred_workflow)
            logger.info("Capability Router: 手动指定 workflow=%s (%s)", preferred_workflow, task_type)
            return config
        except WorkflowNotFoundError:
            raise WorkflowNotAvailableError(f"指定的 Workflow 不存在: {preferred_workflow}")

    workflow_id = TASK_TYPE_TO_WORKFLOW.get(task_type)
    if not workflow_id:
        raise WorkflowNotAvailableError(f"暂无支持该任务类型的 Workflow: {task_type}")
    try:
        config = workflow_registry.get(workflow_id)
    except WorkflowNotFoundError as e:
        raise WorkflowNotAvailableError(str(e))
    logger.info("Capability Router: task=%s → workflow=%s", task_type, workflow_id)
    return config
