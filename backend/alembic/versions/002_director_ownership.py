"""Director user/project ownership columns.

Revision ID: 002_director_ownership
Revises: 001_baseline
Create Date: 2026-09-05

Adds nullable user_id / project_id. Does not backfill or delete rows.
Historical rows remain orphan (NULL).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.alembic_runtime import add_column_if_missing, create_index_if_missing

revision: str = "002_director_ownership"
down_revision: Union[str, Sequence[str], None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = (
    "director_characters",
    "director_scenes",
    "director_poses",
    "director_custom_animations",
    "director_library_meta",
    "director_agent_logs",
    "director_character_tasks",
)


def upgrade() -> None:
    for table in _SCOPED_TABLES:
        add_column_if_missing(table, sa.Column("user_id", sa.String(length=12), nullable=True))
        add_column_if_missing(table, sa.Column("project_id", sa.String(length=12), nullable=True))
        create_index_if_missing(f"ix_{table}_user_id", table, ["user_id"], unique=False)
        create_index_if_missing(f"ix_{table}_project_id", table, ["project_id"], unique=False)
        create_index_if_missing(f"ix_{table}_user_project", table, ["user_id", "project_id"], unique=False)

    add_column_if_missing("director_generations", sa.Column("user_id", sa.String(length=12), nullable=True))
    create_index_if_missing("ix_director_generations_user_id", "director_generations", ["user_id"], unique=False)
    create_index_if_missing(
        "ix_director_generations_user_project",
        "director_generations",
        ["user_id", "project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_director_generations_user_project", table_name="director_generations")
    op.drop_index("ix_director_generations_user_id", table_name="director_generations")
    op.drop_column("director_generations", "user_id")

    for table in reversed(_SCOPED_TABLES):
        op.drop_index(f"ix_{table}_user_project", table_name=table)
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_column(table, "project_id")
        op.drop_column(table, "user_id")
