"""短信 / 邮箱验证码：落库、频控、一次性消费。"""
from __future__ import annotations

import hashlib
import random
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.logging import logger
from ..core.security_guard import allow_dev_echo
from ..db.models import VerificationCode

CODE_TTL_SECONDS = 600
SEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 8


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _utcnow() -> float:
    return datetime.now(timezone.utc).timestamp()


async def issue_code(
    db: AsyncSession,
    *,
    target: str,
    channel: str,
    purpose: str,
) -> tuple[str, bool]:
    """生成验证码。返回 (plain_code, echoed)。"""
    now = _utcnow()
    recent = await db.execute(
        select(VerificationCode)
        .where(
            VerificationCode.target == target,
            VerificationCode.purpose == purpose,
            VerificationCode.created_at > now - 3600,
        )
        .order_by(VerificationCode.created_at.desc())
    )
    rows = list(recent.scalars())
    if rows and now - rows[0].created_at < SEND_COOLDOWN_SECONDS:
        wait = int(SEND_COOLDOWN_SECONDS - (now - rows[0].created_at))
        raise ValueError(f"发送过于频繁，请 {wait} 秒后再试")
    if len(rows) >= MAX_SENDS_PER_HOUR:
        raise ValueError("该账号一小时内验证码次数已达上限")

    code = f"{random.randint(0, 999999):06d}"
    row = VerificationCode(
        target=target,
        channel=channel,
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=now + CODE_TTL_SECONDS,
        consumed=False,
        created_at=now,
    )
    db.add(row)
    await db.commit()

    echoed = _deliver(target, channel, purpose, code)
    return code, echoed


async def consume_code(
    db: AsyncSession,
    *,
    target: str,
    purpose: str,
    code: str,
) -> bool:
    now = _utcnow()
    result = await db.execute(
        select(VerificationCode)
        .where(
            VerificationCode.target == target,
            VerificationCode.purpose == purpose,
            VerificationCode.consumed.is_(False),
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_at.desc())
    )
    row = result.scalars().first()
    if row is None:
        return False
    if row.code_hash != _hash_code((code or "").strip()):
        return False
    row.consumed = True
    await db.commit()
    return True


def email_delivery_ready() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def sms_delivery_ready() -> bool:
    return bool(
        settings.sms_access_key
        and settings.sms_access_secret
        and settings.sms_sign_name
        and settings.sms_template_code
    )


def channel_ready(channel: str) -> bool:
    if channel == "email":
        return email_delivery_ready()
    if channel == "sms":
        return sms_delivery_ready()
    return False


def _send_email(target: str, purpose: str, code: str) -> bool:
    label = {"register": "注册", "login": "登录", "reset": "重置密码"}.get(purpose, purpose)
    sender = settings.smtp_from or settings.smtp_user
    msg = MIMEText(f"你的 VideoForge {label}验证码是 {code}，10 分钟内有效。", "plain", "utf-8")
    msg["Subject"] = f"VideoForge {label}验证码"
    msg["From"] = sender
    msg["To"] = target
    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=12) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(sender, [target], msg.as_string())
        logger.info("邮件验证码已发送 purpose=%s", label)
        return True
    except Exception:
        logger.exception("邮件验证码发送失败 purpose=%s", label)
        return False


def _deliver(target: str, channel: str, purpose: str, code: str) -> bool:
    """真正投递。成功返回 False（不要回显）；失败或未配置时，开发环境才回显。"""
    label = {"register": "注册", "login": "登录", "reset": "重置密码"}.get(purpose, purpose)
    if channel == "email" and email_delivery_ready():
        if _send_email(target, purpose, code):
            return False
        return allow_dev_echo()
    if channel == "sms" and sms_delivery_ready():
        logger.warning("短信通道已配置但尚未接入运营商发送，purpose=%s", label)
        return allow_dev_echo()
    logger.info("验证码未配置发送通道 purpose=%s", label)
    return allow_dev_echo()
