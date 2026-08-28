"""需求理解阶段输出：StructuredRequirement。

由 RequirementAgent 从用户自然语言创意提取，作为整个 Pipeline 的起点。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Character(BaseModel):
    name: str = Field(..., description="角色名称")
    description: str = Field("", description="角色外貌/身份简介")


class Scene(BaseModel):
    location: str = Field(..., description="场景地点")
    description: str = Field("", description="场景描述")


class StructuredRequirement(BaseModel):
    topic: str = Field(..., description="视频主题")
    genre: str = Field("", description="内容类型/题材，如 轻喜剧")
    duration: int = Field(30, description="目标视频时长(秒)")
    style: str = Field("", description="视频风格，如 古装喜剧")
    audience: str = Field("", description="目标受众")
    characters: List[Character] = Field(default_factory=list)
    scenes: List[Scene] = Field(default_factory=list)
    tone: str = Field("", description="情绪基调")
    visual_style: str = Field("", description="视觉风格")
    output_requirement: Optional[str] = Field(None, description="输出要求，如分辨率/比例")
