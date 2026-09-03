"""Creative Intent:用户创意的结构化理解结果。

由 RequirementAgent 从用户自然语言提取,作为整个 Pipeline 的创意蓝图。
与 StructuredRequirement 互补:StructuredRequirement 面向脚本生成,
CreativeIntent 面向用户展示和 Prompt Engineering。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CreativeIntent(BaseModel):
    """AI 对用户创意的深度理解,包含显式和隐式推断的创作要素。"""

    concept: str = Field(..., description="创意概念:一句话概括用户想做什么")
    subject: str = Field("", description="主体:人/动物/产品/汽车/建筑/物体/机器人/虚构生物/自然环境/食物/角色/无明确主体")
    subject_description: str = Field("", description="主体详细描述(外貌/特征/状态)")
    scene: str = Field("", description="场景:城市/街道/房间/森林/海边/宫殿/办公室/商场/太空/虚拟世界/自然环境/自定义")
    scene_description: str = Field("", description="场景详细描述(氛围/细节)")
    action: str = Field("", description="主体动作:走路/奔跑/跳跃/转身/拿起物体/打开门/观察/战斗/驾驶/飞行/产品展示/镜头运动")
    action_description: str = Field("", description="动作详细描述")
    emotion: str = Field("", description="情绪基调:惊讶/幽默/紧张/平静/悲伤/兴奋/恐惧/温馨")
    visual_style: str = Field("", description="视觉风格:真人写实/电影感/纪录片/商业广告/Vlog/3D动画/2D动画/日漫/国漫/赛博朋克/水墨/像素")
    camera_style: str = Field("", description="镜头风格:跟拍/固定/摇摄/俯拍/低角度/对称构图/三分法")
    lighting: str = Field("", description="光线:自然光/柔光/硬光/逆光/轮廓光/黄金时刻/霓虹/影棚/电影感/低调/高调")
    color_mood: str = Field("", description="色彩情绪:暖色调/冷色调/高饱和/低饱和/单色/对比色")
    duration: int = Field(15, description="建议时长(秒)")
    aspect_ratio: str = Field("9:16", description="建议比例:9:16/16:9/1:1/4:3")
    references: List[str] = Field(default_factory=list, description="参考素材描述列表")
    creative_goal: str = Field("", description="创作目标:用户最终想达到什么效果")
    constraints: List[str] = Field(default_factory=list, description="创作约束:用户明确或隐含的限制条件")
    inferred_needs: List[str] = Field(default_factory=list, description="AI 推断的合理创作需求(用户未明确说出但合理)")

    def to_dict(self) -> dict:
        return self.model_dump()
