"""危险 SQL 封装：拒绝无 WHERE 的 DELETE / UPDATE。"""
from __future__ import annotations

from sqlalchemy import delete, update
from sqlalchemy.sql.dml import Delete, Update

from ..core.security_guard import UnsafeDatabaseOperation


def safe_delete(entity, *where_clauses) -> Delete:
    if not where_clauses:
        raise UnsafeDatabaseOperation("DELETE without WHERE is refused")
    stmt = delete(entity)
    for clause in where_clauses:
        stmt = stmt.where(clause)
    if stmt.whereclause is None:
        raise UnsafeDatabaseOperation("DELETE without WHERE is refused")
    return stmt


def safe_update(entity, *where_clauses) -> Update:
    if not where_clauses:
        raise UnsafeDatabaseOperation("UPDATE without WHERE is refused")
    stmt = update(entity)
    for clause in where_clauses:
        stmt = stmt.where(clause)
    if stmt.whereclause is None:
        raise UnsafeDatabaseOperation("UPDATE without WHERE is refused")
    return stmt
