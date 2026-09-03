"""视频模型 Provider 工厂。

根据 settings.video_model_provider 切换 qwen / minimax。
生产环境禁止 mock，mock 仅在 APP_ENV=test 且 ENABLE_MOCK_PROVIDERS=true 时可用。
向后兼容:旧 i2v_provider=dashscope 自动映射到 qwen。
"""
from __future__ import annotations

import importlib

from ...core.config import settings
from ...core.exceptions import ProviderNotConfiguredError
from ...core.logging import logger
from .base import VideoModelProvider


def _is_mock_allowed() -> bool:
    return settings.app_env == "test" and settings.enable_mock_providers


def get_video_provider(provider: str | None = None) -> VideoModelProvider:
    """返回视频模型 Provider 实例。

    Args:
        provider: 可选,覆盖配置中的 provider 选择(用于 preferred_model)
    """
    # 测试模式显式配置 mock 时,路由覆盖不应切换回真实 Provider
    if _is_mock_allowed() and settings.video_model_provider == "mock":
        choice = "mock"
    elif provider:
        choice = provider
    else:
        choice = settings.video_model_provider
        # 向后兼容:未配置新字段但旧 i2v_provider=dashscope → qwen
        # (仅生产环境兜底;测试模式显式 mock 不应被覆盖)
        if choice == "mock" and settings.i2v_provider == "dashscope" and not _is_mock_allowed():
            choice = "qwen"

    if choice == "qwen":
        if not (settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key):
            raise ProviderNotConfiguredError("video/qwen", "未配置 Qwen API Key")
        from .qwen_video import QwenVideoProvider
        logger.info("视频模型: qwen (%s)", settings.qwen_video_model)
        return QwenVideoProvider()

    if choice == "minimax":
        if not settings.minimax_api_key:
            raise ProviderNotConfiguredError("video/minimax", "未配置 MINIMAX_API_KEY")
        from .minimax_video import MiniMaxVideoProvider
        logger.info("视频模型: minimax (%s)", settings.minimax_video_model)
        return MiniMaxVideoProvider()

    if choice == "comfy":
        if not settings.comfy_api_key:
            raise ProviderNotConfiguredError("video/comfy", "未配置 COMFY_API_KEY (云端 ComfyUI)")
        from .comfy_video import ComfyVideoProvider
        logger.info("视频模型: comfy (MiniMax H3 官方 Workflow)")
        return ComfyVideoProvider()

    if choice == "mock":
        if not _is_mock_allowed():
            raise ProviderNotConfiguredError(
                "video/mock",
                "video_model_provider=mock 但当前为生产环境 (APP_ENV=production)。",
            )
        from .mock_video import MockVideoProvider
        logger.warning("视频模型: mock (测试模式)")
        return MockVideoProvider()

    raise ProviderNotConfiguredError("video", f"未知 video_model_provider: {choice}")


def list_available_models() -> list[dict]:
    """列出所有可用模型及能力描述(供 API /api/models 使用)。"""
    models = []
    for name, cls_name, module_name in [
        ("qwen", "QwenVideoProvider", "app.providers.video.qwen_video"),
        ("minimax", "MiniMaxVideoProvider", "app.providers.video.minimax_video"),
        ("comfy", "ComfyVideoProvider", "app.providers.video.comfy_video"),
    ]:
        try:
            mod = importlib.import_module(module_name)
            cls = getattr(mod, cls_name)
            inst = cls()
            caps = inst.capabilities
            models.append({
                "provider": name,
                "model": inst.name,
                "capabilities": caps.to_dict(),
            })
        except Exception as e:
            logger.debug("模型 %s 不可用: %s", name, e)

    # 测试模式下额外列出 mock
    if _is_mock_allowed():
        try:
            from .mock_video import MockVideoProvider
            inst = MockVideoProvider()
            models.append({
                "provider": "mock",
                "model": inst.name,
                "capabilities": inst.capabilities.to_dict(),
            })
        except Exception as e:
            logger.debug("模型 mock 不可用: %s", e)

    return models
