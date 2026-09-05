"""图形验证码：服务端生成，一次性校验。"""
from __future__ import annotations

import base64
import io
import random
import secrets
import time
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from ..core.config import settings

_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TTL_SECONDS = 300


@dataclass
class _CaptchaRecord:
    code: str
    expires_at: float


_STORE: dict[str, _CaptchaRecord] = {}


def _purge() -> None:
    now = time.time()
    dead = [k for k, v in _STORE.items() if v.expires_at < now]
    for k in dead:
        _STORE.pop(k, None)


def create_captcha() -> tuple[str, str, str]:
    """返回 (captcha_id, data_url, plain_code)。plain_code 仅供开发回显。"""
    _purge()
    code = "".join(random.choice(_CHARS) for _ in range(4))
    captcha_id = secrets.token_urlsafe(16)
    _STORE[captcha_id] = _CaptchaRecord(code=code, expires_at=time.time() + _TTL_SECONDS)
    return captcha_id, _render_data_url(code), code


def verify_captcha(captcha_id: str, user_input: str, *, consume: bool = True) -> bool:
    _purge()
    rec = _STORE.get(captcha_id)
    if rec is None or rec.expires_at < time.time():
        _STORE.pop(captcha_id, None)
        return False
    ok = (user_input or "").strip().upper() == rec.code
    if consume:
        _STORE.pop(captcha_id, None)
    return ok


def _render_data_url(code: str) -> str:
    width, height = 128, 44
    image = Image.new("RGB", (width, height), (245, 247, 252))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(settings.subtitle_font_path, 26)
    except OSError:
        font = ImageFont.load_default()

    for _ in range(6):
        draw.line(
            [
                (random.randint(0, width), random.randint(0, height)),
                (random.randint(0, width), random.randint(0, height)),
            ],
            fill=(
                random.randint(140, 200),
                random.randint(140, 200),
                random.randint(180, 230),
            ),
            width=1,
        )
    for i, ch in enumerate(code):
        draw.text(
            (12 + i * 28, random.randint(4, 12)),
            ch,
            font=font,
            fill=(
                random.randint(20, 90),
                random.randint(20, 90),
                random.randint(80, 140),
            ),
        )
    for _ in range(80):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(80, 180), random.randint(80, 180), random.randint(80, 180)),
        )

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
