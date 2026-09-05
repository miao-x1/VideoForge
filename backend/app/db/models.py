"""ORM 模型：User / Project / Asset / TaskRecord / TaskLog。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, ForeignKey, JSON, Integer, Boolean, Index
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
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
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
    """统一 Asset 元数据。文件在本地 storage，库内不存 Data URL。"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ready", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[float | None] = mapped_column(Float, nullable=True)

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


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(16), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[float] = mapped_column(Float)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(12), ForeignKey("task_records.task_id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[float] = mapped_column(Float, default=_utcnow)

    task: Mapped["TaskRecord"] = relationship(back_populates="logs")


class DirectorCharacter(Base):
    """导演台角色资产（与前端 CharacterAsset 对齐）。"""

    __tablename__ = "director_characters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    template_id: Mapped[str] = mapped_column(String(64), default="")
    source_type: Mapped[str] = mapped_column(String(32), default="official", index=True)
    primary_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    reference_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    thumbnail_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class DirectorScene(Base):
    """导演台分镜。"""

    __tablename__ = "director_scenes"

    scene_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    scene_name: Mapped[str] = mapped_column(String(128), default="")
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    background_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    reference_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    composition_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    current_generation_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class DirectorPose(Base):
    """已保存的角色姿势。"""

    __tablename__ = "director_poses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    character_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    name: Mapped[str] = mapped_column(String(128), default="")
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class DirectorCustomAnimation(Base):
    """自定义骨骼动画。"""

    __tablename__ = "director_custom_animations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    character_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class DirectorLibraryMeta(Base):
    """角色库收藏 / 最近使用 / 当前分镜（单行）。"""

    __tablename__ = "director_library_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    favorites_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recent_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_scene_id: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class DirectorAgentLog(Base):
    """导演台 Agent 执行日志。"""

    __tablename__ = "director_agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String(32), index=True)
    message_id: Mapped[str] = mapped_column(String(32), index=True)
    agent_run_id: Mapped[str] = mapped_column(String(32), index=True)
    user_input: Mapped[str] = mapped_column(Text, default="")
    context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_name: Mapped[str] = mapped_column(String(64), default="", index=True)
    tool_arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(24), default="planned")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)


class DirectorGeneration(Base):
    """导演台图片/视频生成历史。结果绑定 scene/shot。"""

    __tablename__ = "director_generations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    generation_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    scene_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    shot_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    kind: Mapped[str] = mapped_column(String(16), default="image")
    title: Mapped[str] = mapped_column(String(128), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    parameters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_asset_id: Mapped[str | None] = mapped_column(String(12), nullable=True)
    parent_generation_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)


class DirectorCharacterTask(Base):
    """3D 导演台角色生产任务（Image-to-3D / AI 生成）。不是视频任务。"""

    __tablename__ = "director_character_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stages_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class UserWallet(Base):
    """平台余额，单位分。"""

    __tablename__ = "user_wallets"

    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), primary_key=True)
    balance_fen: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class WalletLedger(Base):
    """钱包流水：充值 / 扣费 / 退回。"""

    __tablename__ = "wallet_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    delta_fen: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(String(255), default="")
    ref_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)


class UserApiCredential(Base):
    """用户自带上游 Key。密文入库，接口只回 last4。"""

    __tablename__ = "user_api_credentials"
    __table_args__ = (
        Index("ix_user_api_credentials_user_provider", "user_id", "provider", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    encrypted_key: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(String(255), default="")
    last4: Mapped[str] = mapped_column(String(8), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)


class UserBillingPref(Base):
    """出片走平台模型还是自带 Key。"""

    __tablename__ = "user_billing_prefs"

    user_id: Mapped[str] = mapped_column(String(12), ForeignKey("users.id"), primary_key=True)
    video_source: Mapped[str] = mapped_column(String(16), default="platform")
    video_provider: Mapped[str] = mapped_column(String(32), default="minimax")
    video_model: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[float] = mapped_column(Float, default=_utcnow, onupdate=_utcnow)
