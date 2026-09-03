"""LLM Provider 抽象接口。

所有 Agent 通过本接口获取结构化 JSON 结果，不直接耦合具体 LLM 服务。
替换模型(如 DashScope/DeepSeek)时，仅需新增一个实现并切换 settings.llm_provider。
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict

from ..base import ModelProvider


class LLMProvider(ModelProvider):
    """文本/LLM 模型 Provider 抽象(对应任务书 TextModelProvider)。"""

    provider_type = "text"

    @abstractmethod
    async def generate(self, *, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """根据任务类型与上游上下文，生成结构化 JSON(已 dict 化)。

        task 取值: requirement | script | storyboard
        context 透传上游产物，例如:
          - requirement: {"user_input": "...", "duration": 30, "style": "..."}
          - script:      {"requirement": StructuredRequirement.dict()}
          - storyboard:  {"script": VideoScript.dict()}
        """

    async def describe_image(self, image_path: str, prompt: str = "描述这张图片的内容、主体、风格、色调和氛围") -> str:
        """图片理解(多模态):返回图片的文本描述,不支持时抛 NotImplementedError。"""
        raise NotImplementedError(f"{type(self).__name__} 不支持图片理解")


# 任务书语义别名: TextModelProvider 即 LLMProvider
TextModelProvider = LLMProvider
