"""ScriptAgent:根据 StructuredRequirement 生成完整短视频脚本。"""
from __future__ import annotations

from ..models.state import VideoGenerationState
from ..schemas.script import VideoScript
from .base import BaseAgent


class ScriptAgent(BaseAgent):
    name = "script"

    async def run(self, state: VideoGenerationState) -> None:
        if state.requirement is None:
            raise RuntimeError("ScriptAgent 缺少上游 requirement")
        context = {"requirement": state.requirement.model_dump()}
        data = await self.llm.generate(task="script", context=context)
        state.script = VideoScript(**data)
