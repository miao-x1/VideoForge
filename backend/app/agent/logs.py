"""写入 DirectorAgentLog。敏感字段按 Wave 0 规则脱敏。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DirectorAgentLog

_SENSITIVE_KEYS = frozenset({
    "authorization",
        "api_key",
        "apikey",
        "encrypted_key",
    "jwt",
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "bearer",
})


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_payload(item)
        return out
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "[REDACTED]"
    return value


async def write_log(
    db: AsyncSession,
    *,
    conversation_id: str,
    message_id: str,
    agent_run_id: str,
    user_input: str,
    context: dict | None,
    user_id: str,
    project_id: str,
    tool_name: str = "",
    tool_arguments: dict | None = None,
    tool_result: dict | None = None,
    execution_status: str = "planned",
    error: str | None = None,
) -> None:
    row = DirectorAgentLog(
        user_id=user_id,
        project_id=project_id,
        conversation_id=conversation_id[:32],
        message_id=message_id[:32],
        agent_run_id=agent_run_id[:32],
        user_input=user_input,
        context_json=redact_payload(context),
        tool_name=tool_name,
        tool_arguments=redact_payload(tool_arguments),
        tool_result=redact_payload(tool_result),
        execution_status=execution_status,
        error=error,
    )
    db.add(row)
    await db.commit()


def slim_context(
    context: dict[str, Any] | None,
    *,
    user_id: str,
    project_id: str,
) -> dict | None:
    if not context:
        return {"user_id": user_id, "project_id": project_id}
    return redact_payload({
        "user_id": user_id,
        "project_id": project_id,
        "scene_id": context.get("scene_id"),
        "scene_name": context.get("scene_name"),
        "selected_id": context.get("selected_id"),
        "focus": context.get("focus"),
        "objects": [
            {
                "id": o.get("id"),
                "name": o.get("name"),
                "characterId": o.get("characterId"),
                "position": o.get("position"),
                "catalogId": o.get("catalogId"),
            }
            for o in (context.get("objects") or [])
            if isinstance(o, dict)
        ],
        "cameras": context.get("cameras"),
        "shot_duration": context.get("shot_duration"),
        "current_generation": context.get("current_generation"),
    })
