"""RequirementAgent:深度理解用户自然语言创意,输出 CreativeIntent + StructuredRequirement。

理解原则:
- 不只做字面提取,要理解用户真正想达到的创作效果
- 识别用户未明确说出但合理的创作需求
- 不强制所有视频都必须存在"人物"
"""
from __future__ import annotations

from ..core.logging import logger
from ..models.state import VideoGenerationState
from ..schemas.creative_intent import CreativeIntent
from ..schemas.requirement import StructuredRequirement
from .base import BaseAgent


class RequirementAgent(BaseAgent):
    name = "requirement"

    async def run(self, state: VideoGenerationState, *, project_memory: dict | None = None) -> None:
        # 用户已在"创作方案"环节确认过意图:确认结果为权威输入,跳过重新理解
        if state.creative_intent is not None and state.requirement is not None:
            logger.info("使用用户已确认的创作意图,跳过需求重新理解")
            return

        context = self._build_context(state)
        # 项目记忆继承:同项目新任务自动继承系列设定(主体/场景/风格),保持内容一致性
        if project_memory:
            from ..services.project_memory import build_memory_hints
            hints = build_memory_hints(project_memory)
            if hints:
                context["project_memory"] = hints
                logger.info("注入项目记忆: %s", ", ".join(hints.keys()))
        data = await self.llm.generate(task="requirement", context=context)

        creative_data = data.get("creative_intent", {})
        req_data = data.get("requirement", data)

        if creative_data:
            state.creative_intent = CreativeIntent(**creative_data)
            logger.info(
                "CreativeIntent 解析完成: concept=%s subject=%s scene=%s emotion=%s visual_style=%s lighting=%s",
                state.creative_intent.concept,
                state.creative_intent.subject,
                state.creative_intent.scene,
                state.creative_intent.emotion,
                state.creative_intent.visual_style,
                state.creative_intent.lighting,
            )
            if state.creative_intent.inferred_needs:
                for need in state.creative_intent.inferred_needs:
                    logger.info("  推断需求: %s", need)

        state.requirement = StructuredRequirement(**req_data)
        state.duration = state.requirement.duration
        if state.requirement.style:
            state.style = state.requirement.style
        logger.info(
            "StructuredRequirement 解析完成: topic=%s genre=%s duration=%ds style=%s characters=%d scenes=%d",
            state.requirement.topic, state.requirement.genre,
            state.requirement.duration, state.requirement.style,
            len(state.requirement.characters), len(state.requirement.scenes),
        )

    @staticmethod
    def _build_context(state: VideoGenerationState) -> dict:
        if state.spec:
            from .prompt_compiler import PromptCompiler
            context = PromptCompiler.compile(state.spec)
        else:
            context = {
                "user_input": state.user_input,
                "duration": state.duration,
                "style": state.style,
                "aspect_ratio": state.aspect_ratio,
            }
        if state.multimodal_context:
            context["multimodal_context"] = state.multimodal_context
        return context
