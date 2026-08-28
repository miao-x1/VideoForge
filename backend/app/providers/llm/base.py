"""LLM Provider 抽象接口。

所有 Agent 通过本接口获取结构化 JSON 结果，不直接耦合具体 LLM 服务。
替换模型(如 DashScope/DeepSeek)时，仅需新增一个实现并切换 settings.llm_provider。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, *, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """根据任务类型与上游上下文，生成结构化 JSON(已 dict 化)。

        task 取值: requirement | script | storyboard
        context 透传上游产物，例如:
          - requirement: {"user_input": "...", "duration": 30, "style": "..."}
          - script:      {"requirement": StructuredRequirement.dict()}
          - storyboard:  {"script": VideoScript.dict()}
        """
