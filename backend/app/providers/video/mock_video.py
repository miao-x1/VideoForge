"""Mock 视频模型 Provider。

本地测试用,不调用任何 API:
- I2V(有首帧):用 moviepy 把输入图片渲染成 N 秒 MP4(轻微 Ken Burns)
- T2V(无首帧):生成纯色占位片段,验证纯文生视频路径贯通
输出格式与真实 Provider 一致,用于 orchestrator/assembly 集成验证。
"""
from __future__ import annotations

import os

from PIL import Image

from ...core.config import settings
from ...core.logging import logger
from .base import ModelRequest, ModelResponse, VideoModelProvider
from .capabilities import ModelCapabilities


class MockVideoProvider(VideoModelProvider):
    @property
    def name(self) -> str:
        return "mock"

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_duration=60,
            quality_score=3,
            speed_score=10,
            cost_per_sec=0.0,
            supports_text_to_video=True,
            supports_negative_prompt=True,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        from moviepy import ColorClip, ImageClip, vfx

        os.makedirs(os.path.dirname(request.save_path), exist_ok=True)
        if request.image_path and os.path.exists(request.image_path):
            with Image.open(request.image_path) as im:
                w, h = im.size
            clip = ImageClip(request.image_path, duration=request.duration)
            clip = clip.with_effects([vfx.Resize(new_size=lambda t: 1.0 + 0.05 * (t / request.duration))])
            clip = clip.with_position(("center", "center"))
            kind = "伪 Ken Burns(I2V)"
        else:
            # T2V 占位:深灰纯色片段(尺寸跟随配置,无外部依赖)
            w, h = settings.video_width, settings.video_height
            clip = ColorClip(size=(w, h), color=(42, 42, 48), duration=request.duration)
            kind = "纯色占位(T2V)"
        clip = clip.with_fps(24)
        clip.write_videofile(
            request.save_path,
            codec="libx264",
            audio=False,
            bitrate="500k",
            preset="ultrafast",
            logger=None,
        )
        clip.close()
        logger.info("Mock 视频已生成(%s %ds): %s", kind, request.duration, request.save_path)
        return ModelResponse(
            video_path=request.save_path,
            duration=request.duration,
            model=self.name,
        )
