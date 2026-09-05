"""账号格式：邮箱或中国大陆手机号。"""
from __future__ import annotations

import re

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_account(raw: str) -> str:
    return (raw or "").strip()


def is_phone(account: str) -> bool:
    return bool(PHONE_RE.match(normalize_account(account)))


def is_email(account: str) -> bool:
    return bool(EMAIL_RE.match(normalize_account(account).lower()))


def account_channel(account: str) -> str:
    value = normalize_account(account)
    if is_phone(value):
        return "sms"
    if is_email(value):
        return "email"
    raise ValueError("请输入有效的邮箱或手机号")


def display_account(account: str) -> str:
    value = normalize_account(account)
    return value.lower() if is_email(value) else value
