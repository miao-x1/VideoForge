"""DirectorPlan 执行前校验。Planner 不写库，Validator 不改意图。"""
from __future__ import annotations

import re
from typing import Any

from .errors import (
    FORBIDDEN_TOOLS,
    INVALID_ARGUMENTS,
    INVALID_PLAN,
    RESOURCE_NOT_FOUND,
    UNKNOWN_TOOL,
    AgentError,
)
from .registry import is_allowed

FORBIDDEN_TOOL_NAMES = frozenset({
    "execute_sql",
    "run_sql",
    "sql",
    "execute_python",
    "run_python",
    "eval",
    "exec",
    "execute_shell",
    "run_shell",
    "bash",
    "sh",
    "system",
    "subprocess",
    "os_system",
})

_CODE_HINT = re.compile(
    r"(?is)\b(select\s+.+\s+from|insert\s+into|update\s+.+\s+set|delete\s+from|"
    r"drop\s+table|import\s+os|subprocess\.|os\.system|__import__|eval\(|exec\()\b"
)


def _scope_ids(scope: Any) -> tuple[str, str]:
    return str(getattr(scope, "user_id", "") or ""), str(getattr(scope, "project_id", "") or "")


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(x) for x in value if x]
    return [str(value)]


def _check_ref(kind: str, value: Any, allowed: set[str]) -> None:
    if value in (None, "", [], {}):
        return
    raw = str(value)
    if raw.startswith("__") and raw.endswith("__"):
        return
    if raw in {"女主角", "男主角", "当前角色"}:
        return
    if raw not in allowed:
        raise AgentError(RESOURCE_NOT_FOUND, f"{kind} 不属于当前项目", details={"kind": kind, "id": raw})


def validate_plan(plan: dict[str, Any], scope: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {}
    user_id, project_id = _scope_ids(scope)
    if not isinstance(plan, dict):
        raise AgentError(INVALID_PLAN, "Plan 必须是对象")
    if not user_id or not project_id:
        raise AgentError(INVALID_PLAN, "缺少 User / Project 作用域")
    if str(plan.get("project_id") or "") != project_id:
        raise AgentError(RESOURCE_NOT_FOUND, "Plan 的 project_id 不属于当前用户")

    owned_scenes = set(_as_list(ctx.get("owned_scene_ids")))
    scene_id = str(plan.get("scene_id") or ctx.get("scene_id") or "")
    if scene_id and owned_scenes and scene_id not in owned_scenes:
        raise AgentError(RESOURCE_NOT_FOUND, "scene_id 不属于当前项目")

    calls = plan.get("tool_calls") or []
    if not isinstance(calls, list):
        raise AgentError(INVALID_PLAN, "tool_calls 必须是数组")

    owned_chars = set(_as_list(ctx.get("owned_character_ids"))) | set(_as_list(ctx.get("owned_object_ids")))
    owned_cams = set(_as_list(ctx.get("owned_camera_ids")))
    owned_gens = set(_as_list(ctx.get("owned_generation_ids")))
    owned_assets = set(_as_list(ctx.get("owned_asset_ids")))
    for obj in ctx.get("objects") or []:
        if isinstance(obj, dict):
            if obj.get("id"):
                owned_chars.add(str(obj["id"]))
            if obj.get("characterId"):
                owned_chars.add(str(obj["characterId"]))
    for cam in ctx.get("cameras") or []:
        if isinstance(cam, dict) and cam.get("id"):
            owned_cams.add(str(cam["id"]))

    for call in calls:
        if not isinstance(call, dict):
            raise AgentError(INVALID_PLAN, "Tool 调用必须是对象")
        name = str(call.get("name") or "").strip()
        if not name:
            raise AgentError(INVALID_PLAN, "Tool 名为空")
        if name in FORBIDDEN_TOOL_NAMES or name.lower() in FORBIDDEN_TOOL_NAMES:
            raise AgentError(FORBIDDEN_TOOLS, "禁止执行 SQL / Python / Shell")
        if not is_allowed(name):
            raise AgentError(UNKNOWN_TOOL, f"未注册 Tool：{name}")
        args = call.get("arguments")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise AgentError(INVALID_ARGUMENTS, f"{name} 参数必须是对象")
        blob = " ".join(str(v) for v in args.values() if isinstance(v, str))
        if _CODE_HINT.search(blob):
            raise AgentError(FORBIDDEN_TOOLS, "禁止把 SQL / Python / Shell 当作 Tool 参数")

        _check_ref("character_id", args.get("character_id") or args.get("character_ref") or args.get("object_ref") or args.get("target_ref"), owned_chars)
        _check_ref("camera_id", args.get("camera_id"), owned_cams)
        _check_ref("generation_id", args.get("generation_id"), owned_gens)
        _check_ref("asset_id", args.get("asset_id") or args.get("reference_asset_id"), owned_assets)
        _check_ref("scene_id", args.get("scene_id"), owned_scenes)

        if name == "move_character":
            pos = args.get("position")
            near = args.get("near")
            if pos is not None and not isinstance(pos, (list, tuple)) and not (isinstance(pos, str) and pos.startswith("__")):
                if not isinstance(pos, dict):
                    raise AgentError(INVALID_ARGUMENTS, "position 必须是坐标数组")
            if pos is None and not near and args.get("character_id") is None and args.get("character_ref") is None:
                raise AgentError(INVALID_ARGUMENTS, "move_character 缺少目标位置")
        if name in {"generate_image", "generate_video"} and args.get("kind") not in (None, "", "image", "video"):
            raise AgentError(INVALID_ARGUMENTS, "generation kind 非法")

    return {"ok": True, "plan_id": plan.get("plan_id"), "tool_count": len(calls)}
