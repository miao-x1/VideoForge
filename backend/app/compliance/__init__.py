"""内容合规预审模块。

在 Script 生成后、Storyboard 之前对脚本做合规检查:
  规则检查(确定性正则,辅助) + LLM 语义判断(主) -> 结构化 ComplianceResult
  reject -> ScriptRevisionAgent 自动修订 -> 复检(最多 N 次)
  耗尽仍不通过 -> HUMAN_REVIEW(人工审核兜底)

设计原则:
- 复用现有 LLMProvider,不引入新 LLM 服务
- 规则独立配置(rules_data.py),新增规则无需改 Agent 代码
- 多模态可扩展:BaseComplianceAgent 抽象,未来可加 Image/Video Compliance Agent
- 失败保护:审核异常不自动放行,标记 human_review_required
- 不声明"AI 100% 合规",定位为 自动预审+风险识别+自动修订+人工兜底
"""
from __future__ import annotations

from .audit import ComplianceAuditLogger
from .base import BaseComplianceAgent
from .compliance_agent import TextComplianceAgent
from .models import AuditEntry, ComplianceResult, ComplianceWarning, Violation
from .revision_agent import ScriptRevisionAgent
from .rule_engine import RuleEngine

__all__ = [
    "BaseComplianceAgent",
    "TextComplianceAgent",
    "ScriptRevisionAgent",
    "ComplianceAuditLogger",
    "RuleEngine",
    "ComplianceResult",
    "Violation",
    "ComplianceWarning",
    "AuditEntry",
]
