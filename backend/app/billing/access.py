"""出片时解析 Key 并预扣平台余额。失败退回。"""
from __future__ import annotations

from ..generation.router import generate_video
from .service import refund_reservation, reserve_video_access


async def run_charged_video(db, user_id: str, **generate_kwargs) -> dict:
    duration = int(generate_kwargs.get("duration") or 5)
    access = await reserve_video_access(db, user_id, duration)
    await db.commit()
    try:
        return await generate_video(
            **generate_kwargs,
            provider_name=access.provider,
            api_key=access.api_key,
            base_url=access.base_url or None,
            model=access.model or None,
        )
    except Exception:
        await refund_reservation(db, user_id, access)
        await db.commit()
        raise
