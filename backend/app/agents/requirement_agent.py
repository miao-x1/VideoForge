"""RequirementAgent:理解用户自然语言创意,输出 StructuredRequirement。"""
from __future__ import annotations

from ..models.state import VideoGenerationState
from ..schemas.requirement import StructuredRequirement
from .base import BaseAgent


class RequirementAgent(BaseAgent):
    name = "requirement"

    async def run(self, state: VideoGenerationState) -> None:
        context = {
            "user_input": state.user_input,
            "duration": state.duration,
            "style": state.style,
        }
        data = await self.llm.generate(task="requirement", context=context)
        state.requirement = StructuredRequirement(**data)
        # 回填解析出的时长/风格,保证后续阶段使用结构化结果
        state.duration = state.requirement.duration
        state.style = state.requirement.style
