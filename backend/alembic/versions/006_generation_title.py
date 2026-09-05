"""Add display title to director generations.

Revision ID: 006_generation_title
Revises: 005_billing_and_credentials
Create Date: 2026-09-05

Additive only. Existing rows keep an empty title and fall back to prompt.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.alembic_runtime import add_column_if_missing

revision: str = "006_generation_title"
down_revision: Union[str, Sequence[str], None] = "005_billing_and_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing(
        "director_generations",
        sa.Column("title", sa.String(length=128), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("director_generations", "title")
