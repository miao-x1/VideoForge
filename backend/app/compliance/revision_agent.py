"""ScriptRevisionAgent:依据合规报告自动修订脚本。

约束:
1. 只修改存在风险的部分
2. 尽量保留原始主题、叙事结构和风格
3. 不允许为规避审核而改变原始主题
4. 输出完整 VideoScript JSON,供 Compliance Agent 再次审核
"""
from __future__ import annotations

from typing import Any, Dict

from ..core.logging import logger
from ..providers.llm.base import LLMProvider
from ..schemas.script import VideoScript
from .models import ComplianceResult

AGENT_VERSION = "1.0"


class ScriptRevisionAgent:
    name = "script_revision"

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def revise(self, script: VideoScript, result: ComplianceResult) -> VideoScript:
        context: Dict[str, Any] = {
            "original_script": script.model_dump(),
            "violations": [v.model_dump() for v in result.violations],
            "warnings": [w.model_dump() for w in result.warnings],
            "revision_suggestions": result.revision_suggestions,
            "matched_rules": result.matched_rules,
            "risk_level": result.risk_level,
        }
        try:
            data = await self.llm.generate(task="script_revision", context=context)
            revised = VideoScript(**data)
            logger.info("脚本修订完成: title=%s -> %s", script.title, revised.title)
            return revised
        except Exception as e:
            logger.warning("脚本修订失败,保留原脚本: %s: %s", type(e).__name__, e)
            # 修订失败不阻断修订循环(由 Orchestrator 控制重试上限),返回原脚本
            return script
