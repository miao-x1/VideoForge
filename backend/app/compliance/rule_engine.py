"""确定性规则引擎(辅助层)。

仅做基于正则的快速筛查,作为 LLM 语义判断的辅助:
- 能自动命中的明确模式(如医疗绝对化、金融收益保证)直接标记
- 上下文/语义/边界判断全部交给 LLM,不在此处阻断

绝不设计成纯关键词黑名单:命中只产生 matched_rules,最终 status 由 LLM 综合判断。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .rules_data import RULES_VERSION, get_enabled_rules


class RuleEngine:
    """加载规则并对文本做正则筛查。"""

    def __init__(self) -> None:
        self.rules: List[Dict[str, Any]] = get_enabled_rules()
        self.version = RULES_VERSION

    def match(self, text: str) -> List[Dict[str, Any]]:
        """对文本做正则匹配,返回命中的规则条目(含 matched_text 证据)。"""
        if not text:
            return []
        hits: List[Dict[str, Any]] = []
        for rule in self.rules:
            patterns: List[str] = rule.get("patterns") or []
            for pat in patterns:
                try:
                    m = re.search(pat, text)
                except re.error:
                    continue
                if m:
                    hits.append({
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "severity": rule.get("severity", "medium"),
                        "action": rule.get("action", "review"),
                        "matched_text": m.group(0),
                        "description": rule.get("description", ""),
                    })
                    break  # 同一规则命中一次即可
        return hits

    def rules_for_llm(self) -> List[Dict[str, str]]:
        """供 LLM 参考的规则摘要(不含 patterns,避免 LLM 退化成关键词匹配)。"""
        return [
            {
                "rule_id": r["rule_id"],
                "category": r["category"],
                "description": r["description"],
                "severity": r.get("severity", "medium"),
                "action": r.get("action", "review"),
            }
            for r in self.rules
        ]
