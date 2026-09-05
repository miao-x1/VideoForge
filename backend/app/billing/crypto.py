"""用 JWT secret 派生 Fernet，加密用户自带 Key。禁止把明文写进日志或接口。"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from ..core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
