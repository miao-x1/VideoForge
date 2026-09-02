"""FastAPI 入口。

启动: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.config import STORAGE_ROOT, settings
from .core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("AI Video Agent 启动 (llm=%s)", settings.llm_provider)
    yield
    # shutdown
    logger.info("AI Video Agent 关闭")


app = FastAPI(title="AI Video Agent", version="0.1.0", lifespan=lifespan)

# CORS:允许前端 dev server 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源:让前端能直接播放 storage/videos/*.mp4
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "AI Video Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "provider": {
            "llm": settings.llm_provider,
            "image": settings.image_provider,
            "voice": settings.voice_provider,
            "music": settings.music_provider,
        },
    }
