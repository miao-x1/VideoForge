"""Baseline: current VideoForge SQLite schema snapshot.

Revision ID: 001_baseline
Revises:
Create Date: 2026-09-05

Wave 1 只建立版本控制。本 revision 描述检查时的真实库结构，
不新增业务列/表/索引，也不回填 ORM 里尚未落到现网的索引与 FK。

现有数据库必须 stamp，禁止对本 revision 执行 upgrade
（upgrade 会 CREATE 已存在的表）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

revision: str = "001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BUSINESS_TABLES = (
    "users",
    "projects",
    "assets",
    "task_records",
    "verification_codes",
    "task_logs",
    "director_characters",
    "director_scenes",
    "director_poses",
    "director_custom_animations",
    "director_library_meta",
    "director_agent_logs",
    "director_generations",
    "director_character_tasks",
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa_inspect(bind).get_table_names())
    if existing.intersection(_BUSINESS_TABLES):
        raise RuntimeError(
            "Refusing baseline upgrade: business tables already exist. "
            "Stamp an existing database with: alembic stamp 001_baseline"
        )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=12), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(length=20), server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=12), nullable=False),
        sa.Column("user_id", sa.String(length=12), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cover_image", sa.Text()),
        sa.Column("is_series", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("memory_json", sa.JSON()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=12), nullable=False),
        sa.Column("user_id", sa.String(length=12), nullable=False),
        sa.Column("project_id", sa.String(length=12)),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text()),
        sa.Column("media_type", sa.String(length=16)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_user_id", "assets", ["user_id"], unique=False)
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"], unique=False)
    op.create_index("ix_assets_project_id", "assets", ["project_id"], unique=False)

    op.create_table(
        "verification_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_codes_target", "verification_codes", ["target"], unique=False)
    op.create_index("ix_verification_codes_purpose", "verification_codes", ["purpose"], unique=False)

    op.create_table(
        "task_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=12), nullable=False),
        sa.Column("user_id", sa.String(length=12), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("style", sa.String(length=64), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("compliance_enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("video_path", sa.Text()),
        sa.Column("quality_grade", sa.String(length=4)),
        sa.Column("state_json", sa.JSON()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("spec_json", sa.JSON()),
        sa.Column("mode", sa.String(length=16), server_default="quick"),
        sa.Column("project_id", sa.String(length=32)),
        sa.Column("model_used", sa.String(length=64)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_records_task_id", "task_records", ["task_id"], unique=True)
    op.create_index("ix_task_records_user_id", "task_records", ["user_id"], unique=False)

    op.create_table(
        "task_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task_records.task_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_logs_task_id", "task_logs", ["task_id"], unique=False)

    op.create_table(
        "director_characters",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_director_characters_source_type",
        "director_characters",
        ["source_type"],
        unique=False,
    )

    op.create_table(
        "director_scenes",
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("scene_name", sa.String(length=128), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("scene_id"),
    )

    op.create_table(
        "director_poses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("character_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_director_poses_character_id", "director_poses", ["character_id"], unique=False)

    op.create_table(
        "director_custom_animations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("character_id", sa.String(length=64)),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_director_custom_animations_character_id",
        "director_custom_animations",
        ["character_id"],
        unique=False,
    )

    op.create_table(
        "director_library_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("favorites_json", sa.JSON()),
        sa.Column("recent_ids_json", sa.JSON()),
        sa.Column("current_scene_id", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "director_agent_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.String(length=32), nullable=False),
        sa.Column("message_id", sa.String(length=32), nullable=False),
        sa.Column("agent_run_id", sa.String(length=32), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("context_json", sa.JSON()),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("tool_arguments", sa.JSON()),
        sa.Column("tool_result", sa.JSON()),
        sa.Column("execution_status", sa.String(length=24), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_director_agent_logs_conversation_id",
        "director_agent_logs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_director_agent_logs_message_id",
        "director_agent_logs",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_director_agent_logs_agent_run_id",
        "director_agent_logs",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_director_agent_logs_tool_name",
        "director_agent_logs",
        ["tool_name"],
        unique=False,
    )

    op.create_table(
        "director_generations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("generation_id", sa.String(length=16), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("scene_id", sa.String(length=64), nullable=False),
        sa.Column("shot_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("parameters_json", sa.JSON()),
        sa.Column("result_path", sa.Text()),
        sa.Column("result_url", sa.Text()),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_director_generations_generation_id",
        "director_generations",
        ["generation_id"],
        unique=True,
    )
    op.create_index(
        "ix_director_generations_project_id",
        "director_generations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_director_generations_scene_id",
        "director_generations",
        ["scene_id"],
        unique=False,
    )
    op.create_index(
        "ix_director_generations_shot_id",
        "director_generations",
        ["shot_id"],
        unique=False,
    )

    op.create_table(
        "director_character_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("result_json", sa.JSON()),
        sa.Column("stages_json", sa.JSON()),
        sa.Column("payload_json", sa.JSON()),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_director_character_tasks_task_id",
        "director_character_tasks",
        ["task_id"],
        unique=True,
    )
    op.create_index(
        "ix_director_character_tasks_kind",
        "director_character_tasks",
        ["kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("director_character_tasks")
    op.drop_table("director_generations")
    op.drop_table("director_agent_logs")
    op.drop_table("director_library_meta")
    op.drop_table("director_custom_animations")
    op.drop_table("director_poses")
    op.drop_table("director_scenes")
    op.drop_table("director_characters")
    op.drop_table("task_logs")
    op.drop_table("task_records")
    op.drop_table("verification_codes")
    op.drop_table("assets")
    op.drop_table("projects")
    op.drop_table("users")
