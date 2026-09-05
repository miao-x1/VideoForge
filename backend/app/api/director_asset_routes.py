"""Director Asset API。User + Project 隔离，storage_key 不是授权凭证。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..assets.dataurl import count_data_urls, replace_data_urls
from ..assets.service import (
    asset_file_url,
    create_from_bytes,
    dump_asset,
    get_owned_asset,
    list_owned_assets,
    mark_deleted,
    validate_upload,
)
from ..db.database import get_db
from ..db.ownership import DirectorScope, get_director_scope, get_director_scope_file
from ..storage.local import storage

router = APIRouter(prefix="/api/director/assets", tags=["director-assets"])


@router.post("")
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(""),
    name: str = Form(""),
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    data = await file.read()
    validate_upload(file.filename or "", data, file.content_type)
    row, reused = await create_from_bytes(
        db,
        user_id=scope.user_id,
        project_id=scope.project_id,
        data=data,
        filename=file.filename or "file",
        asset_type=asset_type or None,
        name=name or None,
        content_type=file.content_type,
    )
    await db.commit()
    return {**dump_asset(row), "deduplicated": reused}


@router.get("")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    rows = await list_owned_assets(db, user_id=scope.user_id, project_id=scope.project_id)
    return {"assets": [dump_asset(r) for r in rows]}


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    row = await get_owned_asset(db, asset_id=asset_id, user_id=scope.user_id, project_id=scope.project_id)
    if row is None:
        raise HTTPException(404, "素材不存在")
    return dump_asset(row)


@router.get("/{asset_id}/file")
async def read_asset_file(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope_file),
):
    row = await get_owned_asset(db, asset_id=asset_id, user_id=scope.user_id, project_id=scope.project_id)
    if row is None or not row.storage_key:
        raise HTTPException(404, "素材不存在")
    try:
        path = storage.get_path(row.storage_key)
    except ValueError as exc:
        raise HTTPException(400, "非法 storage_key") from exc
    if not path.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(
        path,
        filename=row.file_name or path.name,
        media_type=row.mime_type,
        content_disposition_type="inline",
    )


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    row = await get_owned_asset(db, asset_id=asset_id, user_id=scope.user_id, project_id=scope.project_id)
    if row is None:
        raise HTTPException(404, "素材不存在")
    await mark_deleted(db, row)
    await db.commit()
    return {"deleted": True, "id": asset_id, "status": "deleted"}


async def persist_without_data_urls(payload: dict, db: AsyncSession, scope: DirectorScope) -> dict:
    """转换或拒绝 Data URL，避免写入业务 JSON。"""
    if count_data_urls(payload) == 0:
        return payload
    pending: list[tuple[str, bytes, str, str]] = []

    def collect(raw: bytes, mime: str, ext: str) -> str:
        token = f"__vf_asset_{len(pending)}__"
        pending.append((token, raw, mime, ext))
        return token

    walked = replace_data_urls(payload, collect)
    tokens: dict[str, str] = {}
    for token, raw, mime, ext in pending:
        row, _ = await create_from_bytes(
            db,
            user_id=scope.user_id,
            project_id=scope.project_id,
            data=raw,
            filename=f"inline{ext}",
            asset_type="image" if mime.startswith("image/") else None,
        )
        tokens[token] = asset_file_url(row.id, scope.project_id)
    from ..assets.dataurl import apply_asset_tokens

    converted = apply_asset_tokens(walked, tokens)
    if count_data_urls(converted):
        raise HTTPException(400, "拒绝持久化 Data URL，请先上传为 Asset")
    return converted
