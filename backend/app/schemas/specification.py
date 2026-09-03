"""视频创作规格：用户创作意图的完整结构化表达。

替代扁平的 StructuredRequirement，支持创作元素/环境/镜头/动作/音频/参考素材等多维度。
所有字段允许为空 — 用户可以只输入一句话直接生成。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── 枚举 ──

class CreativeElementType(str, Enum):
    CHARACTER = "character"
    ANIMAL = "animal"
    VEHICLE = "vehicle"
    PRODUCT = "product"
    BUILDING = "building"
    LANDSCAPE = "landscape"
    OBJECT = "object"
    CREATURE = "creature"
    ABSTRACT = "abstract"
    CUSTOM = "custom"


class ReferenceType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    URL = "url"


class ReferencePurpose(str, Enum):
    SUBJECT = "subject"
    SCENE = "scene"
    STYLE = "style"
    COMPOSITION = "composition"
    COLOR = "color"
    ACTION = "action"
    OVERALL = "overall"
    CAMERA = "camera"
    MOVEMENT = "movement"
    RHYTHM = "rhythm"


# ── 创作元素 ──

class CreativeElement(BaseModel):
    """创作元素：可多实例、可多类型、全部可选。"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    type: CreativeElementType = CreativeElementType.CUSTOM
    name: str = ""
    description: str = ""
    attributes: Dict[str, Any] = Field(default_factory=dict)
    action: str = ""
    reference_asset_id: Optional[str] = None
    sort_order: int = 0


# ── 参考素材 ──

class ReferenceAsset(BaseModel):
    """参考素材：带用途分类的素材引用。"""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    type: ReferenceType = ReferenceType.IMAGE
    source: str = ""
    purpose: ReferencePurpose = ReferencePurpose.OVERALL
    thumbnail: str = ""
    description: str = ""


# ── 环境与场景 ──

class Environment(BaseModel):
    """场景与环境（全部可选）。"""
    location: str = ""
    time_of_day: str = ""
    weather: str = ""
    lighting: str = ""
    lighting_type: str = ""  # natural / studio / neon / candlelight / mixed
    atmosphere: str = ""
    color_palette: str = ""  # 主色调,如 "warm orange and deep blue"
    color_temperature: str = ""  # 色温,如 "warm 3200K" / "cool 5600K" / "neutral"
    color_grading: str = ""  # 调色风格,如 "cinematic teal-orange" / "desaturated" / "vivid"


# ── 叙事 ──

class Narrative(BaseModel):
    """叙事结构。"""
    structure: str = ""  # linear / non-linear / montage / tutorial
    theme: str = ""
    mood: str = ""


# ── 运动控制 ──

class MotionControl(BaseModel):
    """动作与运动控制（三维度分离）。"""
    subject_motion: str = ""
    camera_motion: str = ""
    environment_motion: str = ""


# ── 视觉风格 ──

class StyleItem(BaseModel):
    """风格项（支持多选组合）。"""
    category: str = ""
    name: str = ""


# ── 镜头 ──

class CameraControl(BaseModel):
    """镜头系统。"""
    shot_type: str = ""
    angle: str = ""
    movement: str = ""
    rhythm: str = ""


# ── 音频 ──

class AudioControl(BaseModel):
    """音频系统。"""
    bgm_mode: str = "auto"
    bgm_path: str = ""
    sfx_mode: str = "auto"
    sfx_description: str = ""
    dialogue_mode: str = "auto"
    dialogue_text: str = ""
    voice_style: str = ""


# ── 高级参数 ──

class AdvancedParams(BaseModel):
    """高级参数。"""
    quality_priority: str = "balanced"
    compliance_enabled: bool = True
    custom_params: Dict[str, Any] = Field(default_factory=dict)


# ── VideoSpecification 主结构 ──

class VideoSpecification(BaseModel):
    """视频创作规格：用户创作意图的完整结构化表达。

    所有字段允许为空 — 用户可以只输入 prompt 直接生成。
    替代扁平的 StructuredRequirement，作为 Pipeline 的统一输入。
    """
    # ── 基础 ──
    prompt: str = ""
    duration: int = 30
    aspect_ratio: str = "9:16"
    target_platform: str = ""

    # ── 创作元素 ──
    creative_elements: List[CreativeElement] = Field(default_factory=list)

    # ── 环境与场景 ──
    environment: Optional[Environment] = None

    # ── 叙事 ──
    narrative: Optional[Narrative] = None

    # ── 运动控制 ──
    motion: Optional[MotionControl] = None

    # ── 视觉风格（多选组合）──
    visual_style: List[StyleItem] = Field(default_factory=list)
    custom_style: str = ""

    # ── 镜头 ──
    camera: Optional[CameraControl] = None

    # ── 音频 ──
    audio: Optional[AudioControl] = None

    # ── 参考素材 ──
    references: List[ReferenceAsset] = Field(default_factory=list)

    # ── 高级参数 ──
    advanced: Optional[AdvancedParams] = None

    # ── 模型 ──
    preferred_model: str = ""
    routing_decision: Optional[Dict[str, Any]] = None

    def to_requirement_context(self) -> Dict[str, Any]:
        """转换为 RequirementAgent 可消费的 context（由 PromptCompiler 调用）。"""
        from ..agents.prompt_compiler import PromptCompiler
        return PromptCompiler.compile(self)
