"""局部重生成时的单镜头 Prompt 编译上下文构建。

复用 PromptEngineeringAgent 的上下文契约,但 storyboard 只包含被修改的单个镜头,
使 LLM 只重新编译该镜头的 Prompt(依赖图局部重算)。
"""
from __future__ import annotations

from ..models.state import VideoGenerationState
from ..router import registry


def build_single_shot_context(state: VideoGenerationState, shot_index: int) -> dict:
    """构建单镜头 prompt_engineering 上下文(模型感知)。"""
    shot = state.storyboard.shots[shot_index]
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

    context: dict = {
        # 关键:仅包含被修改的镜头(shot_index 保持原索引)
        "storyboard": {"shots": [shot.model_dump()]},
        "shot_index": shot_index,
        "model_info": {"model_id": model_id, "model_name": model_name, "capabilities": capabilities},
        "model_capabilities": capabilities,
    }
    if state.creative_intent:
        context["creative_intent"] = state.creative_intent.model_dump()
    if state.spec:
        from ..agents.prompt_compiler import PromptCompiler
        visual_directives = PromptCompiler.compile_visual_directives(state.spec)
        if visual_directives:
            context["visual_directives"] = visual_directives
    return context
