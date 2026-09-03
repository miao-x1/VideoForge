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
    negative_prompt: str = Field("", description="负面提示词(模型不支持时为空)")
    subtitle: str = Field("", description="字幕文本(精炼短句,适合屏幕显示)")
    subtitle_enabled: bool = Field(True, description="是否烧录该镜头字幕(逐镜头开关)")
    subtitle_font_size: int = Field(0, description="该镜头字幕字号覆盖(0=用全局默认)")
    transition: str = Field("fade", description="转场效果:fade / cut / dissolve / slide")
    emotion: str = Field("", description="情绪基调(镜头开始):neutral / surprise / humor / tension / calm")
    # ---- 镜头连续性字段(ShotPlanner 维护,任务书第六/七节) ----
    characters: List[str] = Field(default_factory=list, description="本镜出场人物名(必须与 Character Bible 姓名一致)")
    location: str = Field("", description="本镜地点(与 World Bible 场景一致)")
    time_of_day: str = Field("", description="本镜时段:清晨/正午/傍晚/深夜")
    lighting: str = Field("", description="本镜光线(在 Style Bible 基调下的场景级细化)")
    emotion_end: str = Field("", description="镜头结束时的情绪(情绪变化:疑惑→惊讶)")
    continuity_in: str = Field("", description="继承上一镜的状态:人物姿态/情绪/服装/道具/天气")
    continuity_out: str = Field("", description="本镜结束后传递给下一镜的状态")
    causal_note: str = Field("", description="叙事因果:为什么本镜会发生(上一镜的什么导致了本镜)")
    desired_mode: str = Field("", description="期望生成模式(由镜头规划决定,空=自动): t2v / i2v / r2v / first_last")
    # 运行时填充：素材路径
    image_path: Optional[str] = Field(None, description="生成图片的本地路径(关键帧,也作为 I2V 首帧输入)")
    audio_path: Optional[str] = Field(None, description="生成旁白的本地路径")
    video_path: Optional[str] = Field(None, description="I2V 生成的动态视频片段路径(有则优先于 image_path+Ken Burns)")
    # 依赖图:锁定节点,局部重生成时跳过
    locked: bool = Field(False, description="是否锁定:锁定后局部重生成不会修改该镜头")


class Storyboard(BaseModel):
    shots: List[StoryboardShot] = Field(default_factory=list)
