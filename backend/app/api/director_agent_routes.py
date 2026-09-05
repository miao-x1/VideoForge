"""导演台 Agent API。JWT → DirectorContext → Planner → Plan → Validator → Executor。"""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.context import build_director_context
from ..agent.errors import AgentError, FORBIDDEN_TOOLS
from ..agent.executor import execute_plan
from ..agent.logs import slim_context, write_log
from ..agent.plan_model import to_director_plan
from ..agent.planner import plan, try_llm_async
from ..agent.prompt_gen import generate_prompt
from ..agent.registry import ALLOWED, TOOLS, is_allowed, needs_confirm
from ..agent.validator import FORBIDDEN_TOOL_NAMES
from ..auth.dependencies import get_current_user
from ..db.database import get_db
from ..db.models import User
from ..db.ownership import resolve_director_scope

router = APIRouter(prefix="/api/agent", tags=["director-agent"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    project_id: str = ""
    conversation_id: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False
    stream: bool = False


class LogRequest(BaseModel):
    conversation_id: str
    message_id: str
    agent_run_id: str
    user_input: str = ""
    context: dict[str, Any] | None = None
    tool_name: str = ""
    tool_arguments: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    execution_status: str = "ok"
    error: str | None = None


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def _human_message(plan_doc: dict, execution: dict) -> str:
    if execution.get("requires_confirmation"):
        return str(execution.get("message") or "该操作需要确认后才能执行。")
    if execution.get("error_code"):
        return str(execution.get("message") or "执行失败")
    names = [str(c.get("name") or "") for c in plan_doc.get("tool_calls") or []]
    if "move_character" in names and "set_character_action" in names:
        return "已将角色移动到目标位置，并设置动作。"
    if "move_character" in names:
        return "已将角色移动到目标位置。"
    if "generate_video" in names:
        return "已按导演方案调用视频生成。"
    if "generate_image" in names:
        return "已按导演方案调用图片生成。"
    return str(execution.get("message") or plan_doc.get("summary") or "已完成导演指令。")


@router.get("/tools")
async def list_tools(_user: User = Depends(get_current_user)) -> dict:
    return {
        "tools": [
            {
                "name": t.name,
                "group": t.group,
                "description": t.description,
                "confirm": t.confirm,
                "permission": t.permission,
                "side_effect": t.side_effect,
            }
            for t in TOOLS
        ]
    }


@router.post("/log")
async def post_log(
    body: LogRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: str | None = Query(None),
) -> dict:
    scope = await resolve_director_scope(db, user, project_id)
    if body.tool_name and not is_allowed(body.tool_name) and body.tool_name not in {"", "plan"}:
        return {"ok": False, "error": "未注册 Tool，拒绝写入"}
    await write_log(
        db,
        conversation_id=body.conversation_id,
        message_id=body.message_id,
        agent_run_id=body.agent_run_id,
        user_input=body.user_input,
        user_id=scope.user_id,
        project_id=scope.project_id,
        context=slim_context(body.context, user_id=scope.user_id, project_id=scope.project_id),
        tool_name=body.tool_name,
        tool_arguments=body.tool_arguments,
        tool_result=body.tool_result,
        execution_status=body.execution_status,
        error=body.error,
    )
    return {"ok": True}


@router.post("/chat")
async def agent_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: str | None = Query(None),
):
    try:
        scope = await resolve_director_scope(db, user, body.project_id or project_id or "")
    except Exception as exc:
        if hasattr(exc, "status_code"):
            return JSONResponse({"success": False, "error_code": "PROJECT_NOT_FOUND", "message": "项目不存在", "plan": None, "actions": [], "tool_results": [], "generation_id": None}, status_code=exc.status_code)
        raise

    if any(token in body.message.lower() for token in ("execute_sql", "execute_python", "execute_shell", "os.system", "subprocess.")):
        return JSONResponse(
            {"success": False, "error_code": FORBIDDEN_TOOLS, "message": "禁止执行 SQL / Python / Shell", "plan": None, "actions": [], "tool_results": [], "generation_id": None},
            status_code=400,
        )

    conversation_id = (body.conversation_id or uuid.uuid4().hex)[:32]
    message_id = uuid.uuid4().hex[:32]
    agent_run_id = uuid.uuid4().hex[:32]
    client = dict(body.context or {})
    client.pop("user_id", None)
    client.pop("project_id", None)
    client["user_message"] = body.message
    context = await build_director_context(db, scope, client)

    result = plan(body.message, context)
    if result.get("error") and not result.get("calls"):
        llm = await try_llm_async(body.message, context)
        if llm:
            result = llm

    raw_calls = []
    for raw in result.get("calls") or []:
        name = str(raw.get("name") or "")
        if name in FORBIDDEN_TOOL_NAMES:
            return JSONResponse(
                {"success": False, "error_code": FORBIDDEN_TOOLS, "message": "禁止执行 SQL / Python / Shell", "plan": None, "actions": [], "tool_results": [], "generation_id": None},
                status_code=400,
            )
        if not is_allowed(name):
            continue
        raw_calls.append({
            "name": name,
            "arguments": raw.get("arguments") or {},
            "note": raw.get("note") or ALLOWED[name].description,
        })
    result = {**result, "calls": raw_calls}
    plan_doc = to_director_plan(result, project_id=scope.project_id, scene_id=str(context.get("scene_id") or ""), message=body.message)

    execution: dict[str, Any] = {
        "executed": False,
        "requires_confirmation": False,
        "tool_results": [],
        "generation_id": None,
        "message": result.get("error") or "未能形成可执行方案",
    }
    error_code = None
    try:
        if raw_calls:
            execution = await execute_plan(db, scope, plan_doc, context, confirm=body.confirm)
            error_code = execution.get("error_code")
        elif result.get("error"):
            error_code = "PLAN_ERROR"
    except AgentError as exc:
        execution = {"executed": False, "requires_confirmation": False, "tool_results": [], "generation_id": None, "message": exc.message, "error_code": exc.code}
        error_code = exc.code
        payload = {
            "success": False,
            "plan": plan_doc,
            "actions": plan_doc.get("actions") or [],
            "tool_results": [],
            "generation_id": None,
            "message": exc.message,
            "requires_confirmation": False,
            "thinking": plan_doc.get("thinking") or [],
            "error_code": exc.code,
        }
        await write_log(
            db,
            conversation_id=conversation_id,
            message_id=message_id,
            agent_run_id=agent_run_id,
            user_input=body.message,
            user_id=scope.user_id,
            project_id=scope.project_id,
            context=slim_context(context, user_id=scope.user_id, project_id=scope.project_id),
            tool_name="plan",
            tool_arguments={"message": body.message},
            tool_result={"plan_json": plan_doc, "error_code": exc.code},
            execution_status="error",
            error=exc.message,
        )
        if body.stream:
            return StreamingResponse(_error_events(conversation_id, message_id, agent_run_id, payload), media_type="text/event-stream")
        return JSONResponse(payload, status_code=exc.http_status if exc.http_status != 200 else 400)

    status = "ok" if execution.get("executed") else ("confirm" if execution.get("requires_confirmation") else ("error" if error_code else "planned"))
    await write_log(
        db,
        conversation_id=conversation_id,
        message_id=message_id,
        agent_run_id=agent_run_id,
        user_input=body.message,
        user_id=scope.user_id,
        project_id=scope.project_id,
        context=slim_context(context, user_id=scope.user_id, project_id=scope.project_id),
        tool_name="plan",
        tool_arguments={"message": body.message},
        tool_result={
            "plan_json": plan_doc,
            "tool_calls": [c["name"] for c in raw_calls],
            "tool_results": execution.get("tool_results") or [],
            "thinking": plan_doc.get("thinking"),
        },
        execution_status=status,
        error=None if status in {"ok", "confirm", "planned"} else execution.get("message"),
    )

    payload = {
        "success": bool(execution.get("executed")) or bool(execution.get("requires_confirmation")),
        "plan": plan_doc,
        "actions": plan_doc.get("actions") or [],
        "tool_results": execution.get("tool_results") or [],
        "generation_id": execution.get("generation_id"),
        "message": _human_message(plan_doc, execution) if raw_calls else (result.get("error") or "无法理解这条指令。"),
        "requires_confirmation": bool(execution.get("requires_confirmation")),
        "thinking": plan_doc.get("thinking") or [],
        "error_code": error_code,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "agent_run_id": agent_run_id,
    }

    if body.stream:
        return StreamingResponse(
            _stream_events(payload, raw_calls, body.confirm),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
    return payload


async def _error_events(conversation_id: str, message_id: str, agent_run_id: str, payload: dict):
    yield _sse("run", {"conversation_id": conversation_id, "message_id": message_id, "agent_run_id": agent_run_id})
    yield _sse("error", {"message": payload.get("message"), "code": payload.get("error_code")})
    yield _sse("complete", {"ok": False})


async def _stream_events(payload: dict, calls: list[dict], confirm: bool):
    yield _sse("run", {
        "conversation_id": payload["conversation_id"],
        "message_id": payload["message_id"],
        "agent_run_id": payload["agent_run_id"],
    })
    for line in payload.get("thinking") or []:
        yield _sse("thinking", {"text": str(line)})
    if payload.get("error_code") and not calls:
        yield _sse("error", {"message": payload.get("message")})
        yield _sse("complete", {"ok": False})
        return
    for call in calls:
        yield _sse("tool_call", {
            **call,
            "confirm": needs_confirm(call["name"]) and not confirm,
        })
    yield _sse("complete", {
        "ok": bool(payload.get("success")),
        "planned": len(calls),
        "generation_id": payload.get("generation_id"),
        "requires_confirmation": payload.get("requires_confirmation"),
    })


@router.post("/prompt")
async def agent_prompt(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: str | None = Query(None),
) -> dict:
    scope = await resolve_director_scope(db, user, body.get("project_id") or project_id or "")
    kind = str(body.get("kind") or "video")
    client = dict(body.get("context") or {})
    client.pop("user_id", None)
    client.pop("project_id", None)
    context = await build_director_context(db, scope, client)
    return generate_prompt(kind, context)
