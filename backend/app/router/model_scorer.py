"""模型评分器:基于需求画像和模型能力计算综合评分。

支持所有模型类型 (LLM/Image/Voice/Video/Embedding) 和多种路由策略。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model_registry import ModelEntry, registry
from .requirement_analyzer import RequirementProfile
from . import scoring_rules


@dataclass
class ModelScore:
    """单个模型的评分结果。"""

    model_id: str
    provider: str
    model: str
    model_type: str
    total_score: float
    quality_score: float
    speed_score: float
    cost_score: float
    fit_score: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "model": self.model,
            "model_type": self.model_type,
            "total_score": round(self.total_score, 3),
            "quality_score": round(self.quality_score, 3),
            "speed_score": round(self.speed_score, 3),
            "cost_score": round(self.cost_score, 3),
            "fit_score": round(self.fit_score, 3),
            "reason": self.reason,
        }


class ModelScorer:
    """根据需求画像和模型能力计算评分。"""

    def score_all(
        self,
        profile: RequirementProfile,
        model_type: str = "image_to_video",
        strategy: str = "auto",
    ) -> list[ModelScore]:
        """对指定类型的所有可用模型评分并排序。"""
        candidates = registry.list_by_type(model_type)
        scores = []
        for entry in candidates:
            score = self._score_one(entry, profile, strategy)
            scores.append(score)
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def score_all_by_types(
        self,
        profile: RequirementProfile,
        model_types: list[str],
        strategy: str = "auto",
    ) -> list[ModelScore]:
        """对多种类型的所有可用模型评分并排序。"""
        candidates = registry.list_by_types(model_types)
        scores = []
        for entry in candidates:
            score = self._score_one(entry, profile, strategy)
            scores.append(score)
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def _score_one(
        self,
        entry: ModelEntry,
        profile: RequirementProfile,
        strategy: str,
    ) -> ModelScore:
        w = self._get_weights(strategy)

        quality = (entry.quality_score / 10.0) * profile.quality_priority
        speed = (entry.speed_score / 10.0) * profile.speed_priority
        cost = ((10.0 - entry.cost_score) / 10.0) * profile.cost_sensitivity
        fit = self._calc_fit(entry, profile)

        total = (
            w["quality"] * quality
            + w["speed"] * speed
            + w["cost"] * cost
            + w["fit"] * fit
        )

        reasons = []
        if quality > 0.5:
            reasons.append(f"画质匹配度高({quality:.2f})")
        if speed > 0.5:
            reasons.append(f"速度优势明显({speed:.2f})")
        if cost > 0.5:
            reasons.append(f"成本效益好({cost:.2f})")
        if fit < 0.3:
            reasons.append(f"需求匹配度低({fit:.2f})")
        if entry.priority > 0:
            reasons.append(f"优先级={entry.priority}")
        if not reasons:
            reasons.append("综合评分最优")

        return ModelScore(
            model_id=entry.model_id,
            provider=entry.provider,
            model=entry.model_name,
            model_type=entry.model_type,
            total_score=total,
            quality_score=quality,
            speed_score=speed,
            cost_score=cost,
            fit_score=fit,
            reason="; ".join(reasons),
        )

    @staticmethod
    def _get_weights(strategy: str) -> dict[str, float]:
        """根据策略调整评分权重。"""
        if strategy == "best_quality":
            return {"quality": 0.50, "speed": 0.15, "cost": 0.10, "fit": 0.25}
        if strategy == "lowest_cost":
            return {"quality": 0.15, "speed": 0.15, "cost": 0.55, "fit": 0.15}
        if strategy == "fastest":
            return {"quality": 0.15, "speed": 0.55, "cost": 0.15, "fit": 0.15}
        return scoring_rules.WEIGHTS  # auto

    @staticmethod
    def _calc_fit(entry: ModelEntry, profile: RequirementProfile) -> float:
        """需求匹配度:时长支持 + 比例支持 + 风格匹配。"""
        fit = 1.0

        if entry.supported_durations and profile.duration > 0:
            max_dur = max(entry.supported_durations)
            if profile.duration > max_dur:
                fit *= 0.3

        if profile.aspect_ratio and profile.aspect_ratio not in entry.supported_aspect_ratios:
            fit *= 0.5

        if profile.style and entry.supported_styles:
            style_lower = profile.style.lower()
            if not any(s in style_lower or style_lower in s for s in entry.supported_styles):
                fit *= 0.7

        return fit
