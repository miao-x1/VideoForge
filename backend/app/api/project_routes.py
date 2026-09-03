"""Project / Asset / History API 路由。

用户系统:
- 项目管理(创建/列表/详情/删除)
- 素材库(添加/列表/删除/按类型过滤)
- 生成历史(列表/详情/按项目过滤)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from ..auth.dependencies import get_current_user
from ..core.logging import logger
from ..db.database import get_session
from ..db.models import User, Project, Asset, TaskRecord

router = APIRouter(prefix="/api", tags=["projects"])


# ======================== Pydantic Schemas ========================

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    is_series: bool = False


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    is_series: Optional[bool] = None


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    asset_type: str = Field(..., description="person/scene/object/style/reference/voice/music")
    description: str = ""
    file_path: Optional[str] = None
    media_type: Optional[str] = None
    metadata: Optional[dict] = None


# ======================== Project Endpoints ========================

@router.post("/projects")
async def create_project(
    body: ProjectCreate,
    user: User = Depends(get_current_user),
) -> dict:
    """创建项目。"""
    with get_session() as session:
        project = Project(
            user_id=user.id,
            title=body.title,
            description=body.description,
            is_series=body.is_series,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        logger.info("项目创建: %s (%s) user=%s", project.id, project.title, user.id)
        return {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "is_series": project.is_series,
            "created_at": project.created_at,
        }


@router.get("/projects")
async def list_projects(
    user: User = Depends(get_current_user),
) -> dict:
    """列出用户的所有项目。"""
    with get_session() as session:
        projects = session.scalars(
            select(Project)
            .where(Project.user_id == user.id)
            .order_by(desc(Project.updated_at))
        ).all()
        result = []
        for p in projects:
            task_count = session.query(TaskRecord).filter(
                TaskRecord.project_id == p.id
            ).count()
            asset_count = session.query(Asset).filter(
                Asset.project_id == p.id
            ).count()
            result.append({
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "cover_image": p.cover_image,
                "is_series": p.is_series,
                "task_count": task_count,
                "asset_count": asset_count,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
        return {"projects": result}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """获取项目详情。"""
    with get_session() as session:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user.id,
            )
        )
        if not project:
            raise HTTPException(404, "项目不存在")
        tasks = session.scalars(
            select(TaskRecord)
            .where(TaskRecord.project_id == project_id)
            .order_by(desc(TaskRecord.created_at))
        ).all()
        assets = session.scalars(
            select(Asset)
            .where(Asset.project_id == project_id)
            .order_by(desc(Asset.created_at))
        ).all()
        return {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "cover_image": project.cover_image,
            "is_series": project.is_series,
            "memory": project.memory_json or {},
            "created_at": project.created_at,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "user_input": t.user_input[:100],
                    "status": t.status,
                    "video_path": t.video_path,
                    "mode": t.mode,
                    "model_used": t.model_used,
                    "created_at": t.created_at,
                }
                for t in tasks
            ],
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "asset_type": a.asset_type,
                    "file_path": a.file_path,
                    "media_type": a.media_type,
                    "created_at": a.created_at,
                }
                for a in assets
            ],
        }


@router.get("/projects/{project_id}/memory")
async def get_project_memory(
    project_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """获取项目记忆:创作设定/主体/场景/风格/Prompt 摘要/历史视频/用户修改记录。"""
    with get_session() as session:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user.id,
            )
        )
        if not project:
            raise HTTPException(404, "项目不存在")
        memory = project.memory_json or {}
        return {
            "project_id": project_id,
            "memory": memory,
            "summary": {
                "subject_count": len(memory.get("subjects", [])),
                "scene_count": len(memory.get("scenes", [])),
                "style_count": len(memory.get("styles", [])),
                "video_count": len(memory.get("videos", [])),
                "modification_count": len(memory.get("modifications", [])),
            },
        }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """删除项目。"""
    with get_session() as session:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user.id,
            )
        )
        if not project:
            raise HTTPException(404, "项目不存在")
        session.delete(project)
        session.commit()
        return {"deleted": True, "id": project_id}


# ======================== Asset Endpoints ========================

@router.post("/projects/{project_id}/assets")
async def add_asset_to_project(
    project_id: str,
    body: AssetCreate,
    user: User = Depends(get_current_user),
) -> dict:
    """向项目添加素材。"""
    with get_session() as session:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user.id,
            )
        )
        if not project:
            raise HTTPException(404, "项目不存在")
        asset = Asset(
            user_id=user.id,
            project_id=project_id,
            name=body.name,
            asset_type=body.asset_type,
            description=body.description,
            file_path=body.file_path,
            media_type=body.media_type,
            metadata_json=body.metadata,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return {
            "id": asset.id,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "project_id": asset.project_id,
            "created_at": asset.created_at,
        }


@router.get("/assets")
async def list_assets(
    asset_type: Optional[str] = Query(None, description="按类型过滤:person/scene/object/style/reference/voice/music"),
    project_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
) -> dict:
    """列出用户素材库。"""
    with get_session() as session:
        query = select(Asset).where(Asset.user_id == user.id)
        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
        if project_id:
            query = query.where(Asset.project_id == project_id)
        query = query.order_by(desc(Asset.created_at))
        assets = session.scalars(query).all()
        return {
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "asset_type": a.asset_type,
                    "description": a.description,
                    "file_path": a.file_path,
                    "media_type": a.media_type,
                    "project_id": a.project_id,
                    "metadata": a.metadata_json,
                    "created_at": a.created_at,
                }
                for a in assets
            ]
        }


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """删除素材。"""
    with get_session() as session:
        asset = session.scalar(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.user_id == user.id,
            )
        )
        if not asset:
            raise HTTPException(404, "素材不存在")
        session.delete(asset)
        session.commit()
        return {"deleted": True, "id": asset_id}


# ======================== Generation History ========================

@router.get("/history")
async def get_generation_history(
    project_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
) -> dict:
    """获取用户生成历史。"""
    with get_session() as session:
        query = select(TaskRecord).where(TaskRecord.user_id == user.id)
        if project_id:
            query = query.where(TaskRecord.project_id == project_id)
        query = query.order_by(desc(TaskRecord.created_at)).limit(limit).offset(offset)
        tasks = session.scalars(query).all()
        return {
            "history": [
                {
                    "task_id": t.task_id,
                    "user_input": t.user_input[:200],
                    "duration": t.duration,
                    "style": t.style,
                    "aspect_ratio": t.aspect_ratio,
                    "mode": t.mode,
                    "status": t.status,
                    "video_path": t.video_path,
                    "quality_grade": t.quality_grade,
                    "model_used": t.model_used,
                    "project_id": t.project_id,
                    "created_at": t.created_at,
                }
                for t in tasks
            ],
            "total": len(tasks),
        }


@router.get("/history/{task_id}")
async def get_generation_detail(
    task_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """获取生成详情(含完整状态)。"""
    with get_session() as session:
        task = session.scalar(
            select(TaskRecord).where(
                TaskRecord.task_id == task_id,
                TaskRecord.user_id == user.id,
            )
        )
        if not task:
            raise HTTPException(404, "记录不存在")
        return {
            "task_id": task.task_id,
            "user_input": task.user_input,
            "duration": task.duration,
            "style": task.style,
            "aspect_ratio": task.aspect_ratio,
            "mode": task.mode,
            "status": task.status,
            "video_path": task.video_path,
            "quality_grade": task.quality_grade,
            "model_used": task.model_used,
            "project_id": task.project_id,
            "spec": task.spec_json,
            "state": task.state_json,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
