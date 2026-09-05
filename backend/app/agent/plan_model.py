"""把 Planner 输出收成结构化 DirectorPlan。不执行、不写库。"""
from __future__ import annotations

import uuid
from typing import Any

from .registry import ALLOWED, needs_confirm

_INTENT = {
    "create_scene": "create_scene",
    "rename_scene": "update_scene",
    "delete_scene": "update_scene",
    "create_character": "create_character",
    "add_character_to_scene": "update_character",
    "remove_character_from_scene": "update_character",
    "move_character": "move_character",
    "rotate_character": "update_character",
    "scale_character": "update_character",
    "set_character_pose": "set_character_pose",
    "set_character_action": "set_character_action",
    "set_character_expression": "update_character",
    "set_camera": "set_camera",
    "create_camera": "set_camera",
    "move_camera": "set_camera",
    "rotate_camera": "set_camera",
    "set_camera_fov": "set_camera",
    "set_camera_target": "set_camera",
    "set_camera_motion": "set_camera",
    "select_camera": "set_camera",
    "create_shot": "create_shot",
    "update_shot": "update_shot",
    "delete_shot": "delete_shot",
    "duplicate_shot": "create_shot",
    "set_shot_duration": "update_shot",
    "set_shot_description": "update_shot",
    "set_shot_type": "update_shot",
    "update_storyboard": "update_storyboard",
    "update_timeline": "update_timeline",
    "create_keyframe": "update_timeline",
    "generate_image": "generate_image",
    "generate_video": "generate_video",
    "restore_generation": "restore_generation",
    "generate_prompt": "update_shot",
}


def infer_intent(calls: list[dict[str, Any]]) -> str:
    names = [str(c.get("name") or "") for c in calls]
    if "restore_generation" in names:
        return "restore_generation"
    if "generate_video" in names:
        return "generate_video"
    if "generate_image" in names:
        return "generate_image"
    if "delete_shot" in names or "delete_scene" in names:
        return "delete_shot"
    if "create_shot" in names:
        return "create_shot"
    if "move_character" in names:
        return "move_character"
    if "set_character_action" in names:
        return "set_character_action"
    if "set_character_pose" in names:
        return "set_character_pose"
    if any(n.startswith("set_camera") or n in {"create_camera", "move_camera", "select_camera"} for n in names):
        return "set_camera"
    if names:
        return _INTENT.get(names[0], names[0])
    return "unknown"


def to_director_plan(
    raw: dict[str, Any],
    *,
    project_id: str,
    scene_id: str,
    message: str,
) -> dict[str, Any]:
    calls = [c for c in (raw.get("calls") or []) if isinstance(c, dict)]
    confirm = any(needs_confirm(str(c.get("name") or "")) for c in calls)
    actions = []
    camera: dict[str, Any] = {}
    generation: dict[str, Any] = {}
    required_assets: list[str] = []
    for call in calls:
        name = str(call.get("name") or "")
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        spec = ALLOWED.get(name)
        actions.append({
            "type": _INTENT.get(name, name),
            "tool": name,
            "arguments": args,
            "note": call.get("note") or (spec.description if spec else ""),
            "requires_confirmation": bool(spec and spec.confirm),
        })
        if name in {"set_camera", "move_camera", "set_camera_motion", "set_camera_target", "set_camera_fov"}:
            camera = {**camera, **args, "tool": name}
        if name in {"generate_image", "generate_video", "restore_generation"}:
            generation = {**args, "kind": "video" if name == "generate_video" else args.get("kind") or "image", "tool": name}
        for key in ("asset_id", "character_id", "reference_asset_id"):
            if args.get(key):
                required_assets.append(str(args[key]))
    summary = str(raw.get("summary") or message).strip()[:240]
    if raw.get("director_plan") and isinstance(raw["director_plan"], dict):
        summary = str(raw["director_plan"].get("story") or summary)[:240]
    return {
        "plan_id": uuid.uuid4().hex,
        "project_id": project_id,
        "scene_id": scene_id,
        "intent": infer_intent(calls),
        "summary": summary,
        "actions": actions,
        "camera": camera,
        "generation": generation,
        "required_assets": required_assets,
        "tool_calls": [
            {
                "name": str(c.get("name") or ""),
                "arguments": c.get("arguments") if isinstance(c.get("arguments"), dict) else {},
                "note": c.get("note") or "",
            }
            for c in calls
        ],
        "risk_level": "high" if confirm else "normal",
        "requires_confirmation": confirm,
        "thinking": list(raw.get("thinking") or []),
        "error": raw.get("error"),
    }
