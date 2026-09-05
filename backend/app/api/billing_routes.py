"""用户 API 接入：平台充值 或 自带 Key。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..billing.errors import BillingError
from ..billing.service import (
    PACKAGES,
    credit_wallet,
    delete_credential,
    dev_recharge_allowed,
    dump_credential,
    dump_ledger,
    dump_status,
    list_ledger,
    save_credential,
    update_prefs,
)
from ..db.database import get_db
from ..db.models import User

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CredentialBody(BaseModel):
    provider: str = "minimax"
    api_key: str
    base_url: str = ""


class PrefsBody(BaseModel):
    video_source: str | None = None
    video_provider: str | None = None
    video_model: str | None = None


class RechargeBody(BaseModel):
    package_id: str = ""
    yuan: float | None = Field(default=None, ge=0, le=1000)


def _http(exc: BillingError) -> HTTPException:
    return HTTPException(exc.http_status, exc.message)


@router.get("/status")
async def billing_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    data = await dump_status(db, user.id)
    await db.commit()
    return data


@router.put("/prefs")
async def billing_prefs(
    body: PrefsBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        await update_prefs(
            db,
            user.id,
            video_source=body.video_source,
            video_provider=body.video_provider,
            video_model=body.video_model,
        )
        data = await dump_status(db, user.id)
        await db.commit()
        return data
    except BillingError as exc:
        raise _http(exc) from exc


@router.put("/credentials")
async def put_credentials(
    body: CredentialBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        row = await save_credential(
            db,
            user.id,
            provider=body.provider,
            api_key=body.api_key,
            base_url=body.base_url,
        )
        await db.commit()
        return {"ok": True, "credential": dump_credential(row)}
    except BillingError as exc:
        raise _http(exc) from exc


@router.delete("/credentials/{provider}")
async def remove_credentials(
    provider: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    deleted = await delete_credential(db, user.id, provider)
    await db.commit()
    return {"ok": True, "deleted": deleted}


@router.get("/ledger")
async def billing_ledger(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    rows = await list_ledger(db, user.id, limit=limit)
    return {"items": [dump_ledger(row) for row in rows]}


@router.post("/recharge")
async def billing_recharge(
    body: RechargeBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if not dev_recharge_allowed():
        raise HTTPException(501, "微信支付 / 支付宝即将接入。当前请使用自己的 API Key，或联系运营人工入账。")
    fen = 0
    note = "手动入账"
    if body.package_id:
        pack = next((item for item in PACKAGES if item["id"] == body.package_id), None)
        if pack is None:
            raise HTTPException(400, "套餐不存在")
        fen = int(pack["fen"])
        note = f"本站测试额度 {pack['label']}，不转账到 MiniMax"
    elif body.yuan is not None:
        fen = int(round(float(body.yuan) * 100))
        note = f"本站测试额度 {body.yuan:.2f} 元，不转账到 MiniMax"
    if fen <= 0:
        raise HTTPException(400, "请选择套餐或填写金额")
    try:
        await credit_wallet(db, user.id, fen, kind="recharge", note=note)
        data = await dump_status(db, user.id)
        await db.commit()
        return data
    except BillingError as exc:
        raise _http(exc) from exc
