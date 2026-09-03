"""模型能力描述:供 ModelRouter 评分和 UI 动态控制用。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelCapabilities:
    """视频模型的各项能力指标。

    前端根据本结构动态控制 UI 选项（如 max_duration 限制时长选择）。
    """

    # 基础
    max_duration: int = 15
    supported_ratios: list[str] = field(default_factory=lambda: ["9:16", "16:9", "1:1"])
    max_resolution: str = "720P"

    # 评分
    quality_score: int = 8
    speed_score: int = 7
    cost_per_sec: float = 0.0

    # 能力
    supports_image_input: bool = True
    supports_video_input: bool = False
    supports_audio_output: bool = False
    supports_text_to_video: bool = False
    supports_first_frame: bool = True
    supports_last_frame: bool = False
    supports_motion_control: bool = False
    supports_negative_prompt: bool = False

    def to_dict(self) -> dict:
        return {
            "max_duration": self.max_duration,
            "supported_ratios": self.supported_ratios,
            "max_resolution": self.max_resolution,
            "quality_score": self.quality_score,
            "speed_score": self.speed_score,
            "cost_per_sec": self.cost_per_sec,
            "supports_image_input": self.supports_image_input,
            "supports_video_input": self.supports_video_input,
            "supports_audio_output": self.supports_audio_output,
            "supports_text_to_video": self.supports_text_to_video,
            "supports_first_frame": self.supports_first_frame,
            "supports_last_frame": self.supports_last_frame,
            "supports_motion_control": self.supports_motion_control,
            "supports_negative_prompt": self.supports_negative_prompt,
        }
