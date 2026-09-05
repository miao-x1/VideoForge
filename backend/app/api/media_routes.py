"""受控文件访问。生产禁止匿名读取 /storage；永不返回数据库文件。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.jwt_handler import verify_token
from ..core.security_guard import normalize_app_env
from ..core.config import settings
from ..db.database import get_db
from ..db.models import Asset
from ..storage.local import storage

router = APIRouter(tags=["media"])

_BLOCKED_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def _require_media_auth(request: Request, access_token: str | None) -> None:
    env = normalize_app_env(settings.app_env)
    if env != "production":
        return
    token = access_token or ""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = token or auth.split(" ", 1)[1].strip()
    if not token or verify_token(token) is None:
        raise HTTPException(401, "未授权访问文件")


def resolve_storage_file(rel: str) -> Path:
    if not rel or rel.startswith("/") or "\\" in rel.replace("/", ""):
        raise HTTPException(400, "非法路径")
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts:
        raise HTTPException(400, "非法路径")
    if raw.suffix.lower() in _BLOCKED_SUFFIXES:
        raise HTTPException(403, "禁止访问数据库文件")
    root = storage.root()
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(400, "非法路径") from exc
    if not target.is_file():
        raise HTTPException(404, "文件不存在")
    return target


@router.get("/storage/{path:path}")
async def read_storage_file(
    path: str,
    request: Request,
    access_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    rel = (path or "").replace("\\", "/").lstrip("/")
    if rel.startswith("projects/"):
        token = access_token or ""
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = token or auth.split(" ", 1)[1].strip()
        payload = verify_token(token) if token else None
        user_id = (payload or {}).get("sub") if payload else None
        if not user_id:
            raise HTTPException(401, "未授权访问文件")
        result = await db.execute(
            select(Asset).where(
                Asset.storage_key == rel,
                Asset.user_id == user_id,
                Asset.deleted_at.is_(None),
                Asset.status != "deleted",
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "文件不存在")
        target = resolve_storage_file(rel)
        return FileResponse(
            target,
            filename=row.file_name or target.name,
            content_disposition_type="inline",
        )
    _require_media_auth(request, access_token)
    target = resolve_storage_file(path)
    return FileResponse(target, content_disposition_type="inline")
