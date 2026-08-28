"""合规预审结构化输出模型。

所有 Compliance Agent 必须返回 ComplianceResult,不允许只返回自然语言。
status 三态:
  pass   - 无明显风险,可继续 Pipeline
  review - 存在边界问题,需人工审核(默认打标继续,可配置阻断)
  reject - 存在明确高风险内容,不允许直接进入后续生成(触发修订或人工)
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high"]
ComplianceStatus = Literal["pass", "review", "reject"]

# 关闭 pydantic 对 model_ 前缀的保护(model_name 是审计字段,非 Pydantic 内部方法)
_NO_PROTECT = ConfigDict(protected_namespaces=())


class Violation(BaseModel):
    """明确命中的违规问题。"""
    rule_id: str = Field("", description="命中的规则 ID,如 COM-001")
    category: str = Field("", description="规则类别")
    severity: RiskLevel = Field("medium", description="严重程度")
    evidence: str = Field("", description="具体证据片段(原文摘录)")
    explanation: str = Field("", description="为何违规的说明")


class ComplianceWarning(BaseModel):
    """不确定但值得注意的边界问题。"""
    rule_id: str = Field("", description="相关规则 ID(可空)")
    category: str = Field("", description="类别")
    severity: RiskLevel = Field("low", description="严重程度")
    evidence: str = Field("", description="证据片段")
    explanation: str = Field("", description="说明")


class ComplianceResult(BaseModel):
    """合规预审最终结构化结果,可被后续 Pipeline 消费。"""
    model_config = _NO_PROTECT
    status: ComplianceStatus = Field("review", description="pass/review/reject")
    risk_level: RiskLevel = Field("low", description="整体风险等级")
    overall_score: int = Field(100, description="内容安全程度 0-100,非平台通过率")
    violations: List[Violation] = Field(default_factory=list)
    warnings: List[ComplianceWarning] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list, description="命中的规则 ID 列表")
    explanation: str = Field("", description="整体判断说明")
    revision_suggestions: List[str] = Field(default_factory=list, description="具体修改建议")
    human_review_required: bool = Field(False, description="是否需要人工审核")
    review_reason: str = Field("", description="人工审核原因")

    # 审计元数据(由 Agent / Orchestrator 回填)
    agent_version: str = "1.0"
    rules_version: str = "1.0"
    model_name: str = ""
    revision_count: int = 0


class AuditEntry(BaseModel):
    """单次合规审核的审计记录,用于追溯。"""
    model_config = _NO_PROTECT
    request_id: str = ""
    content_id: str = ""
    timestamp: float = 0.0
    agent_version: str = "1.0"
    rules_version: str = "1.0"
    model_name: str = ""
    status: ComplianceStatus = "review"
    risk_level: RiskLevel = "low"
    violations: int = 0
    warnings: int = 0
    revision_count: int = 0
    human_review_required: bool = False
    review_reason: str = ""
