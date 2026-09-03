"""用户认证 Pydantic schemas。"""
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
