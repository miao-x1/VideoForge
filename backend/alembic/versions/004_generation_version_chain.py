"""Generation version chain + idempotency fields.

Revision ID: 004_generation_version_chain
Revises: 003_asset_normalization
Create Date: 2026-09-05

Additive only. Does not delete or overwrite generation rows or files.
Reuses director_generations.status and error; does not add a second error column.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.alembic_runtime import add_column_if_missing, create_index_if_missing

revision: str = "004_generation_version_chain"
down_revision: Union[str, Sequence[str], None] = "003_asset_normalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("director_generations", sa.Column("parent_generation_id", sa.String(length=16), nullable=True))
    add_column_if_missing("director_generations", sa.Column("version_number", sa.Integer(), nullable=True))
    add_column_if_missing("director_generations", sa.Column("generation_key", sa.String(length=64), nullable=True))
    add_column_if_missing("director_generations", sa.Column("input_snapshot_json", sa.JSON(), nullable=True))
    create_index_if_missing("ix_director_generations_parent_generation_id", "director_generations", ["parent_generation_id"], unique=False)
    create_index_if_missing("ix_director_generations_generation_key", "director_generations", ["user_id", "project_id", "generation_key"], unique=False)

    add_column_if_missing("director_scenes", sa.Column("current_generation_id", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("director_scenes", "current_generation_id")
    op.drop_index("ix_director_generations_generation_key", table_name="director_generations")
    op.drop_index("ix_director_generations_parent_generation_id", table_name="director_generations")
    op.drop_column("director_generations", "input_snapshot_json")
    op.drop_column("director_generations", "generation_key")
    op.drop_column("director_generations", "version_number")
    op.drop_column("director_generations", "parent_generation_id")
