"""Asset metadata + file lifecycle fields.

Revision ID: 003_asset_normalization
Revises: 002_director_ownership
Create Date: 2026-09-05

Does not backfill or delete rows. Existing assets (if any) stay nullable.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.alembic_runtime import add_column_if_missing, create_index_if_missing

revision: str = "003_asset_normalization"
down_revision: Union[str, Sequence[str], None] = "002_director_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("assets", sa.Column("file_name", sa.String(length=255), nullable=True))
    add_column_if_missing("assets", sa.Column("storage_key", sa.Text(), nullable=True))
    add_column_if_missing("assets", sa.Column("mime_type", sa.String(length=128), nullable=True))
    add_column_if_missing("assets", sa.Column("file_size", sa.Integer(), nullable=True))
    add_column_if_missing("assets", sa.Column("file_hash", sa.String(length=64), nullable=True))
    add_column_if_missing("assets", sa.Column("width", sa.Integer(), nullable=True))
    add_column_if_missing("assets", sa.Column("height", sa.Integer(), nullable=True))
    add_column_if_missing("assets", sa.Column("duration", sa.Float(), nullable=True))
    add_column_if_missing("assets", sa.Column("thumbnail_asset_id", sa.String(length=12), nullable=True))
    add_column_if_missing("assets", sa.Column("status", sa.String(length=16), server_default="ready", nullable=True))
    add_column_if_missing("assets", sa.Column("updated_at", sa.Float(), nullable=True))
    add_column_if_missing("assets", sa.Column("deleted_at", sa.Float(), nullable=True))
    create_index_if_missing("ix_assets_file_hash", "assets", ["file_hash"], unique=False)
    create_index_if_missing("ix_assets_status", "assets", ["status"], unique=False)
    create_index_if_missing("ix_assets_storage_key", "assets", ["storage_key"], unique=True)
    create_index_if_missing("ix_assets_user_project_hash", "assets", ["user_id", "project_id", "file_hash"], unique=False)

    add_column_if_missing("director_characters", sa.Column("primary_asset_id", sa.String(length=12), nullable=True))
    add_column_if_missing("director_characters", sa.Column("reference_asset_id", sa.String(length=12), nullable=True))
    add_column_if_missing("director_characters", sa.Column("thumbnail_asset_id", sa.String(length=12), nullable=True))

    add_column_if_missing("director_scenes", sa.Column("background_asset_id", sa.String(length=12), nullable=True))
    add_column_if_missing("director_scenes", sa.Column("reference_asset_id", sa.String(length=12), nullable=True))
    add_column_if_missing("director_scenes", sa.Column("composition_asset_id", sa.String(length=12), nullable=True))

    add_column_if_missing("director_generations", sa.Column("output_asset_id", sa.String(length=12), nullable=True))


def downgrade() -> None:
    op.drop_column("director_generations", "output_asset_id")
    op.drop_column("director_scenes", "composition_asset_id")
    op.drop_column("director_scenes", "reference_asset_id")
    op.drop_column("director_scenes", "background_asset_id")
    op.drop_column("director_characters", "thumbnail_asset_id")
    op.drop_column("director_characters", "reference_asset_id")
    op.drop_column("director_characters", "primary_asset_id")
    op.drop_index("ix_assets_user_project_hash", table_name="assets")
    op.drop_index("ix_assets_storage_key", table_name="assets")
    op.drop_index("ix_assets_status", table_name="assets")
    op.drop_index("ix_assets_file_hash", table_name="assets")
    op.drop_column("assets", "deleted_at")
    op.drop_column("assets", "updated_at")
    op.drop_column("assets", "status")
    op.drop_column("assets", "thumbnail_asset_id")
    op.drop_column("assets", "duration")
    op.drop_column("assets", "height")
    op.drop_column("assets", "width")
    op.drop_column("assets", "file_hash")
    op.drop_column("assets", "file_size")
    op.drop_column("assets", "mime_type")
    op.drop_column("assets", "storage_key")
    op.drop_column("assets", "file_name")
