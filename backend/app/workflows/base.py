"""Workflow 层基类。

Workflow 与 Agent 的分工(任务书架构原则):
- Agent/LLM 层:理解、推理、规划、决策、状态管理、质量判断
- Workflow 层:把**已经确定**的任务按固定步骤执行(无 LLM 调用、无创作决策)
- Model 层:真正的图片/视频/音频/文本生成(Provider)
- Infrastructure 层:文件、DB、任务队列、缓存、API、状态持久化

每个 Workflow 接收 VideoGenerationState,读取 Agent 已决策好的规划
(storyboard / project_state),调用 Model 层 Provider 执行生成,
把产物路径与资产台账写回 state。执行中发生的"该选什么模式/模型"
类决策读取 project_state 中的 Agent 决策结果,Workflow 不做创作判断。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.state import VideoGenerationState


class BaseWorkflow(ABC):
    """固定步骤执行流基类。"""

    name: str = "workflow"

    @abstractmethod
    async def run(self, state: VideoGenerationState) -> None:
        """执行该 Workflow 的完整固定步骤,产物写回 state。"""
        raise NotImplementedError
