"""数据库连接与会话管理。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine as _create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import STORAGE_ROOT


class Base(DeclarativeBase):
    pass


_engine = None
_session_maker = None
_sync_session_factory = None


def _get_engine():
    global _engine, _session_maker
    if _engine is None:
        db_path = STORAGE_ROOT / "videoforge.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"
        _engine = create_async_engine(db_url, echo=False)
        _session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def get_session_maker():
    if _session_maker is None:
        _get_engine()
    return _session_maker


async def init_db() -> None:
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_task_records(conn)
        await _migrate_projects(conn)


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
    global _engine, _session_maker
    if _engine is not None:
        _engine.sync_engine.dispose()
    _engine = None
    _session_maker = None


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
        db_path = STORAGE_ROOT / "videoforge.db"
        sync_engine = _create_sync_engine(f"sqlite:///{db_path}", echo=False)
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
