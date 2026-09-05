"""Generation Router：选择已有 Image / Video Provider，不在 Agent 里写死 API。"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from ..core.config import STORAGE_ROOT, settings, storage_dir
from ..core.logging import logger
from ..providers.image import get_image_provider
from ..providers.video import get_video_provider
from ..providers.video.base import ModelRequest


def public_url(path: str) -> str:
    p = Path(path).resolve()
    try:
        rel = p.relative_to(STORAGE_ROOT.resolve())
        return f"/storage/{rel.as_posix()}"
    except ValueError:
        return f"/storage/{p.name}"


def local_path_from_url(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if raw.startswith("data:"):
        return None
    raw = raw.split("?", 1)[0].split("#", 1)[0]
    if "access_token=" in raw:
        raw = raw.split("access_token=", 1)[0].rstrip("?&")
    for prefix in (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
            break
    raw = raw.replace("\\", "/")
    if raw.startswith("/storage/"):
        path = STORAGE_ROOT / raw[len("/storage/") :]
        return str(path) if path.is_file() else None
    if raw.startswith("storage/"):
        path = STORAGE_ROOT / raw[len("storage/") :]
        return str(path) if path.is_file() else None
    p = Path(raw)
    return str(p) if p.is_file() else None


async def generate_image(*, prompt: str, width: int | None = None, height: int | None = None) -> dict[str, Any]:
    provider = get_image_provider()
    generation_id = uuid.uuid4().hex[:16]
    dest = storage_dir("director/generations") / f"{generation_id}.png"
    w = width or settings.video_width
    h = height or settings.video_height
    logger.info("Director generate_image id=%s model=%s", generation_id, getattr(provider, "model", provider.__class__.__name__))
    path = await provider.generate(prompt=prompt, save_path=str(dest), width=w, height=h)
    return {
        "generation_id": generation_id,
        "kind": "image",
        "path": path,
        "url": public_url(path),
        "model": getattr(provider, "model", settings.image_model),
        "prompt": prompt,
        "status": "ok",
    }


async def generate_video(
    *,
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    image_path: str | None = None,
    last_frame_path: str | None = None,
    reference_paths: list[str] | None = None,
    provider_name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    provider = get_video_provider(provider_name, api_key=api_key, base_url=base_url, model=model)
    generation_id = uuid.uuid4().hex[:16]
    dest = storage_dir("director/generations") / f"{generation_id}.mp4"
    logger.info(
        "Director generate_video id=%s model=%s image=%s",
        generation_id,
        getattr(provider, "name", provider.__class__.__name__),
        bool(image_path),
    )
    resp = await provider.generate(
        ModelRequest(
            image_path=image_path,
            prompt=prompt,
            save_path=str(dest),
            duration=int(duration) or 5,
            aspect_ratio=aspect_ratio or "9:16",
            last_frame_path=last_frame_path,
            reference_paths=reference_paths,
        )
    )
    return {
        "generation_id": generation_id,
        "kind": "video",
        "path": resp.video_path,
        "url": public_url(resp.video_path),
        "model": resp.model,
        "prompt": prompt,
        "duration": resp.duration,
        "status": "ok",
    }
