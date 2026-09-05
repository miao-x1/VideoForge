"""Alembic 命令入口。与应用共用 sync_database_url() / DATABASE_URL。"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from .database import sync_database_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "001_baseline"
HEAD_REVISION = "006_generation_title"


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


def upgrade_head() -> None:
    command.upgrade(alembic_config(), "head")


def downgrade_base() -> None:
    command.downgrade(alembic_config(), "base")


def stamp_head() -> None:
    command.stamp(alembic_config(), "head")


def stamp_revision(revision: str) -> None:
    command.stamp(alembic_config(), revision)


def current_revision() -> str | None:
    engine = create_engine(sync_database_url())
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            return ctx.get_current_revision()
    finally:
        engine.dispose()


def script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(alembic_config())


def heads() -> list[str]:
    return list(script_directory().get_heads())


def has_column(table: str, column: str) -> bool:
    from alembic import op
    from sqlalchemy import inspect as sa_inspect

    return column in {c["name"] for c in sa_inspect(op.get_bind()).get_columns(table)}


def has_index(table: str, name: str) -> bool:
    from alembic import op
    from sqlalchemy import inspect as sa_inspect

    bind = op.get_bind()
    names = {ix["name"] for ix in sa_inspect(bind).get_indexes(table)}
    names.update(uq["name"] for uq in sa_inspect(bind).get_unique_constraints(table) if uq.get("name"))
    return name in names


def add_column_if_missing(table: str, column) -> None:
    from alembic import op

    if not has_column(table, column.name):
        op.add_column(table, column)


def create_index_if_missing(name: str, table: str, columns: list[str], *, unique: bool = False) -> None:
    from alembic import op

    if not has_index(table, name):
        op.create_index(name, table, columns, unique=unique)


def history_revision_ids() -> list[str]:
    return [rev.revision for rev in script_directory().walk_revisions()]
