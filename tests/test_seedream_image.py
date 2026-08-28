"""Seedream 文生图单图测试。

直接运行: python tests/test_seedream_image.py
验证: SeedreamImageProvider 能下载真实 AI 图片并保存为 PNG。
"""
from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.core.config import storage_dir  # noqa: E402
from app.providers.image.seedream_image import SeedreamImageProvider  # noqa: E402


async def main() -> None:
    p = SeedreamImageProvider()
    out = os.path.join(str(storage_dir("images")), "_seedream_test.png")
    await p.generate(
        prompt="Tang Dynasty scholar in silk robe holding a glowing smartphone, "
               "cinematic lighting, humorous, detailed illustration",
        save_path=out,
        width=1280,
        height=720,
    )
    size = os.path.getsize(out)
    print(f"[img] 通过 -> {out} ({size} bytes)")
    assert size > 10000, "图片过小,可能不是真实图片"
    print("[img] Seedream 文生图实测通过 ✅")


if __name__ == "__main__":
    asyncio.run(main())
