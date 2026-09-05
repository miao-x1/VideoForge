"""3D 导演台角色生产接口。不接 Agent。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..core.config import STORAGE_ROOT
from ..db.database import get_db
from ..db.models import User
from ..db.ownership import DirectorScope, get_director_scope
from ..director.character_pipeline import capability, create_task, get_task

router = APIRouter(prefix="/api/director/characters", tags=["director-characters"])


@router.get("/capability")
async def get_capability(_user: User = Depends(get_current_user)) -> dict:
    return capability()


@router.post("/tasks")
async def create_character_task(
    kind: str = Form(...),
    prompt: str = Form(""),
    name: str = Form(""),
    mode: str = Form("single"),
    images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    saved = []
    upload_dir = STORAGE_ROOT / "director" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    for file in images or []:
        dest = upload_dir / f"{file.filename or 'image'}"
        data = await file.read()
        dest.write_bytes(data)
        saved.append({"name": file.filename, "size": len(data), "path": str(dest)})
    return await create_task(
        db,
        kind=kind,
        payload={"prompt": prompt, "name": name, "mode": mode, "images": saved},
        user_id=scope.user_id,
        project_id=scope.project_id,
    )


@router.get("/tasks/{task_id}")
async def read_character_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DirectorScope = Depends(get_director_scope),
) -> dict:
    task = await get_task(db, task_id, user_id=scope.user_id, project_id=scope.project_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task
