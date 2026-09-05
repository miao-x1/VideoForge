"""用户认证 Pydantic schemas。"""
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """兼容旧测试：邮箱 + 密码注册。新前端走 account + verify_code。"""
    email: str | None = None
    account: str | None = None
    password: str
    display_name: str = ""
    captcha_id: str = ""
    captcha_code: str = ""
    verify_code: str = ""
    agree: bool = True


class UserLogin(BaseModel):
    email: str | None = None
    account: str | None = None
    password: str = ""
    captcha_id: str = ""
    captcha_code: str = ""
    remember: bool = False


class SmsLoginRequest(BaseModel):
    account: str
    verify_code: str
    captcha_id: str
    captcha_code: str
    remember: bool = False


class SendCodeRequest(BaseModel):
    account: str
    purpose: str = Field(pattern="^(register|login|reset)$")
    captcha_id: str
    captcha_code: str


class SendCodeResponse(BaseModel):
    ok: bool = True
    cooldown: int = 60
    message: str
    dev_code: str | None = None


class AuthStatus(BaseModel):
    sms_configured: bool = False
    email_configured: bool = False
    password_login: bool = True


class CaptchaResponse(BaseModel):
    captcha_id: str
    image: str
    debug_text: str | None = None


class ForgotPasswordRequest(BaseModel):
    account: str
    captcha_id: str
    captcha_code: str


class ResetPasswordRequest(BaseModel):
    account: str
    verify_code: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    phone: str = ""
    display_name: str
    created_at: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
