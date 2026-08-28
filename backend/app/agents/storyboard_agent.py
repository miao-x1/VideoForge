"""StoryboardAgent:将脚本拆解为可被 Generator 直接消费的分镜。"""
from __future__ import annotations

from ..models.state import VideoGenerationState
from ..schemas.storyboard import Storyboard
from .base import BaseAgent


class StoryboardAgent(BaseAgent):
    name = "storyboard"

    async def run(self, state: VideoGenerationState) -> None:
        if state.script is None:
            raise RuntimeError("StoryboardAgent 缺少上游 script")
        context = {"script": state.script.model_dump()}
        data = await self.llm.generate(task="storyboard", context=context)
        state.storyboard = Storyboard(**data)
