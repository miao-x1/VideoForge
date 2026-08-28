"""Mock Image Provider:用 Pillow 生成纯色占位图+分镜文字。

仅用于第一阶段跑通 Pipeline,未来接 SD/Seedream 时替换实现。
"""
from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFont

from .base import ImageProvider


# 暖色调占位色板
_PALETTE = [
    (45, 74, 99), (99, 60, 45), (60, 80, 55), (80, 60, 90),
    (100, 80, 50), (50, 80, 100),
]


class MockImageProvider(ImageProvider):
    async def generate(self, *, prompt: str, save_path: str, width: int = 1280, height: int = 720) -> str:
        bg = random.choice(_PALETTE)
        img = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)

        # 标题水印
        title = "MOCK IMAGE"
        sub = "AI Video Agent - 占位图"
        try:
            font_title = ImageFont.truetype("arial.ttf", size=64)
            font_sub = ImageFont.truetype("arial.ttf", size=28)
        except OSError:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        # 居中绘制
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, height // 2 - 60), title, fill=(255, 255, 255), font=font_title)

        bbox = draw.textbbox((0, 0), sub, font=font_sub)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, height // 2 + 10), sub, fill=(220, 220, 220), font=font_sub)

        # 把 prompt 截断后画在底部,便于人眼快速对照分镜
        snippet = (prompt[:80] + "...") if len(prompt) > 80 else prompt
        bbox = draw.textbbox((0, 0), snippet, font=font_sub)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, height - 60), snippet, fill=(200, 200, 200), font=font_sub)

        img.save(save_path, "PNG")
        return save_path


def get_image_provider() -> ImageProvider:
    return MockImageProvider()
