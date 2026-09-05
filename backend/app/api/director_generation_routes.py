"""导演台生成 API。版本链 + 幂等，结果落 Asset，不覆盖旧文件。"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..assets.dataurl import decode_data_url
from ..assets.service import create_from_bytes, get_owned_asset, mark_deleted
from ..billing.access import run_charged_video
from ..billing.errors import BillingError
from ..core.exceptions import InsufficientBalanceError, ProviderNotConfiguredError, ProviderUnavailableError
from ..auth.dependencies import get_current_user
from ..db.database import get_db
from ..db.models import DirectorGeneration, DirectorScene, User
from ..db.ownership import DirectorScope, get_director_scope, resolve_director_scope
from ..generation.prompt_engine import compile_prompts
from ..generation.router import generate_image, local_path_from_url
from ..generation.versions import (
    attach_output_asset,
    build_input_snapshot,
    collect_character_ids,
    collect_reference_assets,
    compute_generation_key,
    dump_generation,
    find_idempotent,
    get_owned_generation,
    get_user_generation,
    next_version_number,
    normalize_status,
    resolve_parent,
    set_scene_current,
)
from ..storage.local import storage

router = APIRouter(prefix="/api/director/generate", tags=["director-generation"])

_INFLIGHT: dict[str, float] = {}
_INFLIGHT_TTL = 960.0


def _begin_generation(user_id: str, project_id: str, scene_id: str, kind: str) -> str:
    key = f"{user_id}:{project_id}:{scene_id or '_'}:{kind}"
    now = time.time()
    stale = [k for k, ts in _INFLIGHT.items() if now - ts > _INFLIGHT_TTL]
    for k in stale:
        _INFLIGHT.pop(k, None)
    if key in _INFLIGHT:
        raise HTTPException(409, "同一镜头正在生成，请等待当前任务结束")
    _INFLIGHT[key] = now
    return key


def _end_generation(key: str) -> None:
    _INFLIGHT.pop(key, None)


class GenerateRequest(BaseModel):
    kind: str = "image"
    prompt: str = ""
    negative_prompt: str = ""
    scene_id: str = ""
    shot_id: str = ""
    project_id: str = ""
    parent_generation_id: str | None = None
    duration: float = 5
    aspect_ratio: str = "9:16"
    width: int | None = None
    height: int | None = None
    image_url: str | None = None
    image_data_url: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    shot: dict[str, Any] = Field(default_factory=dict)


async def _persist_capture_asset(data_url: str, db, scope) -> tuple[str, str]:
    if not data_url or "," not in data_url:
        raise HTTPException(400, "无效的截图数据")
    raw, _mime, ext = decode_data_url(data_url)
    row, _ = await create_from_bytes(
        db,
        user_id=scope.user_id,
        project_id=scope.project_id,
        data=raw,
        filename=f"capture{ext}",
        asset_type="reference_image",
        name="capture",
    )
    await db.flush()
    if not row.storage_key:
        raise HTTPException(400, "截图未能保存为 Asset")
    return str(storage.get_path(row.storage_key)), row.id


async def _prepare_row(
    db: AsyncSession,
    body: GenerateRequest,
    scope: DirectorScope,
    *,
    kind: str,
    prompt: str,
    negative_prompt: str,
    extra: dict[str, Any],
    reference_assets: list[str],
    model: str = "",
) -> tuple[DirectorGeneration, bool]:
    snapshot = build_input_snapshot(
        user_id=scope.user_id,
        project_id=scope.project_id,
        scene_id=body.scene_id,
        kind=kind,
        prompt=prompt,
        model=model,
        character_ids=collect_character_ids(body.context, body.shot),
        reference_assets=reference_assets,
        camera=body.shot if isinstance(body.shot, dict) else {},
        extra=extra,
    )
    key = compute_generation_key(snapshot)
    existing = await find_idempotent(db, scope=scope, generation_key=key)
    if existing:
        if normalize_status(existing.status) == "completed":
            await set_scene_current(db, scope=scope, scene_id=body.scene_id, generation=existing)
            await db.commit()
        return existing, True

    parent = await resolve_parent(
        db,
        scope=scope,
        scene_id=body.scene_id,
        explicit=body.parent_generation_id,
    )
    version = await next_version_number(db, scope=scope, scene_id=body.scene_id, kind=kind)
    row = DirectorGeneration(
        generation_id=uuid.uuid4().hex[:16],
        user_id=scope.user_id,
        project_id=scope.project_id,
        scene_id=body.scene_id,
        shot_id=body.shot_id or body.scene_id,
        kind=kind,
        title=(prompt or "").strip()[:80],
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model,
        status="pending",
        parent_generation_id=parent.generation_id if parent else None,
        version_number=version,
        generation_key=key,
        input_snapshot_json=snapshot,
        parameters_json=extra,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, False


async def _scope_from_request(
    body: GenerateRequest,
    db: AsyncSession,
    user: User,
    project_id: str | None,
) -> DirectorScope:
    return await resolve_director_scope(db, user, project_id or body.project_id)


@router.post("/image")
async def post_image(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: str | None = Query(None),
) -> dict:
    scope = await _scope_from_request(body, db, user, project_id)
    compiled = compile_prompts(kind="image", context=body.context, shot=body.shot, extra=body.prompt)
    prompt = body.prompt.strip() or compiled["image_prompt"]
    extra = {"width": body.width, "height": body.height, "aspect_ratio": body.aspect_ratio}
    row, reused = await _prepare_row(
        db,
        body,
        scope,
        kind="image",
        prompt=prompt,
        negative_prompt=body.negative_prompt or compiled["negative_prompt"],
        extra=extra,
        reference_assets=collect_reference_assets(body.context, body.image_url),
    )
    if reused:
        return {**dump_generation(row, idempotent=True), "prompt": row.prompt, "compiled": compiled}

    lock = _begin_generation(scope.user_id, scope.project_id, body.scene_id, "image")
    row.status = "running"
    await db.commit()
    try:
        try:
            result = await generate_image(prompt=prompt, width=body.width, height=body.height)
        except (ProviderNotConfiguredError, ProviderUnavailableError) as exc:
            row.status = "failed"
            row.error = str(exc)
            await db.commit()
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            row.status = "failed"
            row.error = str(exc)
            await db.commit()
            raise HTTPException(502, f"图片生成失败：{exc}") from exc
        row.model = result.get("model") or row.model
        await attach_output_asset(db, scope=scope, row=row, path=result["path"], kind="image")
        row.status = "completed"
        await set_scene_current(db, scope=scope, scene_id=body.scene_id, generation=row)
        await db.commit()
        return {**dump_generation(row), "prompt": prompt, "negative_prompt": row.negative_prompt, "compiled": compiled}
    finally:
        _end_generation(lock)


async def _fail_generation(db: AsyncSession, generation_id: str, message: str) -> None:
    row = (
        await db.execute(select(DirectorGeneration).where(DirectorGeneration.generation_id == generation_id))
    ).scalar_one_or_none()
    if row is None:
        return
    row.status = "failed"
    row.error = message
    await db.commit()


async def _complete_video_job(
    *,
    generation_id: str,
    user_id: str,
    project_id: str,
    scene_id: str,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    image_path: str | None,
    lock: str,
) -> HTTPException | None:
    from ..db.database import async_session
    from ..db.models import Project

    async with async_session() as db:
        try:
            user = await db.get(User, user_id)
            project = await db.get(Project, project_id)
            if user is None or project is None:
                await _fail_generation(db, generation_id, "项目已不存在")
                return HTTPException(404, "项目已不存在")
            scope = DirectorScope(user=user, project=project)
            row = await get_owned_generation(db, generation_id=generation_id, scope=scope)
            if row is None:
                return HTTPException(404, "生成记录不存在")
            result = await run_charged_video(
                db,
                user_id,
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                image_path=image_path,
            )
            row.model = result.get("model") or row.model
            await attach_output_asset(db, scope=scope, row=row, path=result["path"], kind="video")
            row.status = "completed"
            await set_scene_current(db, scope=scope, scene_id=scene_id, generation=row)
            await db.commit()
            return None
        except BillingError as exc:
            await _fail_generation(db, generation_id, str(exc))
            return HTTPException(exc.http_status, str(exc))
        except InsufficientBalanceError as exc:
            await _fail_generation(db, generation_id, str(exc))
            return HTTPException(402, str(exc))
        except (ProviderNotConfiguredError, ProviderUnavailableError) as exc:
            await _fail_generation(db, generation_id, str(exc))
            return HTTPException(503, str(exc))
        except Exception as exc:
            await _fail_generation(db, generation_id, f"视频生成失败：{exc}")
            return HTTPException(502, f"视频生成失败：{exc}")
        finally:
            _end_generation(lock)


@router.post("/video")
async def post_video(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: str | None = Query(None),
    wait: bool = Query(True),
) -> dict:
    scope = await _scope_from_request(body, db, user, project_id)
    compiled = compile_prompts(kind="video", context=body.context, shot=body.shot, extra=body.prompt)
    prompt = body.prompt.strip() or compiled["video_prompt"]
    image_path = local_path_from_url(body.image_url)
    capture_id = ""
    if not image_path and body.image_data_url:
        image_path, capture_id = await _persist_capture_asset(body.image_data_url, db, scope)
        await db.commit()
    extra = {"duration": body.duration, "aspect_ratio": body.aspect_ratio, "has_image": bool(image_path)}
    refs = collect_reference_assets(body.context, body.image_url, [capture_id] if capture_id else None)
    row, reused = await _prepare_row(
        db,
        body,
        scope,
        kind="video",
        prompt=prompt,
        negative_prompt=body.negative_prompt or compiled["negative_prompt"],
        extra=extra,
        reference_assets=refs,
    )
    if reused:
        return {**dump_generation(row, idempotent=True), "prompt": row.prompt, "compiled": compiled}

    lock = _begin_generation(scope.user_id, scope.project_id, body.scene_id, "video")
    row.status = "running"
    await db.commit()
    job = dict(
        generation_id=row.generation_id,
        user_id=scope.user_id,
        project_id=scope.project_id,
        scene_id=body.scene_id,
        prompt=prompt,
        duration=int(body.duration or 5),
        aspect_ratio=body.aspect_ratio,
        image_path=image_path,
        lock=lock,
    )
    if not wait:
        asyncio.create_task(_complete_video_job(**job))
        return {**dump_generation(row), "prompt": prompt, "compiled": compiled}
    error = await _complete_video_job(**job)
    await db.refresh(row)
    if error:
        raise error
    return {**dump_generation(row), "prompt": prompt, "compiled": compiled}


@router.get("/history")
async def history(
    scene_id: str = "",
    shot_id: str = "",
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    stmt = select(DirectorGeneration).where(
        DirectorGeneration.user_id == scope.user_id,
        DirectorGeneration.project_id == scope.project_id,
    )
    if shot_id:
        stmt = stmt.where(DirectorGeneration.shot_id == shot_id)
    elif scene_id:
        stmt = stmt.where(DirectorGeneration.scene_id == scene_id)
    stmt = stmt.order_by(DirectorGeneration.id.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [dump_generation(r) for r in rows]}


class UpdateWorkRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)


@router.get("/works")
async def list_works(
    kind: str = "",
    q: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    stmt = select(DirectorGeneration).where(DirectorGeneration.user_id == user.id)
    if kind in ("image", "video"):
        stmt = stmt.where(DirectorGeneration.kind == kind)
    query = q.strip()
    if query:
        like = f"%{query}%"
        stmt = stmt.where(
            or_(
                DirectorGeneration.title.ilike(like),
                DirectorGeneration.prompt.ilike(like),
            )
        )
    stmt = stmt.order_by(DirectorGeneration.id.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [dump_generation(r) for r in rows]}


@router.get("/{generation_id}")
async def get_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    row = await get_owned_generation(db, generation_id=generation_id, scope=scope)
    if row is None:
        raise HTTPException(404, "生成记录不存在")
    return dump_generation(row)


@router.post("/{generation_id}/restore")
async def restore_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    row = await get_owned_generation(db, generation_id=generation_id, scope=scope)
    if row is None:
        raise HTTPException(404, "生成记录不存在")
    if normalize_status(row.status) != "completed" or not row.output_asset_id:
        raise HTTPException(409, "只能恢复已完成且带有结果的版本")
    await set_scene_current(db, scope=scope, scene_id=row.scene_id, generation=row)
    await db.commit()
    return {"restored": True, **dump_generation(row)}


@router.patch("/{generation_id}")
async def update_work(
    generation_id: str,
    body: UpdateWorkRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = await get_user_generation(db, generation_id=generation_id, user_id=user.id)
    if row is None:
        raise HTTPException(404, "生成记录不存在")
    row.title = body.title.strip()[:128]
    await db.commit()
    await db.refresh(row)
    return dump_generation(row)


@router.delete("/{generation_id}")
async def delete_work(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = await get_user_generation(db, generation_id=generation_id, user_id=user.id)
    if row is None:
        raise HTTPException(404, "生成记录不存在")
    scenes = (
        await db.execute(
            select(DirectorScene).where(
                DirectorScene.user_id == user.id,
                DirectorScene.current_generation_id == generation_id,
            )
        )
    ).scalars().all()
    for scene in scenes:
        scene.current_generation_id = None
        data = dict(scene.data_json) if isinstance(scene.data_json, dict) else {}
        if data.get("generationId") == generation_id or data.get("currentGenerationId") == generation_id:
            data.pop("generationId", None)
            data.pop("currentGenerationId", None)
            scene.data_json = data
    asset_id = row.output_asset_id
    project_id = row.project_id
    await db.delete(row)
    await db.flush()
    if asset_id:
        asset = await get_owned_asset(db, asset_id=asset_id, user_id=user.id, project_id=project_id)
        if asset is not None:
            try:
                await mark_deleted(db, asset)
            except HTTPException:
                pass
    await db.commit()
    return {"deleted": True, "generation_id": generation_id}
