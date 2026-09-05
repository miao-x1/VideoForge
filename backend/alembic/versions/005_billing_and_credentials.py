"""User wallet, ledger, BYOK credentials, billing prefs.

Revision ID: 005_billing_and_credentials
Revises: 004_generation_version_chain
Create Date: 2026-09-05

Additive only. Does not touch existing generation or user rows.
Safe if tables were already created by init_db create_all.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

from app.db.alembic_runtime import create_index_if_missing

revision: str = "005_billing_and_credentials"
down_revision: Union[str, Sequence[str], None] = "004_generation_version_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(sa_inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "user_wallets" not in existing:
        op.create_table(
            "user_wallets",
            sa.Column("user_id", sa.String(length=12), nullable=False),
            sa.Column("balance_fen", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if "wallet_ledger" not in existing:
        op.create_table(
            "wallet_ledger",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=12), nullable=False),
            sa.Column("delta_fen", sa.Integer(), nullable=False),
            sa.Column("balance_after", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(length=24), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=False),
            sa.Column("ref_id", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    create_index_if_missing("ix_wallet_ledger_user_id", "wallet_ledger", ["user_id"], unique=False)

    if "user_api_credentials" not in existing:
        op.create_table(
            "user_api_credentials",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=12), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("encrypted_key", sa.Text(), nullable=False),
            sa.Column("base_url", sa.String(length=255), nullable=False),
            sa.Column("last4", sa.String(length=8), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    create_index_if_missing("ix_user_api_credentials_user_id", "user_api_credentials", ["user_id"], unique=False)
    create_index_if_missing(
        "ix_user_api_credentials_user_provider",
        "user_api_credentials",
        ["user_id", "provider"],
        unique=True,
    )

    if "user_billing_prefs" not in existing:
        op.create_table(
            "user_billing_prefs",
            sa.Column("user_id", sa.String(length=12), nullable=False),
            sa.Column("video_source", sa.String(length=16), nullable=False),
            sa.Column("video_provider", sa.String(length=32), nullable=False),
            sa.Column("video_model", sa.String(length=64), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("user_id"),
        )


def downgrade() -> None:
    existing = _tables()
    if "user_billing_prefs" in existing:
        op.drop_table("user_billing_prefs")
    if "user_api_credentials" in existing:
        op.drop_index("ix_user_api_credentials_user_provider", table_name="user_api_credentials")
        op.drop_index("ix_user_api_credentials_user_id", table_name="user_api_credentials")
        op.drop_table("user_api_credentials")
    if "wallet_ledger" in existing:
        op.drop_index("ix_wallet_ledger_user_id", table_name="wallet_ledger")
        op.drop_table("wallet_ledger")
    if "user_wallets" in existing:
        op.drop_table("user_wallets")
