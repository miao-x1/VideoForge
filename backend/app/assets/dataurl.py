"""Data URL 检测与剥离。持久化不得把大型 base64 写入 JSON。"""
from __future__ import annotations

import base64
import re
from typing import Any, Callable

_DATA_URL = re.compile(
    r"^data:(image|video|audio)/([A-Za-z0-9.+-]+)(;charset=[^;]+)?;base64,(.+)$",
    re.DOTALL,
)


def is_data_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("data:image/", "data:video/", "data:audio/"))


def count_data_urls(obj: Any) -> int:
    if is_data_url(obj):
        return 1
    if isinstance(obj, dict):
        return sum(count_data_urls(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_data_urls(v) for v in obj)
    return 0


def decode_data_url(value: str) -> tuple[bytes, str, str]:
    match = _DATA_URL.match(value)
    if not match:
        raise ValueError("无效 Data URL")
    kind, subtype, _charset, payload = match.groups()
    raw = base64.b64decode(payload, validate=False)
    mime = f"{kind}/{subtype}"
    ext = {
        "png": ".png",
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "webp": ".webp",
        "gif": ".gif",
        "mp4": ".mp4",
        "webm": ".webm",
        "mpeg": ".mp3",
        "wav": ".wav",
    }.get(subtype.lower(), f".{subtype.lower()[:8]}")
    return raw, mime, ext


TokenFn = Callable[[bytes, str, str], str]


def replace_data_urls(obj: Any, replace: TokenFn) -> Any:
    """把 Data URL 换成 replace() 的占位/引用。"""
    if is_data_url(obj):
        raw, mime, ext = decode_data_url(obj)
        return replace(raw, mime, ext)
    if isinstance(obj, dict):
        return {key: replace_data_urls(value, replace) for key, value in obj.items()}
    if isinstance(obj, list):
        return [replace_data_urls(item, replace) for item in obj]
    return obj


def apply_asset_tokens(obj: Any, tokens: dict[str, str]) -> Any:
    if isinstance(obj, str) and obj in tokens:
        return tokens[obj]
    if isinstance(obj, dict):
        return {key: apply_asset_tokens(value, tokens) for key, value in obj.items()}
    if isinstance(obj, list):
        return [apply_asset_tokens(item, tokens) for item in obj]
    return obj
