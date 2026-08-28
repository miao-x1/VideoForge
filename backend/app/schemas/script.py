"""脚本阶段输出：VideoScript。

由 ScriptAgent 根据 StructuredRequirement 生成，描述视频的整体叙事结构。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ScriptScene(BaseModel):
    scene_id: int = Field(..., description="场景编号")
    duration: int = Field(..., description="本场景时长(秒)")
    location: str = Field("", description="场景地点")
    characters: List[str] = Field(default_factory=list, description="出场角色名称")
    visual: str = Field("", description="画面描述")
    dialogue: str = Field("", description="对白")
    voiceover: str = Field("", description="旁白")


class VideoScript(BaseModel):
    title: str = Field(..., description="视频标题")
    hook: str = Field("", description="开头 Hook，前 3 秒抓人")
    scenes: List[ScriptScene] = Field(default_factory=list)
    ending: Optional[str] = Field(None, description="结尾")
