"""Mock 图生视频(I2V)Provider。

本地测试用,不调用 DashScope,用 moviepy 把输入图片渲染成 N 秒 MP4(含轻微 Ken Burns),
输出格式与真实 I2V Provider 一致,用于 orchestrator/assembly 集成代码的本地验证。

注意: mock 输出的"视频"本质仍是 Ken Burns 静态图,无真实连续动作。
真实效果需切换到 dashscope I2V Provider。
"""
from __future__ import annotations

import os

from moviepy import ImageClip, vfx
from PIL import Image

from ...core.logging import logger
from .base import VideoProvider


class MockI2VProvider(VideoProvider):
    async def generate(
        self,
        *,
        image_path: str,
        prompt: str,
        save_path: str,
        duration: int = 5,
    ) -> str:
        # 输入图片尺寸
        with Image.open(image_path) as im:
            w, h = im.size
        # 轻微 Ken Burns: 1.0 → 1.05 放大,模拟"动态"视频
        clip = ImageClip(image_path, duration=duration)
        clip = clip.with_effects([vfx.Resize(new_size=lambda t: 1.0 + 0.05 * (t / duration))])
        clip = clip.with_position(("center", "center"))
        clip = clip.with_fps(24)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        # 写入 mp4(mock 用低比特率节省空间)
        clip.write_videofile(
            save_path,
            codec="libx264",
            audio=False,
            bitrate="500k",
            preset="ultrafast",
            logger=None,
        )
        clip.close()
        logger.info("Mock I2V 已生成(伪 Ken Burns 5s 视频): %s", save_path)
        return save_path
