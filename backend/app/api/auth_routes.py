"""用户认证：登录 / 注册 / 图形验证码 / 短信邮箱验证码 / 忘记密码。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.account import account_channel, display_account, is_email, is_phone, normalize_account
from ..auth.captcha import create_captcha, verify_captcha
from ..auth.dependencies import get_current_user
from ..auth.jwt_handler import create_access_token
from ..auth.password import hash_password, verify_password
from ..auth.schemas import (
    AuthStatus,
    CaptchaResponse,
    ResetPasswordRequest,
    SendCodeRequest,
    SendCodeResponse,
    SmsLoginRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
)
from ..auth.verification import channel_ready, consume_code, email_delivery_ready, issue_code, sms_delivery_ready
from ..db.database import get_db
from ..db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        phone=getattr(user, "phone", "") or "",
        display_name=user.display_name,
        created_at=user.created_at,
    )


def _token(user: User, remember: bool = False) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.email, remember=remember),
        user=_user_out(user),
    )


async def _find_user(db: AsyncSession, account: str) -> User | None:
    value = display_account(account)
    stmt = select(User).where(or_(User.email == value, User.phone == normalize_account(account)))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _require_captcha(captcha_id: str, captcha_code: str) -> None:
    if not captcha_id or not captcha_code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请填写图形验证码")
    if not verify_captcha(captcha_id, captcha_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "图形验证码错误或已过期，请点击图片刷新")


@router.get("/status", response_model=AuthStatus)
async def auth_status():
    return AuthStatus(
        sms_configured=sms_delivery_ready(),
        email_configured=email_delivery_ready(),
        password_login=True,
    )


@router.get("/captcha", response_model=CaptchaResponse)
async def captcha():
    captcha_id, image, code = create_captcha()
    from ..core.security_guard import allow_dev_echo
    debug = code if allow_dev_echo() else None
    return CaptchaResponse(captcha_id=captcha_id, image=image, debug_text=debug)


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(body: SendCodeRequest, db: AsyncSession = Depends(get_db)):
    _require_captcha(body.captcha_id, body.captcha_code)
    try:
        channel = account_channel(body.account)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    target = display_account(body.account)
    existing = await _find_user(db, body.account)
    if body.purpose == "register" and existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该账号已注册，请直接登录或找回密码")
    if body.purpose in ("login", "reset") and existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该账号尚未注册")
    try:
        code, echoed = await issue_code(db, target=target, channel=channel, purpose=body.purpose)
    except ValueError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    delivered = channel_ready(channel) and not echoed
    if delivered:
        sent = "验证码已发送到手机" if channel == "sms" else "验证码已发送到邮箱"
    elif echoed:
        sent = f"未配置短信/邮箱通道，验证码不会发到手机或邮箱。本次验证码：{code}"
    else:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "未配置短信/邮箱通道，请使用密码登录或注册")
    return SendCodeResponse(message=sent, dev_code=code if echoed else None)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    raw = body.account or body.email or ""
    try:
        channel = account_channel(raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    target = display_account(raw)
    if len(body.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "密码至少 6 位")
    if not body.agree:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先同意用户协议")

    if channel_ready(channel):
        if len(body.password) < 8:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "密码至少 8 位")
        _require_captcha(body.captcha_id, body.captcha_code)
        ok = await consume_code(db, target=target, purpose="register", code=body.verify_code)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误或已过期")
    elif body.captcha_id or body.captcha_code:
        if len(body.password) < 8:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "密码至少 8 位")
        _require_captcha(body.captcha_id, body.captcha_code)

    existing = await _find_user(db, raw)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该账号已注册")

    email = target if is_email(raw) else f"{normalize_account(raw)}@phone.videoforge.local"
    phone = normalize_account(raw) if is_phone(raw) else ""
    if is_email(raw):
        clash = await db.execute(select(User).where(User.email == email))
        if clash.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册")

    user = User(
        email=email,
        phone=phone,
        hashed_password=hash_password(body.password),
        display_name=body.display_name or (phone or email.split("@")[0]),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _token(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    raw = body.account or body.email or ""
    if not raw or not body.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请输入账号和密码")
    if body.captcha_id:
        _require_captcha(body.captcha_id, body.captcha_code)
    user = await _find_user(db, raw)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    return _token(user, remember=body.remember)


@router.post("/login-sms", response_model=TokenResponse)
async def login_sms(body: SmsLoginRequest, db: AsyncSession = Depends(get_db)):
    _require_captcha(body.captcha_id, body.captcha_code)
    try:
        account_channel(body.account)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    target = display_account(body.account)
    ok = await consume_code(db, target=target, purpose="login", code=body.verify_code)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误或已过期")
    user = await _find_user(db, body.account)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该账号尚未注册")
    return _token(user, remember=body.remember)


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        account_channel(body.account)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if len(body.password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码至少 8 位")
    target = display_account(body.account)
    ok = await consume_code(db, target=target, purpose="reset", code=body.verify_code)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误或已过期")
    user = await _find_user(db, body.account)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该账号尚未注册")
    user.hashed_password = hash_password(body.password)
    await db.commit()
    return {"ok": True, "message": "密码已重置，请使用新密码登录"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)
