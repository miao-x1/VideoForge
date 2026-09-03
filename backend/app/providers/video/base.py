"""视频模型 Provider 抽象接口。

统一 Qwen / MiniMax / Mock 等多模型的调用入口,
业务层(Orchestrator)仅依赖本接口,不出现 if model==xxx 硬编码。
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..base import ModelProvider
from .capabilities import ModelCapabilities


@dataclass
class ModelRequest:
    """视频生成请求(统一入参)。

    image_path 可空:为空时走纯文生视频(T2V)路径,由支持 T2V 的 Provider
    (MiniMax / Comfy / Mock)执行;仅支持 I2V 的 Provider 应拒绝并返回
    MODE_UNSUPPORTED,由失败分析层决策补关键帧或切换模型。
    """

    image_path: Optional[str] = None  # 首帧(I2V/R2V/首尾帧);None=T2V
    prompt: str = ""
    save_path: str = ""
    duration: int = 5
    aspect_ratio: str = "9:16"
    last_frame_path: Optional[str] = None  # 尾帧(首尾帧,模型支持时生效)
    reference_paths: Optional[list[str]] = None  # 参考素材路径(R2V,模型支持时生效)


@dataclass
class ModelResponse:
    """视频生成响应(统一出参)。"""

    video_path: str
    duration: int
    model: str
    task_id: Optional[str] = None


class VideoModelProvider(ModelProvider):
    """视频模型 Provider 抽象基类。

    各模型(Qwen/MiniMax/Mock)实现本接口,
    Orchestrator 通过 get_video_provider() 获取实例,调用 generate() 生成视频。
    """

    provider_type = "video"

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称,如 'wan2.6-i2v-flash' / 'video-01' / 'mock'。"""

    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """模型能力描述。"""

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """根据首帧图片 + 文本提示词生成动态视频片段。

        Args:
            request: 统一视频生成请求(ModelRequest)

        Returns:
            ModelResponse: 包含视频路径、时长、模型名等信息
        """
