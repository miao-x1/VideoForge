"""Asset 创建 / 去重 / 引用保护。Hash 去重不跨 user/project。"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import (
    Asset,
    DirectorCharacter,
    DirectorCharacterTask,
    DirectorGeneration,
    DirectorScene,
    TaskRecord,
)
from ..storage.local import storage
from .types import media_kind, mime_for_filename, normalize_asset_type, safe_extension

STATUSES = ("pending", "processing", "ready", "failed", "deleted")


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def max_upload_bytes() -> int:
    return int(settings.upload_max_size_mb) * 1024 * 1024


def validate_upload(filename: str, data: bytes, content_type: str | None = None) -> str:
    ext = safe_extension(filename)
    if not ext:
        raise HTTPException(400, "不支持的文件类型")
    if len(data) > max_upload_bytes():
        raise HTTPException(413, f"文件过大,上限 {settings.upload_max_size_mb}MB")
    if not data:
        raise HTTPException(400, "文件为空")
    return ext


def storage_key_for(project_id: str, asset_id: str, ext: str) -> str:
    return f"projects/{project_id}/assets/{asset_id}/original{ext}"


def asset_file_url(asset_id: str, project_id: str) -> str:
    return f"/api/director/assets/{asset_id}/file?project_id={project_id}"


def dump_asset(row: Asset) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "project_id": row.project_id,
        "name": row.name,
        "asset_type": row.asset_type,
        "media_type": row.media_type,
        "file_name": row.file_name,
        "storage_key": row.storage_key,
        "mime_type": row.mime_type,
        "file_size": row.file_size,
        "file_hash": row.file_hash,
        "width": row.width,
        "height": row.height,
        "duration": row.duration,
        "thumbnail_asset_id": row.thumbnail_asset_id,
        "status": row.status,
        "url": asset_file_url(row.id, row.project_id) if row.project_id and row.status == "ready" else None,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "deleted_at": row.deleted_at,
    }


async def find_duplicate(db: AsyncSession, *, user_id: str, project_id: str, file_hash: str) -> Asset | None:
    result = await db.execute(
        select(Asset).where(
            Asset.user_id == user_id,
            Asset.project_id == project_id,
            Asset.file_hash == file_hash,
            Asset.status != "deleted",
            Asset.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_from_bytes(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: str,
    data: bytes,
    filename: str,
    asset_type: str | None = None,
    name: str | None = None,
    content_type: str | None = None,
) -> tuple[Asset, bool]:
    ext = validate_upload(filename, data, content_type)
    digest = sha256_bytes(data)
    existing = await find_duplicate(db, user_id=user_id, project_id=project_id, file_hash=digest)
    if existing:
        return existing, True

    kind = normalize_asset_type(asset_type, filename=filename)
    row = Asset(
        user_id=user_id,
        project_id=project_id,
        name=(name or filename or "asset")[:128],
        asset_type=kind,
        description="",
        file_name=(filename or f"file{ext}")[:255],
        storage_key=None,
        mime_type=mime_for_filename(filename or f"file{ext}"),
        media_type=media_kind(kind),
        file_size=len(data),
        file_hash=digest,
        status="pending",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(row)
    await db.flush()
    key = storage_key_for(project_id, row.id, ext)
    try:
        storage.save(key, data)
    except Exception:
        row.status = "failed"
        row.updated_at = _now()
        await db.flush()
        raise
    row.storage_key = key
    row.file_path = key
    row.status = "ready"
    row.updated_at = _now()
    await db.flush()
    return row, False


async def get_owned_asset(db: AsyncSession, *, asset_id: str, user_id: str, project_id: str) -> Asset | None:
    result = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == user_id,
            Asset.project_id == project_id,
            Asset.deleted_at.is_(None),
            Asset.status != "deleted",
        )
    )
    return result.scalar_one_or_none()


async def list_owned_assets(db: AsyncSession, *, user_id: str, project_id: str) -> list[Asset]:
    result = await db.execute(
        select(Asset)
        .where(
            Asset.user_id == user_id,
            Asset.project_id == project_id,
            Asset.deleted_at.is_(None),
            Asset.status != "deleted",
        )
        .order_by(Asset.created_at.desc())
    )
    return list(result.scalars().all())


def _json_mentions(payload, asset_id: str) -> bool:
    if payload is None:
        return False
    text = str(payload)
    return asset_id in text


async def referenced_by(db: AsyncSession, asset_id: str, user_id: str, project_id: str) -> list[str]:
    refs: list[str] = []
    thumbs = await db.execute(
        select(Asset.id).where(
            Asset.thumbnail_asset_id == asset_id,
            Asset.id != asset_id,
            Asset.deleted_at.is_(None),
        )
    )
    if thumbs.scalars().first():
        refs.append("asset.thumbnail")

    chars = (await db.execute(select(DirectorCharacter).where(
        DirectorCharacter.user_id == user_id, DirectorCharacter.project_id == project_id
    ))).scalars().all()
    for row in chars:
        if asset_id in {
            row.primary_asset_id,
            row.reference_asset_id,
            row.thumbnail_asset_id,
        } or _json_mentions(row.data_json, asset_id):
            refs.append(f"character:{row.id}")

    scenes = (await db.execute(select(DirectorScene).where(
        DirectorScene.user_id == user_id, DirectorScene.project_id == project_id
    ))).scalars().all()
    for row in scenes:
        if asset_id in {
            row.background_asset_id,
            row.reference_asset_id,
            row.composition_asset_id,
        } or _json_mentions(row.data_json, asset_id):
            refs.append(f"scene:{row.scene_id}")

    gens = (await db.execute(select(DirectorGeneration).where(
        DirectorGeneration.user_id == user_id, DirectorGeneration.project_id == project_id
    ))).scalars().all()
    for row in gens:
        if row.output_asset_id == asset_id or _json_mentions(row.parameters_json, asset_id) or _json_mentions(row.input_snapshot_json, asset_id):
            refs.append(f"generation:{row.generation_id}")

    tasks = (await db.execute(select(DirectorCharacterTask).where(
        DirectorCharacterTask.user_id == user_id, DirectorCharacterTask.project_id == project_id
    ))).scalars().all()
    for row in tasks:
        if _json_mentions(row.payload_json, asset_id) or _json_mentions(row.result_json, asset_id):
            refs.append(f"character_task:{row.task_id}")

    records = (await db.execute(select(TaskRecord).where(
        TaskRecord.user_id == user_id,
        or_(TaskRecord.project_id == project_id, TaskRecord.project_id.is_(None)),
    ))).scalars().all()
    for row in records:
        if _json_mentions(row.spec_json, asset_id) or _json_mentions(row.state_json, asset_id):
            refs.append(f"task:{row.task_id}")
    return refs


async def mark_deleted(db: AsyncSession, row: Asset) -> Asset:
    refs = await referenced_by(db, row.id, row.user_id, row.project_id or "")
    if refs:
        raise HTTPException(409, f"素材仍被引用: {', '.join(refs[:8])}")
    row.status = "deleted"
    row.deleted_at = _now()
    row.updated_at = _now()
    await db.flush()
    return row


def find_duplicate_sync(session: Session, *, user_id: str, project_id: str, file_hash: str) -> Asset | None:
    return session.scalar(
        select(Asset).where(
            Asset.user_id == user_id,
            Asset.project_id == project_id,
            Asset.file_hash == file_hash,
            Asset.status != "deleted",
            Asset.deleted_at.is_(None),
        )
    )
