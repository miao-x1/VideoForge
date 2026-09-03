"""ORM 模型：User / Project / Asset / TaskRecord / TaskLog。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, ForeignKey, JSON, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> float:
    return datetime.now(timezone.utc).timestamp()


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)

    tasks: Mapped[list["TaskRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_series: Mapped[bool] = mapped_column(Boolean, default=False)
    memory_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)  # Project Memory:创作设定/主体/场景/风格/历史视频/修改记录
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["TaskRecord"]] = relationship(back_populates="project")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project")


class Asset(Base):
    """通用素材:人物/场景/物品/动物/建筑/风格/参考图/参考视频/声音/音乐。"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    asset_type: Mapped[str] = mapped_column(String(32), index=True)  # person/scene/object/style/reference/voice/music
    description: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # image/video/audio
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="assets")
    project: Mapped["Project | None"] = relationship(back_populates="assets")


class TaskRecord(Base):
    __tablename__ = "task_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(12), unique=True, index=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), ForeignKey("projects.id"), nullable=True, index=True)
    user_input: Mapped[str] = mapped_column(Text)
    duration: Mapped[int] = mapped_column(default=30)
    style: Mapped[str] = mapped_column(String(64), default="")
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    compliance_enabled: Mapped[bool] = mapped_column(default=True)
    spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="quick")
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(4), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="tasks")
    project: Mapped["Project | None"] = relationship(back_populates="tasks")
    logs: Mapped[list["TaskLog"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(12), ForeignKey("task_records.task_id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[float] = mapped_column(Float, default=_utcnow)

    task: Mapped["TaskRecord"] = relationship(back_populates="logs")
