"""Director 请求级 User + Project 作用域。禁止全局变量，禁止信任客户端 user_id。"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_from_header_or_query
from .database import get_db
from .models import Project, User


@dataclass(frozen=True)
class DirectorScope:
    user: User
    project: Project

    @property
    def user_id(self) -> str:
        return self.user.id

    @property
    def project_id(self) -> str:
        return self.project.id


async def resolve_director_scope(db: AsyncSession, user: User, project_id: str | None) -> DirectorScope:
    pid = (project_id or "").strip()
    if not pid:
        raise HTTPException(400, "需要 project_id")
    result = await db.execute(select(Project).where(Project.id == pid, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(404, "项目不存在")
    return DirectorScope(user=user, project=project)


async def get_director_scope(
    project_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DirectorScope:
    return await resolve_director_scope(db, user, project_id)


async def get_director_scope_file(
    project_id: str | None = Query(None),
    user: User = Depends(get_current_user_from_header_or_query),
    db: AsyncSession = Depends(get_db),
) -> DirectorScope:
    return await resolve_director_scope(db, user, project_id)
