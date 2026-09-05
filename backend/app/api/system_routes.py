"""系统级危险操作入口。Wave 0 即使开发环境也不真正清库。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..assets.consistency import check_consistency, scan_data_urls
from ..auth.dependencies import get_current_user
from ..core.security_guard import ResetDenied, assert_reset_allowed
from ..db.database import get_session
from ..db.models import User

router = APIRouter(prefix="/api/system", tags=["system"])


@router.post("/reset-database")
async def reset_database() -> dict:
    try:
        assert_reset_allowed()
    except ResetDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    # 明确不执行 DROP / TRUNCATE / 删库文件
    raise HTTPException(403, "Wave 0 拒绝执行数据库 reset，即使开发环境也不会删除数据")


@router.get("/asset-consistency")
async def asset_consistency(_user: User = Depends(get_current_user)) -> dict:
    """只检查，不删除 orphan / 缺失文件。"""
    with get_session() as session:
        report = check_consistency(session)
        report["data_urls"] = scan_data_urls(session)
    return report
