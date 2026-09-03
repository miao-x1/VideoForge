"""PromptEngineeringAgent:将分镜基础 Prompt 增强为专业、结构化、模型感知的 Prompt。

核心职责:
1. 接收 Storyboard 的基础 image_prompt/video_prompt
2. 结合 CreativeIntent 的视觉参数增强每个 shot 的 Prompt
3. 根据目标视频模型的能力生成模型专用 Prompt
4. 生成 Negative Prompt(模型支持时)
5. 输出结构化 Prompt 供 UI 检查和修改

这是 VideoForge 的核心能力之一:
用户不需要学习 Prompt Engineering,系统负责把创意变成专业可执行的生成指令。
"""
from __future__ import annotations

from ..core.logging import logger
from ..models.state import VideoGenerationState
from ..router import registry
from ..schemas.structured_prompt import PromptEngineeringResult, StructuredPrompt
from .base import BaseAgent


class PromptEngineeringAgent(BaseAgent):
    name = "prompt_engineering"

    async def run(self, state: VideoGenerationState, *, feedback: str | None = None) -> None:
        if state.storyboard is None:
            raise RuntimeError("PromptEngineeringAgent 缺少上游 storyboard")
        if not state.storyboard.shots:
            raise RuntimeError("PromptEngineeringAgent: storyboard 无 shots")

        model_info = self._get_model_info(state)
        context = self._build_context(state, model_info)
        # Decision Loop:用户重新编译时表达"哪里不满意"(如"人物不够真实")
        if feedback:
            context["user_feedback"] = feedback

        data = await self.llm.generate(task="prompt_engineering", context=context)

        result = PromptEngineeringResult(**data)

        # 用增强后的 Prompt 覆盖 storyboard 的基础 Prompt
        self._apply_enhanced_prompts(state, result)

        state.prompt_engineering_result = result.model_dump()
        logger.info(
            "Prompt Engineering 完成: %d 个镜头, 模型=%s, notes=%s",
            len(result.prompts), result.model_id, result.compilation_notes,
        )
        for p in result.prompts:
            logger.info(
                "  shot%d: raw_image=%s... raw_video=%s... neg=%s",
                p.shot_index,
                p.raw_image_prompt[:60] if p.raw_image_prompt else "",
                p.raw_video_prompt[:60] if p.raw_video_prompt else "",
                "有" if p.negative_prompt else "无",
            )

    @staticmethod
    def _get_model_info(state: VideoGenerationState) -> dict:
        """获取目标视频模型信息。"""
        model_id = ""
        model_name = state.model_used or ""
        capabilities: dict = {}

        if state.routing_decision:
            model_id = state.routing_decision.get("selected_model_id", "")
            model_name = state.routing_decision.get("selected_model", model_name)

        if model_id:
            entry = registry.get(model_id)
            if entry:
                capabilities = {
                    "supports_negative_prompt": entry.supports_negative_prompt,
                    "supports_reference_image": entry.supports_reference_image,
                    "supports_image_to_video": entry.supports_image_to_video,
                    "supports_text_to_video": entry.supports_text_to_video,
                    "max_duration": entry.capabilities.get("max_duration", 15),
                    "max_resolution": entry.capabilities.get("max_resolution", "720P"),
                }
                model_name = entry.model_name

        return {
            "model_id": model_id,
            "model_name": model_name,
            "capabilities": capabilities,
        }

    @staticmethod
    def _build_context(state: VideoGenerationState, model_info: dict) -> dict:
        """构建 LLM context。"""
        context: dict = {
            "storyboard": state.storyboard.model_dump(),
            "model_info": model_info,
            "model_capabilities": model_info.get("capabilities", {}),
        }
        if state.creative_intent:
            context["creative_intent"] = state.creative_intent.model_dump()
        if state.spec:
            from .prompt_compiler import PromptCompiler
            visual_directives = PromptCompiler.compile_visual_directives(state.spec)
            if visual_directives:
                context["visual_directives"] = visual_directives
        return context

    @staticmethod
    def _apply_enhanced_prompts(state: VideoGenerationState, result: PromptEngineeringResult) -> None:
        """用增强后的 Prompt 覆盖 storyboard 的基础 Prompt。"""
        prompt_map = {p.shot_index: p for p in result.prompts}
        for i, shot in enumerate(state.storyboard.shots):
            sp = prompt_map.get(i)
            if sp:
                if sp.raw_image_prompt:
                    shot.image_prompt = sp.raw_image_prompt
                if sp.raw_video_prompt:
                    shot.video_prompt = sp.raw_video_prompt
                if sp.negative_prompt:
                    shot.negative_prompt = sp.negative_prompt
