"""Model Router 包:需求分析 → 评分 → 模型选择。

阶段级模型路由支持:LLM/Image/Voice/Video/Embedding 各阶段独立选模型。
"""
from .model_router import ModelRouter, RoutingDecision, model_router, STAGE_MODEL_TYPES
from .model_registry import ModelEntry, ModelRegistry, registry
from .requirement_analyzer import RequirementAnalyzer, RequirementProfile
from .model_scorer import ModelScorer, ModelScore
from . import scoring_rules

__all__ = [
    "ModelRouter",
    "RoutingDecision",
    "model_router",
    "STAGE_MODEL_TYPES",
    "ModelEntry",
    "ModelRegistry",
    "registry",
    "RequirementAnalyzer",
    "RequirementProfile",
    "ModelScorer",
    "ModelScore",
    "scoring_rules",
]
