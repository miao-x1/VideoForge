"""模型路由器:分析需求 → 评分 → 选模型。

支持阶段级模型路由:
- LLM 模型路由 (reasoning/general_llm/lightweight_llm)
- Image 模型路由 (text_to_image/image_edit)
- Voice 模型路由 (tts)
- Video 模型路由 (image_to_video/text_to_video)
- Embedding 模型路由 (embedding)

路由策略:
- auto: 综合评分
- best_quality: 质量优先
- lowest_cost: 成本优先
- fastest: 速度优先
- manual: 用户指定

路由决策记录可供审计和调优。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.exceptions import ModelUnavailableError, ProviderNotConfiguredError
from ..core.logging import logger
from .model_registry import ModelEntry, registry
from .model_scorer import ModelScore, ModelScorer
from .requirement_analyzer import RequirementAnalyzer, RequirementProfile


@dataclass
class RoutingDecision:
    """路由决策结果。"""

    selected_provider: str
    selected_model: str
    selected_model_id: str
    model_type: str
    strategy: str
    reason: str
    profile: dict
    scored_models: list[dict]
    quality_stars: int = 0
    speed_stars: int = 0
    cost_stars: int = 0

    def to_dict(self) -> dict:
        return {
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "selected_model_id": self.selected_model_id,
            "model_type": self.model_type,
            "strategy": self.strategy,
            "reason": self.reason,
            "profile": self.profile,
            "scored_models": self.scored_models,
            "quality_stars": self.quality_stars,
            "speed_stars": self.speed_stars,
            "cost_stars": self.cost_stars,
        }


# 阶段到模型类型的映射
STAGE_MODEL_TYPES = {
    "requirement_understanding": ["reasoning", "general_llm"],
    "creative_planning": ["reasoning", "general_llm"],
    "script_generation": ["reasoning", "general_llm"],
    "storyboard_generation": ["reasoning", "general_llm"],
    "prompt_engineering": ["reasoning", "general_llm"],
    "compliance_check": ["general_llm", "lightweight_llm"],
    "content_guard": ["general_llm", "lightweight_llm"],
    "image_generation": ["text_to_image", "image_edit"],
    "voice_generation": ["tts"],
    "music_generation": ["music"],
    "video_generation": ["image_to_video", "text_to_video", "reference_to_video"],
    "embedding": ["embedding"],
}


class ModelRouter:
    """根据用户需求自动选择最优模型,支持阶段级路由。"""

    def __init__(self) -> None:
        self.analyzer = RequirementAnalyzer()
        self.scorer = ModelScorer()

    def select(
        self,
        user_input: str,
        duration: int = 30,
        style: str = "",
        aspect_ratio: str = "9:16",
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """选择最优视频模型,返回路由决策。

        Args:
            preferred_model: 用户指定模型 provider,非空时验证可用性后直接使用
            strategy: 路由策略 (auto/best_quality/lowest_cost/fastest/manual)
        """
        return self.select_for_stage(
            stage="video_generation",
            user_input=user_input,
            duration=duration,
            style=style,
            aspect_ratio=aspect_ratio,
            preferred_model=preferred_model,
            strategy=strategy,
        )

    def select_for_stage(
        self,
        stage: str,
        user_input: str = "",
        duration: int = 30,
        style: str = "",
        aspect_ratio: str = "9:16",
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """为指定阶段选择最优模型。

        Args:
            stage: 阶段名称,见 STAGE_MODEL_TYPES
            preferred_model: 用户指定模型 model_id 或 provider
            strategy: 路由策略
        """
        profile = self.analyzer.analyze(
            user_input=user_input,
            duration=duration,
            style=style,
            aspect_ratio=aspect_ratio,
        )

        model_types = STAGE_MODEL_TYPES.get(stage, ["general_llm"])
        candidates = registry.list_by_types(model_types)

        if not candidates:
            logger.error("阶段 %s 无可用模型 (类型: %s)", stage, model_types)
            raise ModelUnavailableError(
                stage,
                f"阶段 {stage} 无可用真实模型。"
                f"请检查 API Key 配置和账户状态。",
                error_code="NO_MODELS_AVAILABLE",
            )

        # 用户手动指定
        if preferred_model:
            entry = self._find_preferred(candidates, preferred_model)
            if entry:
                logger.info("用户指定模型 %s,阶段=%s", entry.model_id, stage)
                return RoutingDecision(
                    selected_provider=entry.provider,
                    selected_model=entry.model_name,
                    selected_model_id=entry.model_id,
                    model_type=entry.model_type,
                    strategy="manual",
                    reason=f"用户手动指定: {entry.model_id}",
                    profile=profile.to_dict(),
                    scored_models=[],
                    quality_stars=_to_stars(entry.quality_score),
                    speed_stars=_to_stars(entry.speed_score),
                    cost_stars=_to_stars(10 - entry.cost_score),
                )
            # 指定但不可用
            available_ids = [m.model_id for m in candidates]
            logger.warning("用户指定 %s 但不可用,可用: %s", preferred_model, available_ids)
            raise ModelUnavailableError(
                stage,
                f"用户指定的模型 {preferred_model} 不可用。"
                f"当前可用模型: {', '.join(available_ids)}。"
                "请检查 API Key 配置和账户状态。",
                error_code="MODEL_NOT_AVAILABLE",
            )

        # 自动评分选择
        scores = self.scorer.score_all_by_types(profile, model_types, strategy)
        if not scores:
            logger.error("阶段 %s 评分后无可用模型", stage)
            raise ModelUnavailableError(
                stage,
                f"阶段 {stage} 所有模型评分后均不可用。",
                error_code="NO_MODELS_AVAILABLE",
            )

        best = scores[0]
        best_entry = registry.get(best.model_id)
        logger.info(
            "模型路由 [stage=%s strategy=%s]: 选中 %s (%s), 总分=%.3f, 理由: %s",
            stage, strategy, best.model_id, best.model, best.total_score, best.reason,
        )
        return RoutingDecision(
            selected_provider=best.provider,
            selected_model=best.model,
            selected_model_id=best.model_id,
            model_type=best.model_type,
            strategy=strategy,
            reason=best.reason,
            profile=profile.to_dict(),
            scored_models=[s.to_dict() for s in scores],
            quality_stars=_to_stars(best_entry.quality_score) if best_entry else 0,
            speed_stars=_to_stars(best_entry.speed_score) if best_entry else 0,
            cost_stars=_to_stars(10 - best_entry.cost_score) if best_entry else 0,
        )

    def select_llm(
        self,
        user_input: str = "",
        stage: str = "script_generation",
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """快捷方法:选择 LLM 模型。"""
        return self.select_for_stage(
            stage=stage,
            user_input=user_input,
            preferred_model=preferred_model,
            strategy=strategy,
        )

    def select_image(
        self,
        user_input: str = "",
        style: str = "",
        aspect_ratio: str = "9:16",
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """快捷方法:选择图片模型。"""
        return self.select_for_stage(
            stage="image_generation",
            user_input=user_input,
            style=style,
            aspect_ratio=aspect_ratio,
            preferred_model=preferred_model,
            strategy=strategy,
        )

    def select_voice(
        self,
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """快捷方法:选择语音模型。"""
        return self.select_for_stage(
            stage="voice_generation",
            preferred_model=preferred_model,
            strategy=strategy,
        )

    def select_music(
        self,
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """快捷方法:选择音乐模型。"""
        return self.select_for_stage(
            stage="music_generation",
            preferred_model=preferred_model,
            strategy=strategy,
        )

    def select_embedding(
        self,
        preferred_model: Optional[str] = None,
        strategy: str = "auto",
    ) -> RoutingDecision:
        """快捷方法:选择 Embedding 模型。"""
        return self.select_for_stage(
            stage="embedding",
            preferred_model=preferred_model,
            strategy=strategy,
        )

    @staticmethod
    def _find_preferred(candidates: list[ModelEntry], preferred: str) -> Optional[ModelEntry]:
        """在候选模型中查找用户指定的模型。"""
        for entry in candidates:
            if entry.model_id == preferred or entry.provider == preferred:
                return entry
        return None


def _to_stars(score: float) -> int:
    """将 0-10 分映射为 0-5 星。"""
    if score >= 9:
        return 5
    if score >= 7:
        return 4
    if score >= 5:
        return 3
    if score >= 3:
        return 2
    if score >= 1:
        return 1
    return 0


model_router = ModelRouter()
