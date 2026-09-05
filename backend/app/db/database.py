"""数据库连接与会话管理。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine as _create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import STORAGE_ROOT, settings


class Base(DeclarativeBase):
    pass


def _default_sqlite_path() -> str:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    return (STORAGE_ROOT / "videoforge.db").as_posix()


def _configured_database_url() -> str:
    url = (settings.database_url or "").strip()
    if url:
        return url
    return f"sqlite+aiosqlite:///{_default_sqlite_path()}"


def _async_database_url() -> str:
    url = _configured_database_url()
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def sync_database_url() -> str:
    """Alembic 与同步 Session 共用的 URL，与应用 DATABASE_URL 同源。"""
    url = _configured_database_url()
    return url.replace("sqlite+aiosqlite://", "sqlite://", 1)


def _sync_database_url() -> str:
    return sync_database_url()


_engine = None
_session_maker = None
_sync_session_factory = None


def _get_engine():
    global _engine, _session_maker
    if _engine is None:
        db_url = _async_database_url()
        _engine = create_async_engine(db_url, echo=False)
        _session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def get_session_maker():
    if _session_maker is None:
        _get_engine()
    return _session_maker


def _has_alembic_version_table(sync_connection) -> bool:
    """True only when Alembic has actually recorded a revision (not an empty leftover table)."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text

    if "alembic_version" not in sa_inspect(sync_connection).get_table_names():
        return False
    row = sync_connection.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    return row is not None and bool(row[0])


async def init_db() -> None:
    """开发/测试启动兜底。create_all 只补缺失表；已有旧表再补缺失列。"""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _repair_assets(conn)
        await _repair_generations(conn)
        if await conn.run_sync(_has_alembic_version_table):
            return
        await _migrate_task_records(conn)
        await _migrate_projects(conn)
        await _migrate_users(conn)


async def _repair_assets(conn) -> None:
    """旧库 assets 只有早期字段时，create_all 不会加列。保存构图 / 出片都会写这些列。"""
    from sqlalchemy import text

    result = await conn.execute(text("PRAGMA table_info(assets)"))
    existing = {row[1] for row in result.fetchall()}
    columns = (
        ("file_name", "VARCHAR(255)"),
        ("storage_key", "TEXT"),
        ("mime_type", "VARCHAR(128)"),
        ("file_size", "INTEGER"),
        ("file_hash", "VARCHAR(64)"),
        ("width", "INTEGER"),
        ("height", "INTEGER"),
        ("duration", "FLOAT"),
        ("thumbnail_asset_id", "VARCHAR(12)"),
        ("status", "VARCHAR(16) DEFAULT 'ready'"),
        ("updated_at", "FLOAT"),
        ("deleted_at", "FLOAT"),
    )
    for name, decl in columns:
        if name not in existing:
            await conn.execute(text(f"ALTER TABLE assets ADD COLUMN {name} {decl}"))


async def _repair_generations(conn) -> None:
    """旧库 director_generations 缺 title 时，create_all 不会加列。"""
    from sqlalchemy import text

    result = await conn.execute(text("PRAGMA table_info(director_generations)"))
    existing = {row[1] for row in result.fetchall()}
    if existing and "title" not in existing:
        await conn.execute(text("ALTER TABLE director_generations ADD COLUMN title VARCHAR(128) DEFAULT ''"))


async def _migrate_users(conn) -> None:
    from sqlalchemy import text
    result = await conn.execute(text("PRAGMA table_info(users)"))
    existing = {row[1] for row in result.fetchall()}
    if "phone" not in existing:
        await conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT ''"))


async def _migrate_projects(conn) -> None:
    """轻量迁移:为 projects 补充 memory_json 列(Project Memory)。"""
    from sqlalchemy import text
    result = await conn.execute(text("PRAGMA table_info(projects)"))
    existing = {row[1] for row in result.fetchall()}
    if "memory_json" not in existing:
        await conn.execute(text("ALTER TABLE projects ADD COLUMN memory_json JSON"))


async def _migrate_task_records(conn) -> None:
    """轻量迁移:为 task_records 补充缺失列(SQLite ALTER TABLE)。"""
    from sqlalchemy import text
    result = await conn.execute(text("PRAGMA table_info(task_records)"))
    existing = {row[1] for row in result.fetchall()}
    if "spec_json" not in existing:
        await conn.execute(text("ALTER TABLE task_records ADD COLUMN spec_json JSON"))
    if "mode" not in existing:
        await conn.execute(text("ALTER TABLE task_records ADD COLUMN mode VARCHAR(16) DEFAULT 'quick'"))
    if "project_id" not in existing:
        await conn.execute(text("ALTER TABLE task_records ADD COLUMN project_id VARCHAR(32)"))
    if "model_used" not in existing:
        await conn.execute(text("ALTER TABLE task_records ADD COLUMN model_used VARCHAR(64)"))


def reset_engine() -> None:
    global _engine, _session_maker, _sync_session_factory
    if _engine is not None:
        _engine.sync_engine.dispose()
    _engine = None
    _session_maker = None
    _sync_session_factory = None


class _AsyncSessionContext:
    async def __aenter__(self):
        sm = get_session_maker()
        self._session = sm()
        return self._session

    async def __aexit__(self, *args):
        await self._session.close()


def async_session():
    return _AsyncSessionContext()


@contextmanager
def get_session() -> Iterator[Session]:
    """同步数据库会话(供 project_routes 等同步风格路由使用)。

    与异步引擎指向同一个 SQLite 文件,靠 SQLite 文件锁保证一致性。
    """
    global _sync_session_factory
    if _sync_session_factory is None:
        sync_engine = _create_sync_engine(_sync_database_url(), echo=False)
        _sync_session_factory = sessionmaker(bind=sync_engine, expire_on_commit=False)
    session = _sync_session_factory()
    try:
        yield session
    finally:
        session.close()


async def get_db() -> AsyncSession:
    sm = get_session_maker()
    async with sm() as session:
        yield session
