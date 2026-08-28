"""Compliance Agent 抽象基类。

设计为可扩展:当前只实现 TextComplianceAgent,
未来可新增 ImageComplianceAgent / VideoComplianceAgent,
最终形成 Text -> Image -> Video -> Final 的多模态合规链。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ComplianceResult


class BaseComplianceAgent(ABC):
    """所有合规 Agent 的统一接口。

    子类只需实现 check(content),返回结构化 ComplianceResult。
    不允许返回自然语言字符串。
    """
    name: str = "base"
    modality: str = "text"  # text / image / video

    @abstractmethod
    async def check(self, content: Any) -> ComplianceResult:
        """对内容做合规检查,返回结构化结果。"""
        raise NotImplementedError
