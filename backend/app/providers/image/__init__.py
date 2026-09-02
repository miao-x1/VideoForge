"""Image Provider 工厂:按 settings.image_provider 返回对应实现。

新增真实 Provider 步骤:
1. 在本包新增 xxx_image.py 实现 ImageProvider
2. 在 core/config.py 的 image_provider Literal 里加入对应字面量
3. 在下方 get_image_provider() 加分发分支
Agent / Orchestrator 无需改动。
"""
from __future__ import annotations

from ...core.config import settings
from ...core.logging import logger
from .base import ImageProvider
from .mock_image import MockImageProvider


def get_image_provider() -> ImageProvider:
    if settings.image_provider == "dashscope":
        try:
            from .dashscope_image import DashScopeImageProvider
            return DashScopeImageProvider()
        except Exception as e:  # 导入或初始化失败时回退 mock,保证 Pipeline 不崩
            logger.warning("DashScope Image Provider 初始化失败,回退 Mock: %s", e)
            return MockImageProvider()
    return MockImageProvider()


__all__ = ["ImageProvider", "get_image_provider"]
