"""统一模型注册中心。

所有模型类型 (LLM/Image/Voice/Video/Embedding) 通过本注册中心统一管理，
支持阶段级模型路由和模型感知 Prompt 编译。

设计原则:
- 模型元数据集中管理，不散落在代码中
- 支持动态注册和静态配置
- enabled 和 priority 控制路由范围
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.config import settings
from ..core.logging import logger


@dataclass
class ModelEntry:
    """模型注册条目:描述一个可用的 AI 模型及其全部能力。"""

    model_id: str
    provider: str
    model_name: str
    model_type: str  # reasoning | general_llm | lightweight_llm | text_to_image | image_edit | text_to_video | image_to_video | video_extension | tts | music | embedding
    capabilities: dict = field(default_factory=dict)
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)
    quality_score: float = 5.0  # 0-10
    speed_score: float = 5.0
    cost_score: float = 5.0  # 0=免费, 10=昂贵
    context_length: int = 0
    supported_styles: list[str] = field(default_factory=list)
    supported_durations: list[int] = field(default_factory=list)
    supported_aspect_ratios: list[str] = field(default_factory=lambda: ["9:16", "16:9", "1:1"])
    supports_reference_image: bool = False
    supports_reference_video: bool = False
    supports_audio: bool = False
    supports_video_extension: bool = False
    supports_image_to_video: bool = False
    supports_text_to_video: bool = False
    supports_negative_prompt: bool = False
    enabled: bool = True
    priority: int = 0  # 越大越优先

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "capabilities": self.capabilities,
            "input_types": self.input_types,
            "output_types": self.output_types,
            "quality_score": self.quality_score,
            "speed_score": self.speed_score,
            "cost_score": self.cost_score,
            "context_length": self.context_length,
            "supported_styles": self.supported_styles,
            "supported_durations": self.supported_durations,
            "supported_aspect_ratios": self.supported_aspect_ratios,
            "supports_reference_image": self.supports_reference_image,
            "supports_reference_video": self.supports_reference_video,
            "supports_audio": self.supports_audio,
            "supports_video_extension": self.supports_video_extension,
            "supports_image_to_video": self.supports_image_to_video,
            "supports_text_to_video": self.supports_text_to_video,
            "supports_negative_prompt": self.supports_negative_prompt,
            "enabled": self.enabled,
            "priority": self.priority,
        }


class ModelRegistry:
    """模型注册中心:统一管理所有 AI 模型的元数据和能力。"""

    def __init__(self) -> None:
        self._models: dict[str, ModelEntry] = {}

    def register(self, entry: ModelEntry) -> None:
        self._models[entry.model_id] = entry
        logger.debug("注册模型: %s (%s/%s)", entry.model_id, entry.provider, entry.model_name)

    def get(self, model_id: str) -> Optional[ModelEntry]:
        return self._models.get(model_id)

    def list_all(self) -> list[ModelEntry]:
        return list(self._models.values())

    def list_enabled(self) -> list[ModelEntry]:
        return [m for m in self._models.values() if m.enabled]

    def list_by_type(self, model_type: str) -> list[ModelEntry]:
        return [
            m for m in self._models.values()
            if m.enabled and m.model_type == model_type
        ]

    def list_by_types(self, model_types: list[str]) -> list[ModelEntry]:
        types_set = set(model_types)
        return [
            m for m in self._models.values()
            if m.enabled and m.model_type in types_set
        ]

    def list_by_provider(self, provider: str) -> list[ModelEntry]:
        return [
            m for m in self._models.values()
            if m.enabled and m.provider == provider
        ]


def _register_llm_models(reg: ModelRegistry) -> None:
    """注册 LLM 模型 (推理/通用/轻量)。"""
    key = settings.llm_api_key or settings.dashscope_api_key
    if not key:
        return

    reg.register(ModelEntry(
        model_id="llm-qwen-plus",
        provider="dashscope",
        model_name=settings.llm_model,
        model_type="general_llm",
        capabilities={"json_mode": True, "vision": False},
        input_types=["text"],
        output_types=["text", "json"],
        quality_score=7.0,
        speed_score=7.0,
        cost_score=4.0,
        context_length=131072,
        supported_styles=["realistic", "cinematic", "animation", "documentary"],
        enabled=True,
        priority=10,
    ))

    reg.register(ModelEntry(
        model_id="llm-qwen-max",
        provider="dashscope",
        model_name="qwen-max",
        model_type="reasoning",
        capabilities={"json_mode": True, "vision": False},
        input_types=["text"],
        output_types=["text", "json"],
        quality_score=9.0,
        speed_score=5.0,
        cost_score=7.0,
        context_length=32768,
        supported_styles=["realistic", "cinematic", "animation", "documentary", "commercial"],
        enabled=True,
        priority=15,
    ))

    reg.register(ModelEntry(
        model_id="llm-qwen-turbo",
        provider="dashscope",
        model_name="qwen-turbo",
        model_type="lightweight_llm",
        capabilities={"json_mode": True, "vision": False},
        input_types=["text"],
        output_types=["text", "json"],
        quality_score=5.0,
        speed_score=9.0,
        cost_score=2.0,
        context_length=131072,
        enabled=True,
        priority=5,
    ))

    reg.register(ModelEntry(
        model_id="llm-qwen-vl-max",
        provider="dashscope",
        model_name=settings.vl_model,
        model_type="reasoning",
        capabilities={"json_mode": True, "vision": True},
        input_types=["text", "image"],
        output_types=["text", "json"],
        quality_score=9.0,
        speed_score=4.0,
        cost_score=7.0,
        context_length=32768,
        supported_styles=["realistic", "cinematic", "animation"],
        supports_reference_image=True,
        enabled=True,
        priority=12,
    ))


def _register_image_models(reg: ModelRegistry) -> None:
    """注册图片生成模型。"""
    key = settings.llm_api_key or settings.dashscope_api_key
    if not key:
        return

    reg.register(ModelEntry(
        model_id="image-wanx21-turbo",
        provider="dashscope",
        model_name=settings.image_model,
        model_type="text_to_image",
        capabilities={"max_resolution": "1440P"},
        input_types=["text"],
        output_types=["image"],
        quality_score=7.0,
        speed_score=8.0,
        cost_score=3.0,
        supported_styles=["realistic", "cinematic", "animation", "commercial", "cyberpunk"],
        supported_aspect_ratios=["9:16", "16:9", "1:1", "4:3", "3:4"],
        supports_negative_prompt=True,
        enabled=True,
        priority=10,
    ))


def _register_voice_models(reg: ModelRegistry) -> None:
    """注册语音合成模型。"""
    key = settings.llm_api_key or settings.dashscope_api_key
    if not key:
        return

    reg.register(ModelEntry(
        model_id="voice-qwen-tts",
        provider="dashscope",
        model_name=settings.tts_model,
        model_type="tts",
        capabilities={"voice": settings.tts_voice, "language": settings.tts_language},
        input_types=["text"],
        output_types=["audio"],
        quality_score=7.0,
        speed_score=8.0,
        cost_score=3.0,
        supports_audio=True,
        enabled=True,
        priority=10,
    ))


def _register_music_models(reg: ModelRegistry) -> None:
    """注册音乐生成模型。"""
    reg.register(ModelEntry(
        model_id="music-ambient",
        provider="ambient",
        model_name="ambient-generator",
        model_type="music",
        capabilities={"mode": "programmatic"},
        input_types=["text"],
        output_types=["audio"],
        quality_score=4.0,
        speed_score=9.0,
        cost_score=0.0,
        supports_audio=True,
        enabled=True,
        priority=5,
    ))


def _register_video_models(reg: ModelRegistry) -> None:
    """注册视频生成模型。"""
    qwen_key = settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key
    if qwen_key:
        reg.register(ModelEntry(
            model_id="video-qwen-i2v",
            provider="qwen",
            model_name=settings.qwen_video_model,
            model_type="image_to_video",
            capabilities={"max_duration": 15, "max_resolution": "720P"},
            input_types=["image", "text"],
            output_types=["video"],
            quality_score=7.0,
            speed_score=8.0,
            cost_score=4.0,
            supported_durations=[5, 10, 15],
            supported_aspect_ratios=["9:16", "16:9", "1:1"],
            supports_reference_image=True,
            supports_image_to_video=True,
            supports_negative_prompt=False,
            enabled=True,
            priority=10,
        ))

    if settings.minimax_api_key:
        reg.register(ModelEntry(
            model_id="video-minimax-h3-i2v-direct",
            provider="minimax",
            model_name=settings.minimax_video_model,
            model_type="image_to_video",
            capabilities={"max_duration": 15, "max_resolution": "2K"},
            input_types=["image", "text"],
            output_types=["video"],
            quality_score=9.5,
            speed_score=7.0,
            cost_score=6.0,
            supported_durations=[4, 5, 6, 8, 10, 15],
            supported_aspect_ratios=["9:16", "16:9", "1:1", "4:3", "3:4"],
            supports_reference_image=True,
            supports_image_to_video=True,
            supports_negative_prompt=False,
            enabled=True,
            priority=13,
        ))

    # MiniMax H3(云端 ComfyUI 官方 Workflow):T2V / I2V / R2V
    if settings.comfy_api_key:
        common = dict(
            provider="comfy",
            model_name="MiniMax-H3",
            output_types=["video"],
            quality_score=9.5,
            speed_score=6.0,
            cost_score=6.0,
            supported_durations=[5, 10],
            supported_aspect_ratios=["9:16", "16:9", "1:1"],
            supports_reference_image=True,
            supports_image_to_video=True,
            supports_negative_prompt=False,
            enabled=True,
        )
        reg.register(ModelEntry(
            model_id="video-minimax-h3-i2v",
            model_type="image_to_video",
            capabilities={"max_duration": 10, "max_resolution": "1080P", "workflow": "minimax_h3_i2v_v1"},
            priority=12,
            **common,
        ))
        reg.register(ModelEntry(
            model_id="video-minimax-h3-t2v",
            model_type="text_to_video",
            capabilities={"max_duration": 10, "max_resolution": "1080P", "workflow": "minimax_h3_t2v_v1"},
            input_types=["text"],
            priority=9,
            **common,
        ))
        reg.register(ModelEntry(
            model_id="video-minimax-h3-r2v",
            model_type="reference_to_video",
            capabilities={"max_duration": 10, "max_resolution": "1080P", "workflow": "minimax_h3_r2v_v1"},
            input_types=["image", "text"],
            priority=11,
            **common,
        ))


def _register_embedding_models(reg: ModelRegistry) -> None:
    """注册 Embedding 模型。"""
    key = settings.llm_api_key or settings.dashscope_api_key
    if not key:
        return

    reg.register(ModelEntry(
        model_id="embedding-text-v3",
        provider="dashscope",
        model_name=settings.embedding_model,
        model_type="embedding",
        capabilities={"dim": settings.embedding_dim},
        input_types=["text"],
        output_types=["vector"],
        quality_score=8.0,
        speed_score=7.0,
        cost_score=2.0,
        context_length=8192,
        enabled=True,
        priority=10,
    ))


def _build_registry() -> ModelRegistry:
    """构建并填充模型注册中心。"""
    reg = ModelRegistry()
    _register_llm_models(reg)
    _register_image_models(reg)
    _register_voice_models(reg)
    _register_music_models(reg)
    _register_video_models(reg)
    _register_embedding_models(reg)
    logger.info("Model Registry 初始化完成: %d 个模型", len(reg.list_all()))
    for m in reg.list_all():
        logger.info("  %s: %s/%s (%s) q=%s s=%s c=%s",
                     m.model_id, m.provider, m.model_name, m.model_type,
                     m.quality_score, m.speed_score, m.cost_score)
    return reg


registry = _build_registry()
