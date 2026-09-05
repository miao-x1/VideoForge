"""统一 Asset 类型。asset_type 是业务种类，mime_type 是文件 MIME。"""
from __future__ import annotations

ASSET_TYPES = (
    "image",
    "video",
    "audio",
    "3d_model",
    "reference_image",
    "thumbnail",
    "other",
)

_ALIASES = {
    "img": "image",
    "image": "image",
    "picture": "image",
    "pic": "image",
    "photo": "image",
    "video": "video",
    "audio": "audio",
    "voice": "audio",
    "music": "audio",
    "3d": "3d_model",
    "3d_model": "3d_model",
    "model": "3d_model",
    "glb": "3d_model",
    "gltf": "3d_model",
    "reference": "reference_image",
    "reference_image": "reference_image",
    "thumbnail": "thumbnail",
    "thumb": "thumbnail",
    "poster": "thumbnail",
    "preview": "thumbnail",
    "person": "other",
    "scene": "other",
    "object": "other",
    "style": "other",
}

_EXT_TYPE = {
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".bmp": "image",
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
    ".avi": "video",
    ".mkv": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".glb": "3d_model",
    ".gltf": "3d_model",
}

_EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
}

ALLOWED_EXTENSIONS = set(_EXT_TYPE)

_MIME_TO_MEDIA = {
    "image": "image",
    "video": "video",
    "audio": "audio",
    "3d_model": "model",
    "reference_image": "image",
    "thumbnail": "image",
    "other": "other",
}


def normalize_asset_type(value: str | None, *, filename: str = "") -> str:
    raw = (value or "").strip().lower()
    if raw in _ALIASES:
        return _ALIASES[raw]
    from pathlib import Path

    ext = Path(filename or "").suffix.lower()
    if ext in _EXT_TYPE:
        return _EXT_TYPE[ext]
    return "other"


def media_kind(asset_type: str) -> str:
    return _MIME_TO_MEDIA.get(asset_type, "other")[:16]


def mime_for_filename(filename: str, fallback: str = "application/octet-stream") -> str:
    from pathlib import Path

    return _EXT_MIME.get(Path(filename or "").suffix.lower(), fallback)


def safe_extension(filename: str) -> str:
    from pathlib import Path

    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ext
    return ""
