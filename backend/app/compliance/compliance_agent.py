"""TextComplianceAgent:规则检查 + LLM 语义判断两层结合。

规则检查:RuleEngine 做正则快速筛查(仅辅助,不阻断)
LLM 语义判断:复用现有 LLMProvider(qwen-plus),按 COMPLIANCE_CHECK_PROMPT 输出结构化 JSON

失败保护:LLM 调用异常或 JSON 解析失败时,返回 status=review + human_review_required=True,
绝不默认 pass(审核失败 ≠ 自动通过)。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ..core.logging import logger
from ..providers.llm.base import LLMProvider
from ..schemas.script import VideoScript
from .base import BaseComplianceAgent
from .models import ComplianceResult, ComplianceWarning, Violation
from .rule_engine import RuleEngine

AGENT_VERSION = "1.0"


class TextComplianceAgent(BaseComplianceAgent):
    name = "text_compliance"
    modality = "text"

    def __init__(self, llm: LLMProvider, rule_engine: RuleEngine | None = None) -> None:
        self.llm = llm
        self.rule_engine = rule_engine or RuleEngine()

    def _assemble_text(self, script: VideoScript, topic: str) -> str:
        """把脚本文本拼成待审字符串(标题/hook/各场 visual/dialogue/voiceover/ending)。"""
        parts: List[str] = [f"标题: {script.title}", f"主题: {topic}"]
        if script.hook:
            parts.append(f"Hook: {script.hook}")
        for sc in script.scenes:
            parts.append(f"场景{sc.scene_id}[{sc.location}]:")
            if sc.visual:
                parts.append(f"  画面: {sc.visual}")
            if sc.dialogue:
                parts.append(f"  对白: {sc.dialogue}")
            if sc.voiceover:
                parts.append(f"  旁白: {sc.voiceover}")
        if script.ending:
            parts.append(f"结尾: {script.ending}")
        return "\n".join(parts)

    async def check(self, content: Any) -> ComplianceResult:  # type: ignore[override]
        """content 为 dict: {script, topic, metadata?}。"""
        script: VideoScript = content["script"]
        topic: str = content.get("topic", "")
        metadata: Dict[str, Any] = content.get("metadata") or {}

        text = self._assemble_text(script, topic)
        rule_hits = self.rule_engine.match(text)
        rules_for_llm = self.rule_engine.rules_for_llm()

        context = {
            "topic": topic,
            "metadata": metadata,
            "rules": rules_for_llm,
            "rule_hits": rule_hits,  # 确定性规则命中(辅助参考)
            "content": text,
        }

        try:
            data = await self.llm.generate(task="compliance_check", context=context)
            result = self._coerce_result(data, rule_hits)
        except Exception as e:
            # 失败保护:不自动放行,标记人工审核
            logger.warning("Compliance LLM 调用失败,降级为 review+人工审核: %s: %s", type(e).__name__, e)
            result = ComplianceResult(
                status="review",
                risk_level="medium",
                overall_score=0,
                explanation=f"合规预审执行失败,需人工复核: {type(e).__name__}: {e}",
                human_review_required=True,
                review_reason="compliance_check_failed",
                matched_rules=[h["rule_id"] for h in rule_hits],
            )

        result.agent_version = AGENT_VERSION
        result.rules_version = self.rule_engine.version
        result.model_name = getattr(self.llm, "model", "mock")
        return result

    def _coerce_result(self, data: Dict[str, Any], rule_hits: List[Dict[str, Any]]) -> ComplianceResult:
        """把 LLM 返回规整为 ComplianceResult,并合并规则命中。"""
        # 确保关键字段存在
        data.setdefault("status", "review")
        data.setdefault("risk_level", "medium")
        data.setdefault("overall_score", 50)
        data.setdefault("violations", [])
        data.setdefault("warnings", [])
        data.setdefault("matched_rules", [])
        data.setdefault("revision_suggestions", [])

        # 风险等级 -> status 一致性兜底
        risk = data.get("risk_level", "medium")
        if data.get("status") == "pass" and risk == "high":
            data["status"] = "reject"
        if data.get("status") == "pass" and risk == "medium":
            data["status"] = "review"

        # high 风险不应 pass
        if risk == "high" and data["status"] != "reject":
            data["status"] = "reject"

        try:
            result = ComplianceResult(**data)
        except Exception as e:
            # JSON schema 异常:不自动放行
            logger.warning("Compliance JSON 解析异常,降级为 review: %s", e)
            return ComplianceResult(
                status="review",
                risk_level="medium",
                overall_score=0,
                explanation=f"合规预审返回格式异常,需人工复核: {e}",
                human_review_required=True,
                review_reason="compliance_json_invalid",
                matched_rules=[h["rule_id"] for h in rule_hits],
            )

        # 合并确定性规则命中(避免 LLM 漏掉明确模式)
        existing = set(result.matched_rules)
        for h in rule_hits:
            if h["rule_id"] not in existing:
                result.matched_rules.append(h["rule_id"])
                # 高 severity reject 规则命中应进 violations
                if h.get("action") == "reject" and h.get("severity") == "high":
                    result.violations.append(Violation(
                        rule_id=h["rule_id"], category=h["category"],
                        severity="high", evidence=h.get("matched_text", ""),
                        explanation=h.get("description", ""),
                    ))
                    # 命中明确 reject 规则,强制 reject
                    result.status = "reject"
                    result.risk_level = "high"

        # reject 必须人工(修订前)
        if result.status == "reject":
            result.human_review_required = True
            if not result.review_reason:
                result.review_reason = "rejected_by_compliance"
        return result
