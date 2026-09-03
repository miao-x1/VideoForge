"""StructuredPrompt:Prompt Engineering Agent 的输出。

将分镜的基础 image_prompt/video_prompt 增强为专业结构化提示词,
包含主体/环境/动作/构图/镜头/光线/风格/情绪等维度,
并生成模型专用的 raw prompt 和 negative prompt。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StructuredPrompt(BaseModel):
    """单个镜头的结构化 Prompt。"""

    model_config = {"protected_namespaces": ()}

    shot_index: int = Field(..., description="镜头序号")

    # 结构化维度
    subject: str = Field("", description="主体描述")
    environment: str = Field("", description="环境描述")
    action: str = Field("", description="动作描述")
    composition: str = Field("", description="画面构图:close-up/medium shot/wide shot/full shot/over-the-shoulder/top-down/low-angle/symmetrical/rule of thirds")
    camera: str = Field("", description="镜头运动:static/pan/tilt/dolly/tracking/orbit/zoom/handheld/crane/drone")
    lighting: str = Field("", description="光线:natural/soft/hard/backlight/rim light/golden hour/neon/studio/cinematic/low-key/high-key")
    visual_style: str = Field("", description="视觉风格")
    emotion: str = Field("", description="情绪基调")
    sound: str = Field("", description="声音描述")
    rhythm: str = Field("", description="节奏描述")

    # 模型专用 Prompt
    raw_image_prompt: str = Field("", description="最终发送给图片模型的英文 Prompt")
    raw_video_prompt: str = Field("", description="最终发送给视频模型的英文 Prompt")
    negative_prompt: str = Field("", description="负面提示词(模型不支持时为空)")

    # 生成参数
    generation_params: dict = Field(default_factory=dict, description="模型生成参数(如 seed/steps/guidance_scale)")

    # 审计
    model_id: str = Field("", description="目标模型 ID")
    model_convention: str = Field("", description="模型 Prompt 约定说明")


class PromptEngineeringResult(BaseModel):
    """Prompt Engineering Agent 的完整输出。"""

    model_config = {"protected_namespaces": ()}

    prompts: List[StructuredPrompt] = Field(default_factory=list)
    model_id: str = Field("", description="目标视频模型 ID")
    model_capabilities: dict = Field(default_factory=dict, description="模型能力摘要")
    compilation_notes: str = Field("", description="编译说明(如适配了哪些模型特性)")

    def to_dict(self) -> dict:
        return self.model_dump()
