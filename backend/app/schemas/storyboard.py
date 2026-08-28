"""分镜阶段输出：Storyboard。

由 StoryboardAgent 将脚本拆解为可被 Generator 直接消费的统一中间数据结构。
后续替换不同文生图/文生视频模型时，仅需让对应 Provider 解析 image_prompt/video_prompt，
Storyboard 本身与 Agent 层契约保持稳定。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StoryboardShot(BaseModel):
    scene_id: int = Field(..., description="对应脚本场景编号")
    duration: int = Field(..., description="本分镜时长(秒)")
    shot_type: str = Field("", description="镜头景别，如 medium shot / close-up")
    camera_movement: str = Field("", description="镜头运动，如 slow push in")
    visual_description: str = Field("", description="画面描述")
    character_action: str = Field("", description="角色动作")
    dialogue: str = Field("", description="对白")
    voiceover: str = Field("", description="旁白")
    background_music: str = Field("", description="背景音乐类型")
    sound_effect: str = Field("", description="音效")
    image_prompt: str = Field("", description="文生图提示词")
    video_prompt: str = Field("", description="文生视频提示词")
    subtitle: str = Field("", description="字幕文本(精炼短句,适合屏幕显示)")
    transition: str = Field("fade", description="转场效果:fade / cut / dissolve / slide")
    emotion: str = Field("", description="情绪基调:neutral / surprise / humor / tension / calm")
    # 运行时填充：素材路径
    image_path: Optional[str] = Field(None, description="生成图片的本地路径(关键帧,也作为 I2V 首帧输入)")
    audio_path: Optional[str] = Field(None, description="生成旁白的本地路径")
    video_path: Optional[str] = Field(None, description="I2V 生成的动态视频片段路径(有则优先于 image_path+Ken Burns)")


class Storyboard(BaseModel):
    shots: List[StoryboardShot] = Field(default_factory=list)
