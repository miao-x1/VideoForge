"""FastAPI 入口。

启动: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api.auth_routes import router as auth_router
from .api.routes import router, upload_router
from .api.project_routes import router as project_router
from .api.director_character_routes import router as director_character_router
from .api.director_persist_routes import router as director_persist_router
from .api.director_agent_routes import router as director_agent_router
from .api.director_generation_routes import router as director_generation_router
from .api.director_asset_routes import router as director_asset_router
from .api.media_routes import router as media_router
from .api.system_routes import router as system_router
from .api.billing_routes import router as billing_router
from .auth.jwt_handler import verify_token
from .core.config import STORAGE_ROOT, settings
from .core.logging import logger
from .core.security_guard import cors_origin_list, validate_runtime_settings
from .db.database import init_db
from .db import models as _db_models  # noqa: F401 — register ORM tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_settings()
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    await init_db()
    _log_provider_status()
    yield
    logger.info("AI Video Agent 关闭")


def _log_provider_status() -> None:
    """启动时输出 Provider 配置状态。不打印任何 secret。"""
    logger.info("=" * 60)
    logger.info("AI Video Agent 启动")
    logger.info("环境: %s (mock=%s)", settings.app_env, settings.enable_mock_providers)
    logger.info("-" * 60)

    providers = [
        ("LLM", settings.llm_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Image", settings.image_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Voice", settings.voice_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Music", settings.music_provider, True),
        ("Video", settings.video_model_provider, bool(settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key)),
    ]
    for name, provider, has_key in providers:
        key_status = "API KEY: PRESENT" if has_key else "API KEY: MISSING"
        logger.info("  %s: %s | %s", name, provider, key_status)

    if settings.video_model_provider == "qwen" or (settings.video_model_provider == "mock" and settings.i2v_provider == "dashscope"):
        has_qwen = bool(settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key)
        logger.info("  Qwen Video: %s | model=%s", "CONFIGURED" if has_qwen else "NOT CONFIGURED", settings.qwen_video_model)
    if settings.minimax_api_key:
        logger.info("  MiniMax Video: CONFIGURED | model=%s", settings.minimax_video_model)
    else:
        logger.info("  MiniMax Video: NOT CONFIGURED (no API key)")

    if not settings.enable_mock_providers:
        logger.info("-" * 60)
        logger.info("Mock providers disabled in production.")
    logger.info("=" * 60)


app = FastAPI(title="AI Video Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    started = time.perf_counter()
    user_id = "-"
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        payload = verify_token(auth.split(" ", 1)[1].strip())
        if payload and payload.get("sub"):
            user_id = str(payload["sub"])
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "request_id=%s user_id=%s %s %s status=%s duration_ms=%s",
        request_id,
        user_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth_router)
app.include_router(router)
app.include_router(upload_router)
app.include_router(project_router)
app.include_router(director_character_router)
app.include_router(director_persist_router)
app.include_router(director_agent_router)
app.include_router(director_generation_router)
app.include_router(director_asset_router)
app.include_router(media_router)
app.include_router(system_router)
app.include_router(billing_router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "AI Video Agent",
        "version": "0.2.0",
        "docs": "/docs",
        "env": settings.app_env,
        "mock_enabled": settings.enable_mock_providers,
        "provider": {
            "llm": settings.llm_provider,
            "image": settings.image_provider,
            "voice": settings.voice_provider,
            "music": settings.music_provider,
            "video": settings.video_model_provider,
        },
    }
