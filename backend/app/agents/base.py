"""Agent 基类。

所有 Agent 拥有统一接口 run(state),Orchestrator 无需区分具体 Agent。
每个 Agent 只负责把自身阶段的产物写入 state,不关心后续编排。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.state import VideoGenerationState
from ..providers.llm.base import LLMProvider


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    @abstractmethod
    async def run(self, state: VideoGenerationState) -> None:
        """执行本阶段任务,产物写入 state。失败应抛异常,由 Orchestrator 捕获。"""
