"""Agent 结构化错误。禁止把未分类 Exception 直接展示给用户。"""
from __future__ import annotations

from typing import Any


USER_ERROR = "USER_ERROR"
AUTH_ERROR = "AUTH_ERROR"
OWNERSHIP_ERROR = "OWNERSHIP_ERROR"
PLAN_ERROR = "PLAN_ERROR"
TOOL_ERROR = "TOOL_ERROR"
GENERATION_ERROR = "GENERATION_ERROR"
ASSET_ERROR = "ASSET_ERROR"
SYSTEM_ERROR = "SYSTEM_ERROR"

PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
INVALID_PLAN = "INVALID_PLAN"
INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
UNKNOWN_TOOL = "UNKNOWN_TOOL"
FORBIDDEN_TOOLS = "FORBIDDEN_TOOLS"
GENERATION_FAILED = "GENERATION_FAILED"
WALLET_INSUFFICIENT = "WALLET_INSUFFICIENT"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"

_HTTP = {
    AUTH_ERROR: 401,
    OWNERSHIP_ERROR: 404,
    PROJECT_NOT_FOUND: 404,
    RESOURCE_NOT_FOUND: 404,
    PLAN_ERROR: 400,
    INVALID_PLAN: 400,
    INVALID_ARGUMENTS: 400,
    UNKNOWN_TOOL: 400,
    FORBIDDEN_TOOLS: 400,
    TOOL_ERROR: 400,
    GENERATION_ERROR: 502,
    GENERATION_FAILED: 502,
    WALLET_INSUFFICIENT: 402,
    ASSET_ERROR: 400,
    USER_ERROR: 400,
    CONFIRMATION_REQUIRED: 200,
    SYSTEM_ERROR: 500,
}


class AgentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status if http_status is not None else _HTTP.get(code, 400)
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "plan": None,
            "actions": [],
            "tool_results": [],
            "generation_id": None,
            "message": self.message,
            "requires_confirmation": self.code == CONFIRMATION_REQUIRED,
            "thinking": [],
            "error_code": self.code,
            "details": self.details,
        }
