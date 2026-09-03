"""FastAPI 入口。

启动: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.auth_routes import router as auth_router
from .api.routes import router, upload_router
from .api.project_routes import router as project_router
from .core.config import STORAGE_ROOT, settings
from .core.logging import logger
from .db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    _log_provider_status()
    yield
    logger.info("AI Video Agent 关闭")


def _log_provider_status() -> None:
    """启动时输出 Provider 配置状态。"""
    logger.info("=" * 60)
    logger.info("AI Video Agent 启动")
    logger.info("环境: %s (mock=%s)", settings.app_env, settings.enable_mock_providers)
    logger.info("-" * 60)

    providers = [
        ("LLM", settings.llm_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Image", settings.image_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Voice", settings.voice_provider, bool(settings.llm_api_key or settings.dashscope_api_key)),
        ("Music", settings.music_provider, True),  # ambient 不需要 API Key
        ("Video", settings.video_model_provider, bool(settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key)),
    ]
    for name, provider, has_key in providers:
        status = "CONFIGURED" if has_key else "NOT CONFIGURED"
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

# CORS:优先使用配置的允许来源,未配置时回退允许全部(开发模式)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

app.include_router(auth_router)
app.include_router(router)
app.include_router(upload_router)
app.include_router(project_router)


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
