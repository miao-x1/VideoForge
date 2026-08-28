"""统一日志配置。"""
from __future__ import annotations

import logging

from .config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("ai_video_agent")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    return logger


logger = setup_logging()
