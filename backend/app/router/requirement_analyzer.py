"""需求分析器:从用户输入和参数提取需求维度。

轻量纯规则实现,不依赖 LLM。可后续升级为 LLM 语义分析。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import scoring_rules


@dataclass
class RequirementProfile:
    """用户需求的维度画像。"""

    duration: int = 30
    aspect_ratio: str = "9:16"
    quality_priority: float = 0.5
    speed_priority: float = 0.5
    cost_sensitivity: float = 0.5
    matched_keywords: list[str] = field(default_factory=list)
    style: str = ""
    detected_styles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "quality_priority": self.quality_priority,
            "speed_priority": self.speed_priority,
            "cost_sensitivity": self.cost_sensitivity,
            "matched_keywords": self.matched_keywords,
            "style": self.style,
            "detected_styles": self.detected_styles,
        }


class RequirementAnalyzer:
    """从 user_input + 参数提取需求维度。"""

    def analyze(
        self,
        user_input: str,
        duration: int = 30,
        style: str = "",
        aspect_ratio: str = "9:16",
    ) -> RequirementProfile:
        text = (user_input or "").lower()
        matched: list[str] = []

        quality = 0.5
        speed = 0.5
        cost = 0.5

        for kw in scoring_rules.QUALITY_KEYWORDS:
            if kw in text:
                quality = min(1.0, quality + 0.3)
                matched.append(kw)
        for kw in scoring_rules.SPEED_KEYWORDS:
            if kw in text:
                speed = min(1.0, speed + 0.3)
                matched.append(kw)
        for kw in scoring_rules.COST_KEYWORDS:
            if kw in text:
                cost = min(1.0, cost + 0.3)
                matched.append(kw)

        # 时长推断:短视频速度优先,长视频质量优先
        if duration <= scoring_rules.SHORT_VIDEO_THRESHOLD:
            speed = min(1.0, speed + 0.2)
        elif duration >= scoring_rules.LONG_VIDEO_THRESHOLD:
            quality = min(1.0, quality + 0.2)

        # 风格检测
        detected_styles = self._detect_styles(text, style)

        return RequirementProfile(
            duration=duration,
            aspect_ratio=aspect_ratio,
            quality_priority=quality,
            speed_priority=speed,
            cost_sensitivity=cost,
            matched_keywords=matched,
            style=style,
            detected_styles=detected_styles,
        )

    @staticmethod
    def _detect_styles(text: str, explicit_style: str) -> list[str]:
        """从文本和显式风格字段检测视觉风格。"""
        detected: list[str] = []
        combined = f"{text} {explicit_style}".lower()
        for style_key, keywords in scoring_rules.STYLE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                detected.append(style_key)
        return detected
