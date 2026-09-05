"""统一日志配置。禁止把 secret / 验证码 / Authorization 写入日志。"""
from __future__ import annotations

import logging
import re

from .config import settings

_REDACT_PATTERN = re.compile(
    r"(?i)(jwt_secret|api[_-]?key|authorization|bearer\s+[A-Za-z0-9\-._~+/]+=*|password=)\S*"
)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if _REDACT_PATTERN.search(msg):
            record.msg = _REDACT_PATTERN.sub("[REDACTED]", msg)
            record.args = ()
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("ai_video_agent")
    if logger.handlers:
        if not any(isinstance(f, RedactingFilter) for h in logger.handlers for f in h.filters):
            for handler in logger.handlers:
                handler.addFilter(RedactingFilter())
        return logger

    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    return logger


logger = setup_logging()
