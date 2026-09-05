"""Executor：验证后的 Plan 只能走白名单 Tool。不重新理解用户意图。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.ownership import DirectorScope
from ..generation.versions import attach_output_asset, dump_generation, get_owned_generation, set_scene_current
from .errors import FORBIDDEN_TOOLS, GENERATION_FAILED, RESOURCE_NOT_FOUND, TOOL_ERROR, WALLET_INSUFFICIENT, AgentError
from .prompt_gen import generate_prompt
from .registry import is_allowed, needs_confirm
from .scene_tools import apply_scene_tool
from .validator import FORBIDDEN_TOOL_NAMES, validate_plan

SCENE_TOOLS = {
    "create_character",
    "add_character_to_scene",
    "remove_character_from_scene",
    "move_character",
    "rotate_character",
    "scale_character",
    "set_character_action",
    "set_character_pose",
    "set_character_expression",
    "create_scene",
    "rename_scene",
    "delete_scene",
    "update_scene",
    "add_prop",
    "remove_prop",
    "move_prop",
    "rotate_prop",
    "scale_prop",
    "change_environment",
    "place_room_preset",
    "create_camera",
    "select_camera",
    "move_camera",
    "rotate_camera",
    "set_camera_fov",
    "set_camera_target",
    "set_camera_motion",
    "set_camera",
    "create_shot",
    "delete_shot",
    "duplicate_shot",
    "update_shot",
    "set_shot_duration",
    "set_shot_description",
    "set_shot_type",
    "update_storyboard",
    "create_keyframe",
    "update_keyframe",
    "delete_keyframe",
    "set_animation_duration",
    "update_timeline",
}


async def execute_plan(
    db: AsyncSession,
    scope: DirectorScope,
    plan: dict[str, Any],
    context: dict[str, Any],
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    validate_plan(plan, scope, context)
    if plan.get("requires_confirmation") and not confirm:
        return {
            "executed": False,
            "requires_confirmation": True,
            "tool_results": [],
            "generation_id": None,
            "message": f"我准备执行高风险操作：{plan.get('summary') or '删除/恢复'}，是否继续？",
        }

    results: list[dict[str, Any]] = []
    generation_id = None
    scene_id = str(plan.get("scene_id") or context.get("scene_id") or "")

    for call in plan.get("tool_calls") or []:
        name = str(call.get("name") or "")
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        if name in FORBIDDEN_TOOL_NAMES or not is_allowed(name):
            raise AgentError(FORBIDDEN_TOOLS, "禁止执行未授权 Tool")
        if needs_confirm(name) and not confirm:
            results.append({"name": name, "success": False, "error_code": "CONFIRMATION_REQUIRED", "message": f"需要确认才能执行 {name}"})
            return {
                "executed": False,
                "requires_confirmation": True,
                "tool_results": results,
                "generation_id": generation_id,
                "message": f"我准备执行「{call.get('note') or name}」，是否继续？",
            }
        try:
            if name == "generate_prompt":
                out = generate_prompt(str(args.get("kind") or "video"), {**context, **args})
                result = {"success": True, "name": name, "message": "已生成提示词", **out}
            elif name in {"generate_image", "generate_video"}:
                result = await _generate(db, scope, plan, context, args, kind="video" if name == "generate_video" else "image")
                generation_id = result.get("generation_id") or generation_id
            elif name == "restore_generation":
                result = await _restore(db, scope, args)
                generation_id = result.get("generation_id") or generation_id
            elif name in {"undo_last", "redo_last", "send_composition"}:
                result = {"success": True, "name": name, "message": "该操作由导演台前端执行", "deferred": True}
            elif name in SCENE_TOOLS:
                result = await apply_scene_tool(db, scope, scene_id=scene_id, name=name, arguments=args, seed=context)
                result["name"] = name
                if result.get("scene_id") and name in {"create_shot", "duplicate_shot", "create_scene"}:
                    scene_id = str(result["scene_id"])
            else:
                raise AgentError(TOOL_ERROR, f"未实现 Tool：{name}")
        except AgentError as exc:
            result = {"success": False, "name": name, "error_code": exc.code, "message": exc.message, "details": exc.details}
            results.append(result)
            return {
                "executed": False,
                "requires_confirmation": False,
                "tool_results": results,
                "generation_id": generation_id,
                "message": exc.message,
                "error_code": exc.code,
            }
        except Exception:
            result = {"success": False, "name": name, "error_code": TOOL_ERROR, "message": "Tool 执行失败"}
            results.append(result)
            return {
                "executed": False,
                "requires_confirmation": False,
                "tool_results": results,
                "generation_id": generation_id,
                "message": "Tool 执行失败",
                "error_code": TOOL_ERROR,
            }
        results.append(result)

    await db.commit()
    ok = all(r.get("success") for r in results) if results else True
    summary = plan.get("summary") or "已完成导演指令"
    return {
        "executed": ok,
        "requires_confirmation": False,
        "tool_results": results,
        "generation_id": generation_id,
        "message": summary if ok else "部分步骤失败",
        "scene_id": scene_id,
    }


async def _generate(
    db: AsyncSession,
    scope: DirectorScope,
    plan: dict[str, Any],
    context: dict[str, Any],
    args: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    from ..api.director_generation_routes import GenerateRequest, _persist_capture_asset, _prepare_row
    from ..generation.prompt_engine import compile_prompts
    from ..generation.router import generate_image, local_path_from_url

    ctx = {**context, "user_message": context.get("user_message") or plan.get("summary") or ""}
    compiled = compile_prompts(kind=kind, context=ctx, shot=args, extra=str(args.get("prompt") or ctx.get("user_message") or ""))
    prompt = str(args.get("prompt") or compiled.get("image_prompt") or compiled.get("video_prompt") or ctx.get("user_message") or plan.get("summary") or "")
    image_path = None
    capture_ids: list[str] = []
    if kind == "video":
        extra_refs = [u for u in (ctx.get("attachment_urls") or []) if isinstance(u, str)]
        for raw in (
            args.get("image_url"),
            args.get("image_data_url"),
            ctx.get("image_url"),
            ctx.get("composition_url"),
            ctx.get("backdrop_url"),
            *extra_refs,
        ):
            if not raw or not isinstance(raw, str):
                continue
            if raw.startswith("data:"):
                image_path, capture_id = await _persist_capture_asset(raw, db, scope)
                if capture_id:
                    capture_ids.append(capture_id)
                break
            resolved = local_path_from_url(raw)
            if resolved:
                image_path = resolved
                break
    body = GenerateRequest(
        kind=kind,
        prompt=prompt,
        scene_id=str(plan.get("scene_id") or context.get("scene_id") or ""),
        shot_id=str(args.get("shot_id") or plan.get("scene_id") or context.get("scene_id") or ""),
        project_id=scope.project_id,
        parent_generation_id=args.get("parent_generation_id") or args.get("parent"),
        duration=float(args.get("duration") or 5),
        aspect_ratio=str(args.get("aspect_ratio") or ctx.get("aspect_ratio") or "9:16"),
        image_url=str(ctx.get("image_url") or ctx.get("composition_url") or ctx.get("backdrop_url") or "") or None,
        context=ctx,
        shot=args,
    )
    extra = {
        "width": args.get("width"),
        "height": args.get("height"),
        "duration": args.get("duration"),
        "user_message": ctx.get("user_message"),
        "plan_id": plan.get("plan_id"),
    }
    row, reused = await _prepare_row(
        db,
        body,
        scope,
        kind=kind,
        prompt=prompt,
        negative_prompt=str(args.get("negative_prompt") or compiled.get("negative_prompt") or ""),
        extra=extra,
        reference_assets=capture_ids,
    )
    if reused:
        return {"success": True, "name": f"generate_{kind}", "message": "复用已有生成", **dump_generation(row, idempotent=True)}
    row.status = "running"
    await db.commit()
    try:
        if kind == "video":
            from ..billing.access import run_charged_video
            from ..billing.errors import BillingError

            try:
                result = await run_charged_video(
                    db,
                    scope.user_id,
                    prompt=prompt,
                    duration=int(float(args.get("duration") or 5)),
                    aspect_ratio=str(args.get("aspect_ratio") or ctx.get("aspect_ratio") or "9:16"),
                    image_path=image_path,
                )
            except BillingError as exc:
                row.status = "failed"
                row.error = str(exc)
                await db.commit()
                raise AgentError(WALLET_INSUFFICIENT if exc.http_status == 402 else GENERATION_FAILED, str(exc), http_status=exc.http_status) from exc
        else:
            result = await generate_image(prompt=prompt, width=args.get("width"), height=args.get("height"))
    except AgentError:
        raise
    except Exception as exc:
        row.status = "failed"
        row.error = str(exc)
        await db.commit()
        raise AgentError(GENERATION_FAILED, "生成失败") from exc
    row.model = result.get("model") or row.model
    await attach_output_asset(db, scope=scope, row=row, path=result["path"], kind=kind)
    row.status = "completed"
    await set_scene_current(db, scope=scope, scene_id=body.scene_id, generation=row)
    await db.flush()
    return {"success": True, "name": f"generate_{kind}", "message": f"已生成 {kind}", **dump_generation(row)}


async def _restore(db: AsyncSession, scope: DirectorScope, args: dict[str, Any]) -> dict[str, Any]:
    gid = str(args.get("generation_id") or "")
    row = await get_owned_generation(db, generation_id=gid, scope=scope)
    if row is None:
        raise AgentError(RESOURCE_NOT_FOUND, "生成记录不存在")
    await set_scene_current(db, scope=scope, scene_id=row.scene_id, generation=row)
    await db.flush()
    return {"success": True, "name": "restore_generation", "message": "已恢复历史版本", **dump_generation(row)}
