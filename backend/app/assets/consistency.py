"""Asset / 文件一致性检查。默认只报告，不删除。"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Asset
from ..storage.local import storage
from .dataurl import count_data_urls


_SKIP_NAMES = {".gitkeep"}
_DB_SUFFIX = {".db", ".sqlite", ".sqlite3"}


def check_consistency(session: Session) -> dict:
    assets = list(session.scalars(select(Asset)).all())
    ready = [a for a in assets if a.status == "ready" and a.deleted_at is None]
    missing: list[str] = []
    invalid: list[str] = []
    keys: set[str] = set()
    for row in assets:
        if row.storage_key:
            try:
                storage.resolve(row.storage_key)
                keys.add(row.storage_key.replace("\\", "/"))
            except ValueError:
                invalid.append(row.id)
                continue
        if row.status == "ready" and row.deleted_at is None:
            if not row.storage_key or not storage.exists(row.storage_key):
                missing.append(row.id)
            if row.file_size is not None and row.storage_key and storage.exists(row.storage_key):
                actual = storage.get_path(row.storage_key).stat().st_size
                if actual != row.file_size:
                    invalid.append(row.id)
            if row.mime_type and "/" not in row.mime_type:
                invalid.append(row.id)

    root = storage.root()
    files = [p for p in root.rglob("*") if p.is_file() and p.name not in _SKIP_NAMES]
    orphan: list[str] = []
    unknown: list[str] = []
    recognized = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in _DB_SUFFIX:
            unknown.append(rel)
            continue
        if rel in keys:
            recognized += 1
            continue
        if rel.startswith("projects/") and "/assets/" in rel and not rel.endswith(".tmp"):
            orphan.append(rel)
        else:
            unknown.append(rel)

    return {
        "total_assets": len(assets),
        "ready": len(ready),
        "missing_files": missing,
        "orphan_files": orphan,
        "invalid_metadata": sorted(set(invalid)),
        "storage_files": len(files),
        "recognized": recognized,
        "unknown": unknown,
        "missing_count": len(missing),
        "orphan_count": len(orphan),
        "unknown_count": len(unknown),
    }


def scan_data_urls(session: Session) -> dict:
    from ..db.models import DirectorCharacter, DirectorCharacterTask, DirectorGeneration, DirectorScene

    counts = {"characters": 0, "scenes": 0, "generations": 0, "character_tasks": 0}
    remaining = 0
    for row in session.scalars(select(DirectorCharacter)).all():
        n = count_data_urls(row.data_json)
        if n:
            counts["characters"] += 1
            remaining += n
    for row in session.scalars(select(DirectorScene)).all():
        n = count_data_urls(row.data_json)
        if n:
            counts["scenes"] += 1
            remaining += n
    for row in session.scalars(select(DirectorGeneration)).all():
        n = count_data_urls(row.parameters_json)
        if n:
            counts["generations"] += 1
            remaining += n
    for row in session.scalars(select(DirectorCharacterTask)).all():
        n = count_data_urls(row.payload_json) + count_data_urls(row.result_json)
        if n:
            counts["character_tasks"] += 1
            remaining += n
    return {"rows_with_data_url": counts, "legacy_data_urls": remaining, "converted": 0, "remaining": remaining}
