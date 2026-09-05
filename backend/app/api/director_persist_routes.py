"""导演台角色 / 分镜 / 姿势 / 自定义动画持久化。按 User + Project 隔离。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_db
from ..db.models import (
    DirectorCharacter,
    DirectorCustomAnimation,
    DirectorLibraryMeta,
    DirectorPose,
    DirectorScene,
)
from ..api.director_asset_routes import persist_without_data_urls
from ..db.ownership import DirectorScope, get_director_scope

router = APIRouter(prefix="/api/director", tags=["director-persist"])


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _scene_out(row) -> dict:
    data = dict(row.data_json) if isinstance(row.data_json, dict) else {}
    if row.current_generation_id:
        data["generationId"] = row.current_generation_id
        data["currentGenerationId"] = row.current_generation_id
    return data


def _owned(model, scope: DirectorScope):
    return (model.user_id == scope.user_id) & (model.project_id == scope.project_id)


async def _meta(db: AsyncSession, scope: DirectorScope) -> DirectorLibraryMeta:
    result = await db.execute(select(DirectorLibraryMeta).where(_owned(DirectorLibraryMeta, scope)))
    row = result.scalar_one_or_none()
    if row:
        return row
    row = DirectorLibraryMeta(
        user_id=scope.user_id,
        project_id=scope.project_id,
        favorites_json=[],
        recent_ids_json=[],
        current_scene_id="",
        updated_at=_now(),
    )
    db.add(row)
    await db.flush()
    return row


async def _owned_row(db: AsyncSession, model, pk_attr: str, pk_val: str, scope: DirectorScope):
    result = await db.execute(
        select(model).where(getattr(model, pk_attr) == pk_val, _owned(model, scope))
    )
    return result.scalar_one_or_none()


@router.get("/library")
async def get_library(
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    characters = (await db.execute(select(DirectorCharacter).where(_owned(DirectorCharacter, scope)))).scalars().all()
    poses = (await db.execute(select(DirectorPose).where(_owned(DirectorPose, scope)))).scalars().all()
    anims = (await db.execute(select(DirectorCustomAnimation).where(_owned(DirectorCustomAnimation, scope)))).scalars().all()
    meta = await _meta(db, scope)
    return {
        "characters": [row.data_json for row in characters if isinstance(row.data_json, dict)],
        "savedPoses": [row.data_json for row in poses if isinstance(row.data_json, dict)],
        "customAnimations": [row.data_json for row in anims if isinstance(row.data_json, dict)],
        "favorites": meta.favorites_json or [],
        "recentIds": meta.recent_ids_json or [],
    }


@router.put("/library")
async def put_library(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    """只 upsert 当前 User+Project。空数组拒绝，以免误清空。不信任 body 里的 user_id。"""
    if not isinstance(payload, dict):
        raise HTTPException(400, "非法请求体")
    incoming_chars = payload.get("characters")
    incoming_poses = payload.get("savedPoses")
    incoming_anims = payload.get("customAnimations")
    if incoming_chars is None and incoming_poses is None and incoming_anims is None:
        raise HTTPException(400, "缺少 characters / savedPoses / customAnimations，拒绝同步")
    if incoming_chars is not None and not isinstance(incoming_chars, list):
        raise HTTPException(400, "characters 必须是数组")
    if incoming_poses is not None and not isinstance(incoming_poses, list):
        raise HTTPException(400, "savedPoses 必须是数组")
    if incoming_anims is not None and not isinstance(incoming_anims, list):
        raise HTTPException(400, "customAnimations 必须是数组")
    incoming_chars = incoming_chars if isinstance(incoming_chars, list) else []
    incoming_poses = incoming_poses if isinstance(incoming_poses, list) else []
    incoming_anims = incoming_anims if isinstance(incoming_anims, list) else []
    if not incoming_chars and not incoming_poses and not incoming_anims:
        raise HTTPException(400, "拒绝空库同步：不会删除已有角色/姿势/动画")

    payload = await persist_without_data_urls(payload, db, scope)
    incoming_chars = payload.get("characters") or []
    incoming_poses = payload.get("savedPoses") or []
    incoming_anims = payload.get("customAnimations") or []

    now = _now()
    for item in incoming_chars:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        cid = str(item["id"])
        row = await _owned_row(db, DirectorCharacter, "id", cid, scope)
        if row is None:
            clash = await db.get(DirectorCharacter, cid)
            if clash is not None:
                continue
            row = DirectorCharacter(id=cid, user_id=scope.user_id, project_id=scope.project_id)
            db.add(row)
        row.user_id = scope.user_id
        row.project_id = scope.project_id
        row.name = str(item.get("name") or "")
        row.template_id = str(item.get("templateId") or "")
        row.source_type = str(item.get("sourceType") or "official")
        row.primary_asset_id = item.get("primaryAssetId") or item.get("primary_asset_id")
        row.reference_asset_id = item.get("referenceAssetId") or item.get("reference_asset_id")
        row.thumbnail_asset_id = item.get("thumbnailAssetId") or item.get("thumbnail_asset_id")
        row.data_json = item
        row.updated_at = float(item.get("updatedAt") or now)

    for item in incoming_poses:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        pid = str(item["id"])
        row = await _owned_row(db, DirectorPose, "id", pid, scope)
        if row is None:
            clash = await db.get(DirectorPose, pid)
            if clash is not None:
                continue
            row = DirectorPose(id=pid, user_id=scope.user_id, project_id=scope.project_id)
            db.add(row)
        row.user_id = scope.user_id
        row.project_id = scope.project_id
        row.character_id = str(item.get("characterId") or "")
        row.name = str(item.get("name") or "")
        row.data_json = item
        row.updated_at = now

    for item in incoming_anims:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        aid = str(item["id"])
        row = await _owned_row(db, DirectorCustomAnimation, "id", aid, scope)
        if row is None:
            clash = await db.get(DirectorCustomAnimation, aid)
            if clash is not None:
                continue
            row = DirectorCustomAnimation(id=aid, user_id=scope.user_id, project_id=scope.project_id)
            db.add(row)
        row.user_id = scope.user_id
        row.project_id = scope.project_id
        row.character_id = str(item["characterId"]) if item.get("characterId") else None
        row.name = str(item.get("name") or "")
        row.data_json = item
        row.updated_at = float(item.get("updatedAt") or now)

    meta = await _meta(db, scope)
    if "favorites" in payload:
        meta.favorites_json = payload.get("favorites") or []
    if "recentIds" in payload:
        meta.recent_ids_json = payload.get("recentIds") or []
    meta.updated_at = now
    await db.commit()
    return await get_library(db, scope)


@router.get("/scenebook")
async def get_scenebook(
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    scenes = (await db.execute(select(DirectorScene).where(_owned(DirectorScene, scope)))).scalars().all()
    meta = await _meta(db, scope)
    return {
        "currentId": meta.current_scene_id,
        "scenes": [_scene_out(row) for row in scenes],
    }


@router.put("/scenebook")
async def put_scenebook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    if not isinstance(payload, dict):
        raise HTTPException(400, "非法请求体")
    incoming = payload.get("scenes")
    if incoming is None:
        raise HTTPException(400, "缺少 scenes，拒绝同步")
    if not isinstance(incoming, list):
        raise HTTPException(400, "scenes 必须是数组")
    if not incoming:
        raise HTTPException(400, "拒绝空分镜同步：不会删除已有分镜")

    payload = await persist_without_data_urls(payload, db, scope)
    incoming = payload.get("scenes") or []

    now = _now()
    current_id = str(payload.get("currentId") or "")
    for item in incoming:
        if not isinstance(item, dict) or not item.get("sceneId"):
            continue
        sid = str(item["sceneId"])
        row = await _owned_row(db, DirectorScene, "scene_id", sid, scope)
        if row is None:
            clash = await db.get(DirectorScene, sid)
            if clash is not None:
                continue
            row = DirectorScene(
                scene_id=sid,
                user_id=scope.user_id,
                project_id=scope.project_id,
                created_at=now,
            )
            db.add(row)
        row.user_id = scope.user_id
        row.project_id = scope.project_id
        row.scene_name = str(item.get("sceneName") or "")
        row.is_current = sid == current_id
        row.background_asset_id = item.get("backgroundAssetId") or item.get("background_asset_id")
        row.reference_asset_id = item.get("referenceAssetId") or item.get("reference_asset_id")
        row.composition_asset_id = item.get("compositionAssetId") or item.get("composition_asset_id") or item.get("imageAssetId")
        row.current_generation_id = (
            item.get("currentGenerationId") or item.get("generationId") or item.get("current_generation_id")
        )
        row.data_json = item
        row.updated_at = now
    meta = await _meta(db, scope)
    if current_id:
        meta.current_scene_id = current_id
    meta.updated_at = now
    await db.commit()
    return await get_scenebook(db, scope)
