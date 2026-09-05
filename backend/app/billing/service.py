"""钱包、凭证、出片前预扣。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import UserApiCredential, UserBillingPref, UserWallet, WalletLedger
from .crypto import decrypt_secret, encrypt_secret
from .errors import BillingError, CredentialMissingError, WalletInsufficientError

PACKAGES = (
    {"id": "p30", "yuan": 30, "fen": 3000, "label": "30 元"},
    {"id": "p100", "yuan": 100, "fen": 10000, "label": "100 元"},
    {"id": "p300", "yuan": 300, "fen": 30000, "label": "300 元"},
)

_PRICE_FEN_PER_SEC = {
    "minimax": 80,
    "qwen": 50,
}

_ALLOWED_PROVIDERS = frozenset({"minimax", "qwen"})
_MINIMAX_URLS = ("https://api.minimax.cn", "https://api.minimax.io")


@dataclass
class VideoAccess:
    source: str
    provider: str
    api_key: str
    base_url: str
    model: str
    reserved_fen: int
    reservation_id: str


def default_video_provider() -> str:
    choice = settings.video_model_provider
    return choice if choice in _ALLOWED_PROVIDERS else "minimax"


def price_fen_per_sec(provider: str) -> int:
    return _PRICE_FEN_PER_SEC.get(provider, 80)


def estimate_fen(provider: str, duration: int) -> int:
    seconds = max(1, int(duration or 1))
    return seconds * price_fen_per_sec(provider)


def fen_to_yuan(fen: int) -> str:
    return f"{fen / 100:.2f}"


def platform_catalog() -> list[dict]:
    qwen_ready = bool(settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key)
    region = "cn" if "minimax.cn" in (settings.minimax_base_url or "") else "intl"
    return [
        {
            "provider": "minimax",
            "model": settings.minimax_video_model or "MiniMax-H3",
            "label": "MiniMax H3 视频",
            "price_fen_per_sec": price_fen_per_sec("minimax"),
            "available": bool(settings.minimax_api_key),
            "region": region,
        },
        {
            "provider": "qwen",
            "model": settings.qwen_video_model or "wan2.6-i2v-flash",
            "label": "通义万相 视频",
            "price_fen_per_sec": price_fen_per_sec("qwen"),
            "available": qwen_ready,
            "region": "cn",
        },
    ]


def dev_recharge_allowed() -> bool:
    return settings.app_env in ("development", "dev", "test")


def _welcome_fen() -> int:
    if settings.app_env in ("development", "dev"):
        return 10000
    return 0


def _last4(key: str) -> str:
    text = key.strip()
    return text[-4:] if len(text) >= 4 else "****"


async def get_or_create_wallet(db: AsyncSession, user_id: str) -> UserWallet:
    wallet = await db.get(UserWallet, user_id)
    if wallet:
        return wallet
    gift = _welcome_fen()
    wallet = UserWallet(user_id=user_id, balance_fen=gift)
    db.add(wallet)
    if gift:
        db.add(
            WalletLedger(
                user_id=user_id,
                delta_fen=gift,
                balance_after=gift,
                kind="welcome",
                note="开发环境体验额度",
                ref_id="",
            )
        )
    await db.flush()
    return wallet


async def get_or_create_prefs(db: AsyncSession, user_id: str) -> UserBillingPref:
    prefs = await db.get(UserBillingPref, user_id)
    if prefs:
        return prefs
    prefs = UserBillingPref(
        user_id=user_id,
        video_source="platform",
        video_provider=default_video_provider(),
        video_model="",
    )
    db.add(prefs)
    await db.flush()
    return prefs


async def list_credentials(db: AsyncSession, user_id: str) -> list[UserApiCredential]:
    result = await db.execute(select(UserApiCredential).where(UserApiCredential.user_id == user_id))
    return list(result.scalars().all())


async def get_credential(db: AsyncSession, user_id: str, provider: str) -> UserApiCredential | None:
    result = await db.execute(
        select(UserApiCredential).where(
            UserApiCredential.user_id == user_id,
            UserApiCredential.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def save_credential(
    db: AsyncSession,
    user_id: str,
    *,
    provider: str,
    api_key: str,
    base_url: str = "",
) -> UserApiCredential:
    if provider not in _ALLOWED_PROVIDERS:
        raise CredentialMissingError("暂不支持该模型供应商")
    key = api_key.strip()
    if len(key) < 8:
        raise CredentialMissingError("API Key 无效")
    url = (base_url or "").strip().rstrip("/")
    if provider == "minimax" and url and url not in _MINIMAX_URLS:
        raise CredentialMissingError("MiniMax 地址请选国内站或国际站")
    if provider == "minimax" and not url:
        url = (settings.minimax_base_url or "https://api.minimax.cn").rstrip("/")

    row = await get_credential(db, user_id, provider)
    if row is None:
        row = UserApiCredential(user_id=user_id, provider=provider)
        db.add(row)
    row.encrypted_key = encrypt_secret(key)
    row.base_url = url
    row.last4 = _last4(key)
    row.enabled = True
    await db.flush()
    return row


async def delete_credential(db: AsyncSession, user_id: str, provider: str) -> bool:
    row = await get_credential(db, user_id, provider)
    if row is None:
        return False
    await db.delete(row)
    await db.flush()
    return True


async def update_prefs(
    db: AsyncSession,
    user_id: str,
    *,
    video_source: str | None = None,
    video_provider: str | None = None,
    video_model: str | None = None,
) -> UserBillingPref:
    prefs = await get_or_create_prefs(db, user_id)
    if video_source in ("platform", "own"):
        prefs.video_source = video_source
    if video_provider in _ALLOWED_PROVIDERS:
        prefs.video_provider = video_provider
    if video_model is not None:
        prefs.video_model = video_model.strip()[:64]
    await db.flush()
    return prefs


async def credit_wallet(
    db: AsyncSession,
    user_id: str,
    fen: int,
    *,
    kind: str = "recharge",
    note: str = "",
    ref_id: str = "",
) -> UserWallet:
    if fen <= 0:
        raise BillingError("入账金额必须大于 0", http_status=400)
    wallet = await get_or_create_wallet(db, user_id)
    wallet.balance_fen += fen
    db.add(
        WalletLedger(
            user_id=user_id,
            delta_fen=fen,
            balance_after=wallet.balance_fen,
            kind=kind,
            note=note,
            ref_id=ref_id,
        )
    )
    await db.flush()
    return wallet


async def list_ledger(db: AsyncSession, user_id: str, limit: int = 20) -> list[WalletLedger]:
    result = await db.execute(
        select(WalletLedger)
        .where(WalletLedger.user_id == user_id)
        .order_by(WalletLedger.id.desc())
        .limit(max(1, min(limit, 50)))
    )
    return list(result.scalars().all())


def dump_credential(row: UserApiCredential) -> dict:
    return {
        "provider": row.provider,
        "last4": row.last4,
        "base_url": row.base_url,
        "enabled": row.enabled,
    }


def dump_ledger(row: WalletLedger) -> dict:
    return {
        "id": row.id,
        "delta_fen": row.delta_fen,
        "balance_after": row.balance_after,
        "kind": row.kind,
        "note": row.note,
        "created_at": row.created_at,
    }


async def dump_status(db: AsyncSession, user_id: str) -> dict:
    wallet = await get_or_create_wallet(db, user_id)
    prefs = await get_or_create_prefs(db, user_id)
    creds = await list_credentials(db, user_id)
    catalog = platform_catalog()
    selected = next((item for item in catalog if item["provider"] == prefs.video_provider), catalog[0])
    return {
        "video_source": prefs.video_source,
        "video_provider": prefs.video_provider,
        "video_model": prefs.video_model or selected.get("model") or "",
        "wallet": {
            "balance_fen": wallet.balance_fen,
            "balance_yuan": fen_to_yuan(wallet.balance_fen),
        },
        "credentials": [dump_credential(row) for row in creds],
        "catalog": catalog,
        "packages": list(PACKAGES),
        "price_fen_per_sec": price_fen_per_sec(prefs.video_provider),
        "dev_recharge": dev_recharge_allowed(),
        "platform_ready": bool(selected.get("available")),
        "wallet_kind": "platform_ledger",
        "recharge_kind": "dev_credit" if dev_recharge_allowed() else "payment_pending",
        "wallet_note": "这是 VideoForge 本站账本，不是 MiniMax / 通义 账户余额。",
        "minimax_note": (
            "平台模式用运营方 .env 里的 MINIMAX_API_KEY 调 MiniMax，再从本站余额扣费；"
            "自己的 Key 直接打你的 MiniMax 账户，本站不扣费。"
        ),
    }


async def reserve_video_access(db: AsyncSession, user_id: str, duration: int) -> VideoAccess:
    prefs = await get_or_create_prefs(db, user_id)
    provider = prefs.video_provider if prefs.video_provider in _ALLOWED_PROVIDERS else default_video_provider()
    model = prefs.video_model

    if prefs.video_source == "own":
        cred = await get_credential(db, user_id, provider)
        if cred is None or not cred.enabled:
            raise CredentialMissingError("请先填写自己的 API Key，或改用平台模型并充值")
        try:
            key = decrypt_secret(cred.encrypted_key)
        except Exception as exc:
            raise CredentialMissingError("已保存的 API Key 无法解密，请重新填写") from exc
        return VideoAccess(
            source="own",
            provider=provider,
            api_key=key,
            base_url=cred.base_url,
            model=model,
            reserved_fen=0,
            reservation_id="",
        )

    if provider == "minimax" and not settings.minimax_api_key:
        raise BillingError("平台尚未配置 MiniMax，请改用自己的 API Key", http_status=503)
    if provider == "qwen" and not (settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key):
        raise BillingError("平台尚未配置通义万相，请改用自己的 API Key", http_status=503)

    cost = estimate_fen(provider, duration)
    wallet = await get_or_create_wallet(db, user_id)
    if wallet.balance_fen < cost:
        need = fen_to_yuan(cost)
        have = fen_to_yuan(wallet.balance_fen)
        raise WalletInsufficientError(f"平台余额不足（需要 {need} 元，当前 {have} 元），请充值或改用自己的 API Key")

    reservation_id = uuid.uuid4().hex[:12]
    wallet.balance_fen -= cost
    db.add(
        WalletLedger(
            user_id=user_id,
            delta_fen=-cost,
            balance_after=wallet.balance_fen,
            kind="consume",
            note=f"视频 {max(1, int(duration or 1))} 秒",
            ref_id=reservation_id,
        )
    )
    await db.flush()

    if provider == "minimax":
        key = settings.minimax_api_key
        base_url = (settings.minimax_base_url or "").rstrip("/")
        model = model or settings.minimax_video_model
    else:
        key = settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key
        base_url = ""
        model = model or settings.qwen_video_model

    return VideoAccess(
        source="platform",
        provider=provider,
        api_key=key,
        base_url=base_url,
        model=model,
        reserved_fen=cost,
        reservation_id=reservation_id,
    )


async def refund_reservation(db: AsyncSession, user_id: str, access: VideoAccess) -> None:
    if access.reserved_fen <= 0:
        return
    wallet = await get_or_create_wallet(db, user_id)
    wallet.balance_fen += access.reserved_fen
    db.add(
        WalletLedger(
            user_id=user_id,
            delta_fen=access.reserved_fen,
            balance_after=wallet.balance_fen,
            kind="refund",
            note="生成失败退回",
            ref_id=access.reservation_id,
        )
    )
    await db.flush()
