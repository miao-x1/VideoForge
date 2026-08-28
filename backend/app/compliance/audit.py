"""合规审计日志:每次审核落盘,支持未来追溯。

复用项目现有文件存储体系(storage_dir),不引入数据库。
写两份:
1. state.compliance_audit 列表(进任务状态,前端可读)
2. storage/audit/compliance_audit.jsonl(append-only,长期追溯)
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from ..core.config import settings, storage_dir
from ..core.logging import logger
from .models import AuditEntry, ComplianceResult


class ComplianceAuditLogger:
    def __init__(self) -> None:
        self.enabled: bool = getattr(settings, "compliance_audit_enabled", True)

    def _audit_path(self) -> Path:
        d = storage_dir("audit")
        return d / "compliance_audit.jsonl"

    def log(
        self,
        *,
        content_id: str,
        result: ComplianceResult,
        request_id: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            request_id=request_id or uuid.uuid4().hex,
            content_id=content_id,
            timestamp=time.time(),
            agent_version=result.agent_version,
            rules_version=result.rules_version,
            model_name=result.model_name,
            status=result.status,
            risk_level=result.risk_level,
            violations=len(result.violations),
            warnings=len(result.warnings),
            revision_count=result.revision_count,
            human_review_required=result.human_review_required,
            review_reason=result.review_reason,
        )
        if self.enabled:
            try:
                line = entry.model_dump_json() + "\n"
                with self._audit_path().open("a", encoding="utf-8") as f:
                    f.write(line)
            except Exception as e:
                logger.warning("审计日志写入失败: %s", e)
        return entry

    def history(self, content_id: str | None = None) -> list[Dict[str, Any]]:
        """读取审计历史(可选按 content_id 过滤)。"""
        p = self._audit_path()
        if not p.exists():
            return []
        out: list[Dict[str, Any]] = []
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if content_id and rec.get("content_id") != content_id:
                continue
            out.append(rec)
        return out
