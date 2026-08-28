"""Seedream 文生图 Provider。

通过 Trae 暴露的 text-to-image HTTP 端点调用 Seedream 模型。

⚠️ 已知限制:
  该端点(https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image)在
  后端 Python 进程裸调时,无论 prompt 如何变化都返回同一张占位图
  (实测 3 个不同 prompt,返回字节 MD5 完全一致)。
  端点需要 TRAE agent 内部鉴权上下文才能产出真实按 prompt 变化的图。

真实 Seedream 出图方式:
  在 TRAE 对话中用 GenerateImage 工具(Seedream 插件提供)按 prompt
  生成 JPG,再用 PIL 转 PNG 覆盖到分镜路径,最后用
  `python tests/reassemble.py` 复用已有音频+BGM 重新合成 MP4。

Pipeline 运行时本 Provider 仍会产出占位图(保证流程不崩),
真实出图需 agent 介入。后续若需全自动,可切到 DashScope 通义万相
(见 dashscope_image.py,复用 LLM_API_KEY 调 wan2.1-t2i-turbo)。
"""
from __future__ import annotations

import asyncio
import io
import urllib.parse
import urllib.request

from PIL import Image

from ...core.logging import logger
from .base import ImageProvider


_SEEDREAM_URL = "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image"

# Seedream 端点支持的预设比例
_SIZE_MAP = {
    (1280, 720): "landscape_16_9",
    (720, 1280): "portrait_16_9",
    (1024, 1024): "square_hd",
}


class SeedreamImageProvider(ImageProvider):
    async def generate(self, *, prompt: str, save_path: str, width: int = 1280, height: int = 720) -> str:
        image_size = _SIZE_MAP.get((width, height), "landscape_16_9")
        params = urllib.parse.urlencode({"prompt": prompt, "image_size": image_size})
        url = f"{_SEEDREAM_URL}?{params}"
        logger.info("Seedream 文生图: %s (%s)", prompt[:60], image_size)

        def _fetch() -> bytes:
            req = urllib.request.Request(url, headers={"User-Agent": "ai-video-agent/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()

        data = await asyncio.to_thread(_fetch)
        if not data:
            raise RuntimeError("Seedream 返回空数据")

        img = Image.open(io.BytesIO(data)).convert("RGB")
        # 统一到目标分辨率,保证分镜图尺寸一致
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
        img.save(save_path, "PNG")
        logger.info("Seedream 图片已保存: %s (%d bytes)", save_path, len(data))
        return save_path
