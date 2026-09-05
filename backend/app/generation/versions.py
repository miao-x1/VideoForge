"""Generation 版本链与幂等。不覆盖旧文件，不删除历史行。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..assets.service import asset_file_url, create_from_bytes
from ..db.models import DirectorGeneration, DirectorScene
from ..db.ownership import DirectorScope

STATUSES = ("pending", "running", "completed", "failed", "cancelled")
_ACTIVE = ("pending", "running")
_STATUS_ALIASES = {
    "queued": "pending",
    "ok": "completed",
    "success": "completed",
    "error": "failed",
}


def normalize_status(value: str | None) -> str:
    raw = (value or "pending").strip().lower()
    return _STATUS_ALIASES.get(raw, raw if raw in STATUSES else "pending")


def compute_generation_key(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_input_snapshot(
    *,
    user_id: str,
    project_id: str,
    scene_id: str,
    kind: str,
    prompt: str,
    model: str,
    character_ids: list[str],
    reference_assets: list[str],
    camera: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "project_id": project_id,
        "scene_id": scene_id or "",
        "kind": kind,
        "prompt": (prompt or "").strip(),
        "model": model or "",
        "character_ids": sorted({str(x) for x in character_ids if x}),
        "reference_assets": sorted({str(x) for x in reference_assets if x}),
        "camera": camera or {},
        "extra": extra or {},
    }


def collect_character_ids(context: dict | None, shot: dict | None) -> list[str]:
    ids: list[str] = []
    for blob in (context, shot):
        if not isinstance(blob, dict):
            continue
        for key in ("character_ids", "characterIds"):
            raw = blob.get(key)
            if isinstance(raw, list):
                ids.extend(str(x) for x in raw if x)
        cid = blob.get("character_id") or blob.get("characterId")
        if cid:
            ids.append(str(cid))
        for ch in blob.get("characters") or []:
            if isinstance(ch, dict) and (ch.get("id") or ch.get("characterId")):
                ids.append(str(ch.get("id") or ch.get("characterId")))
            elif isinstance(ch, str):
                ids.append(ch)
    return ids


def collect_reference_assets(
    context: dict | None,
    image_url: str | None = None,
    extra_ids: list[str] | None = None,
) -> list[str]:
    refs: list[str] = list(extra_ids or [])
    if image_url:
        refs.append(image_url)
    if isinstance(context, dict):
        for key in ("reference_assets", "referenceAssetIds", "reference_asset_ids"):
            raw = context.get(key)
            if isinstance(raw, list):
                refs.extend(str(x) for x in raw if x)
        rid = context.get("reference_asset_id") or context.get("referenceAssetId")
        if rid:
            refs.append(str(rid))
    return refs


def display_title(row: DirectorGeneration) -> str:
    raw = (getattr(row, "title", None) or "").strip()
    if raw:
        return raw
    prompt = (row.prompt or "").strip()
    if prompt:
        return prompt[:40] + ("…" if len(prompt) > 40 else "")
    kind = "视频" if row.kind == "video" else "图片"
    return f"{kind} {row.generation_id[:6]}"


def dump_generation(row: DirectorGeneration, *, idempotent: bool = False) -> dict[str, Any]:
    url = row.result_url
    if row.output_asset_id and row.project_id:
        url = asset_file_url(row.output_asset_id, row.project_id)
    extra = row.parameters_json if isinstance(row.parameters_json, dict) else {}
    return {
        "generation_id": row.generation_id,
        "parent_generation_id": row.parent_generation_id,
        "version": row.version_number or 1,
        "version_number": row.version_number or 1,
        "kind": row.kind,
        "title": display_title(row),
        "project_id": row.project_id,
        "scene_id": row.scene_id,
        "shot_id": row.shot_id,
        "prompt": row.prompt,
        "negative_prompt": row.negative_prompt,
        "model": row.model,
        "status": normalize_status(row.status),
        "error_message": row.error,
        "error": row.error,
        "output_asset_id": row.output_asset_id,
        "preview_asset": row.output_asset_id,
        "url": url,
        "duration": extra.get("duration"),
        "aspect_ratio": extra.get("aspect_ratio"),
        "generation_key": row.generation_key,
        "input_snapshot": row.input_snapshot_json,
        "created_at": row.created_at,
        "idempotent": idempotent,
    }


async def get_owned_generation(
    db: AsyncSession,
    *,
    generation_id: str,
    scope: DirectorScope,
) -> DirectorGeneration | None:
    result = await db.execute(
        select(DirectorGeneration).where(
            DirectorGeneration.generation_id == generation_id,
            DirectorGeneration.user_id == scope.user_id,
            DirectorGeneration.project_id == scope.project_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_generation(
    db: AsyncSession,
    *,
    generation_id: str,
    user_id: str,
) -> DirectorGeneration | None:
    result = await db.execute(
        select(DirectorGeneration).where(
            DirectorGeneration.generation_id == generation_id,
            DirectorGeneration.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def find_idempotent(
    db: AsyncSession,
    *,
    scope: DirectorScope,
    generation_key: str,
) -> DirectorGeneration | None:
    rows = (
        await db.execute(
            select(DirectorGeneration)
            .where(
                DirectorGeneration.user_id == scope.user_id,
                DirectorGeneration.project_id == scope.project_id,
                DirectorGeneration.generation_key == generation_key,
            )
            .order_by(DirectorGeneration.id.desc())
        )
    ).scalars().all()
    for row in rows:
        status = normalize_status(row.status)
        if status in _ACTIVE or status == "completed":
            return row
    return None


async def next_version_number(db: AsyncSession, *, scope: DirectorScope, scene_id: str, kind: str) -> int:
    result = await db.execute(
        select(func.max(DirectorGeneration.version_number)).where(
            DirectorGeneration.user_id == scope.user_id,
            DirectorGeneration.project_id == scope.project_id,
            DirectorGeneration.scene_id == (scene_id or ""),
            DirectorGeneration.kind == kind,
        )
    )
    current = result.scalar() or 0
    return int(current) + 1


async def resolve_parent(
    db: AsyncSession,
    *,
    scope: DirectorScope,
    scene_id: str,
    explicit: str | None,
) -> DirectorGeneration | None:
    if explicit:
        return await get_owned_generation(db, generation_id=explicit, scope=scope)
    scene = await db.get(DirectorScene, scene_id) if scene_id else None
    if (
        scene
        and scene.user_id == scope.user_id
        and scene.project_id == scope.project_id
        and scene.current_generation_id
    ):
        return await get_owned_generation(db, generation_id=scene.current_generation_id, scope=scope)
    return None


async def set_scene_current(db: AsyncSession, *, scope: DirectorScope, scene_id: str, generation: DirectorGeneration) -> None:
    if not scene_id:
        return
    scene = (
        await db.execute(
            select(DirectorScene).where(
                DirectorScene.scene_id == scene_id,
                DirectorScene.user_id == scope.user_id,
                DirectorScene.project_id == scope.project_id,
            )
        )
    ).scalar_one_or_none()
    if scene is None:
        return
    scene.current_generation_id = generation.generation_id
    data = dict(scene.data_json) if isinstance(scene.data_json, dict) else {}
    data["generationId"] = generation.generation_id
    data["currentGenerationId"] = generation.generation_id
    url = dump_generation(generation).get("url")
    if generation.kind == "image" and url:
        data["imageUrl"] = url
    if generation.kind == "video" and url:
        data["videoUrl"] = url
    scene.data_json = data


async def attach_output_asset(
    db: AsyncSession,
    *,
    scope: DirectorScope,
    row: DirectorGeneration,
    path: str,
    kind: str,
) -> None:
    raw = Path(path).read_bytes()
    ext = Path(path).suffix.lower() or (".png" if kind == "image" else ".mp4")
    asset, _ = await create_from_bytes(
        db,
        user_id=scope.user_id,
        project_id=scope.project_id,
        data=raw,
        filename=f"{kind}{ext}",
        asset_type="image" if kind == "image" else "video",
        name=f"{kind}-{row.generation_id}",
    )
    row.output_asset_id = asset.id
    row.result_path = asset.storage_key
    row.result_url = asset_file_url(asset.id, scope.project_id)
