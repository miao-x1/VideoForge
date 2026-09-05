"""角色生产任务：校验输入并记录真实状态。

没有 Image-to-3D Provider 时必须失败，不得返回假角色。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import DirectorCharacterTask

NOT_WIRED = "Image-to-3D 未接入。当前没有可用的图生 3D 服务，系统不会假装生成成功。"


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def capability() -> dict:
    wired = settings.image_to_3d_provider not in ("", "none")
    return {
        "image_to_3d": wired,
        "provider": settings.image_to_3d_provider,
        "message": "Image-to-3D 已配置。" if wired else NOT_WIRED,
    }


def _dump(row: DirectorCharacterTask) -> dict:
    return {
        "task_id": row.task_id,
        "kind": row.kind,
        "status": row.status,
        "progress": row.progress,
        "error": row.error,
        "result": row.result_json,
        "stages": row.stages_json or [],
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def create_task(
    db: AsyncSession,
    *,
    kind: str,
    payload: dict,
    user_id: str,
    project_id: str,
) -> dict:
    now = _now()
    if kind == "ai_generate":
        prompt = str(payload.get("prompt") or "").strip()
        stages = [
            {"name": "validate_prompt", "status": "succeeded" if prompt else "failed", "error": None if prompt else "描述不能为空"},
            {"name": "image_to_3d", "status": "failed", "error": NOT_WIRED},
            {"name": "auto_rig", "status": "skipped", "error": None},
        ]
        error = None if prompt else "描述不能为空"
        if prompt:
            error = NOT_WIRED
        status = "failed"
    elif kind == "image_to_3d":
        images = payload.get("images") or []
        mode = payload.get("mode") or "single"
        valid = len(images) >= 1 and (mode != "single" or len(images) >= 1)
        stages = [
            {"name": "validate_input", "status": "succeeded" if valid else "failed", "error": None if valid else "至少需要一张图片"},
            {"name": "image_to_3d", "status": "failed" if valid else "skipped", "error": NOT_WIRED if valid else None},
            {"name": "auto_rig", "status": "skipped", "error": None},
        ]
        error = NOT_WIRED if valid else "至少需要一张图片"
        status = "failed"
    else:
        stages = [{"name": "validate_input", "status": "failed", "error": f"未知任务类型 {kind}"}]
        error = f"未知任务类型 {kind}"
        status = "failed"

    row = DirectorCharacterTask(
        task_id=_new_id(),
        user_id=user_id,
        project_id=project_id,
        kind=kind,
        status=status,
        progress=0,
        error=error,
        result_json=None,
        stages_json=stages,
        payload_json={**payload, "images": [img.get("name") for img in (payload.get("images") or []) if isinstance(img, dict)]},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _dump(row)


async def get_task(
    db: AsyncSession,
    task_id: str,
    *,
    user_id: str,
    project_id: str,
) -> dict | None:
    result = await db.execute(
        select(DirectorCharacterTask).where(
            DirectorCharacterTask.task_id == task_id,
            DirectorCharacterTask.user_id == user_id,
            DirectorCharacterTask.project_id == project_id,
        )
    )
    row = result.scalar_one_or_none()
    return _dump(row) if row else None
