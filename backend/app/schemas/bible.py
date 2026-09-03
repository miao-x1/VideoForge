"""Bible 层:Character Bible / World Bible / Style Bible。

由 Agent 层(CharacterAgent / WorldAgent)在作品生命周期内建立与维护:
- CharacterBible: 人物设定档案。每个镜头生成前必须读取,保证同一人物
  在不同镜头/场景中的脸、发型、服装、身份一致。
- WorldBible: 世界观/场景设定(时代/地点/建筑/天气/时间/道具)。
- StyleBible: 视觉风格设定(画面风格/摄影/色调/光线基调),全片统一。

这些结构只描述"设定事实",不包含生成逻辑;Agent 负责写入,
Workflow / PromptCompiler 负责读取消费。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CharacterRelation(BaseModel):
    """人物关系条目。"""

    target_name: str = Field(..., description="关系对象的人物姓名")
    relation: str = Field(..., description="关系类型,如 恋人/父女/敌对/主仆/挚友")
    description: str = Field("", description="关系描述:关系背景与当前状态")


class CharacterBible(BaseModel):
    """单个人物的完整设定档案(Character Bible)。"""

    character_id: str = Field(..., description="人物稳定 ID,如 character_001")
    name: str = Field(..., description="人物姓名/称呼")
    age: str = Field("", description="年龄(可写年龄段,如 少女/约二十岁)")
    gender: str = Field("", description="性别")
    identity: str = Field("", description="身份/职业/社会角色")
    personality: str = Field("", description="性格特点")
    appearance: str = Field("", description="外貌:脸型/五官/辨识特征")
    hairstyle: str = Field("", description="发型与发色")
    clothing: str = Field("", description="服装:款式/颜色/材质(当前造型基线)")
    body_type: str = Field("", description="体型")
    speech_style: str = Field("", description="说话方式:语速/口癖/语气")
    emotion_traits: str = Field("", description="情绪特点:常态情绪与反应模式")
    relations: List[CharacterRelation] = Field(default_factory=list, description="人物关系列表")
    background: str = Field("", description="人物背景:身世/经历/动机")
    visual_keywords: List[str] = Field(
        default_factory=list,
        description="视觉一致性关键词:注入每个该人物镜头的提示词(外貌/发型/服装)",
    )
    reference_asset_ids: List[str] = Field(
        default_factory=list,
        description="角色参考图资产 ID(定妆/首镜关键帧),用于 I2V/R2V 人物一致性",
    )
    status: str = Field("active", description="档案状态: active(出场中) / exited(已离场) / background")


class SceneSetting(BaseModel):
    """单个场景的环境设定(World Bible 内)。"""

    scene_key: str = Field(..., description="场景稳定标识,如 scene_01 或 江南青石街道")
    name: str = Field("", description="场景名称")
    location: str = Field("", description="地点")
    time_of_day: str = Field("", description="时段:清晨/正午/傍晚/深夜")
    weather: str = Field("", description="天气:晴/阴雨/雪/雾")
    lighting: str = Field("", description="该场景光线:暖黄路灯/冷月光/霓虹")
    description: str = Field("", description="场景环境描述:建筑/陈设/氛围")


class WorldBible(BaseModel):
    """世界观与场景设定(World Bible)。"""

    era: str = Field("", description="时代:古代/民国/现代/近未来/架空")
    region: str = Field("", description="地域/世界:江南/赛博都市/太空殖民地")
    architecture: str = Field("", description="建筑风格体系")
    weather_base: str = Field("", description="全片基线天气(可被具体场景覆盖)")
    time_span: str = Field("", description="故事时间跨度:一夜/三年/一个朝代")
    props_system: List[str] = Field(default_factory=list, description="道具体系:贯穿全片的关键道具")
    world_rules: str = Field("", description="世界观规则(架空/奇幻设定的自洽规则)")
    scenes: List[SceneSetting] = Field(default_factory=list, description="具体场景设定列表")


class StyleBible(BaseModel):
    """视觉风格设定(Style Bible),全片统一的画面基调。"""

    visual_style: str = Field("", description="画面风格:真人写实/电影感/3D动画/国漫/赛博朋克")
    photography_style: str = Field("", description="摄影风格:手持纪实/稳定器运动/固定长镜头")
    color_palette: str = Field("", description="主色调:冷青灰/暖琥珀/黑金")
    color_temperature: str = Field("", description="色温倾向:暖调/冷调/中性")
    saturation: str = Field("", description="饱和度:高饱和/低饱和")
    contrast: str = Field("", description="对比度:高对比/柔和")
    color_grading: str = Field("", description="调色倾向:青橙调/胶片褪色/赛博霓虹")
    lighting_base: str = Field("", description="光线基调:自然光/低调布光/高调明亮")
    lens_language: str = Field("", description="镜头语言基调:浅景深/广角夸张/对称构图")
    texture: str = Field("", description="画面质感:胶片颗粒/数字锐利/动画赛璐璐")
    negative_keywords: List[str] = Field(
        default_factory=list, description="全片负面约束:所有镜头共同规避的元素"
    )


__all__ = [
    "CharacterRelation",
    "CharacterBible",
    "SceneSetting",
    "WorldBible",
    "StyleBible",
]
