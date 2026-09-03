"""生成产物自动登记到项目素材库。

任务合成出片后,把成片与镜头图片登记为项目 Asset,
供前端素材库检索/预览。幂等:同 project + file_path 不重复登记。
"""
from __future__ import annotations

import os

from sqlalchemy import select

from ..core.logging import logger
from ..db.database import get_session
from ..db.models import Asset


def _to_media_url(path: str, kind: str) -> str:
    """本地素材路径 → 静态访问 URL(/storage/{kind}/{basename})。"""
    return f"/storage/{kind}/{os.path.basename(path)}"


_MEDIA_TYPES = {
    "images": {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"},
    "videos": {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"},
    "audio": {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"},
}


def _media_type(kind: str, path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _MEDIA_TYPES.get(kind, {}).get(ext, "application/octet-stream")


def _add_asset(session, *, user_id: str, project_id: str, name: str, asset_type: str,
               file_path: str, media_type: str, description: str = "") -> bool:
    exists = session.scalar(
        select(Asset).where(Asset.file_path == file_path, Asset.project_id == project_id)
    )
    if exists:
        return False
    session.add(Asset(
        user_id=user_id,
        project_id=project_id,
        name=name,
        asset_type=asset_type,
        description=description,
        file_path=file_path,
        media_type=media_type,
    ))
    return True


def register_generated_assets(state) -> int:
    """成片 + 镜头图片 → 项目素材库(幂等)。返回新增数量;失败不阻塞主流程。"""
    project_id = getattr(state, "project_id", None)
    if not project_id or not getattr(state, "user_id", None):
        return 0
    added = 0
    try:
        with get_session() as session:
            # 成片
            if state.video_path:
                url = _to_media_url(state.video_path, "videos")
                if _add_asset(
                    session,
                    user_id=state.user_id, project_id=project_id,
                    name=f"成片 {os.path.basename(state.video_path)}",
                    asset_type="video", file_path=url,
                    media_type=_media_type("videos", state.video_path),
                    description="任务生成的成片视频",
                ):
                    added += 1
            # 镜头图片(角色/场景视觉锚点,可作后续参考)
            if state.storyboard:
                for idx, shot in enumerate(state.storyboard.shots or []):
                    img = getattr(shot, "image_path", None)
                    if not img:
                        continue
                    url = _to_media_url(img, "images")
                    if _add_asset(
                        session,
                        user_id=state.user_id, project_id=project_id,
                        name=f"镜头 {idx + 1} 图片",
                        asset_type="image", file_path=url,
                        media_type=_media_type("images", img),
                        description=f"第 {idx + 1} 个镜头的生成图片",
                    ):
                        added += 1
            session.commit()
        if added:
            logger.info("项目素材登记: project=%s 新增 %d 项", project_id, added)
    except Exception as e:  # noqa: BLE001
        logger.warning("项目素材登记失败(不影响产物): %s", e)
    return added
