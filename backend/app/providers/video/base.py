"""I2V(图生视频)Provider 基类。

把单张关键帧图片变成 N 秒动态视频片段,让画面里的人物/场景真正"动起来",
突破 Ken Burns 只能缩放平移静态图的局限。

设计取舍:
- 输入: 关键帧图片本地路径 + 文本提示词(描述期望动作/运镜)
- 输出: MP4 文件路径(含真实连续动作)
- 时长参数: 由调用方按 shot.duration 决定,Provider 自行 clamp 到模型支持范围
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class VideoProvider(ABC):
    """图生视频(I2V)Provider 抽象接口。"""

    @abstractmethod
    async def generate(
        self,
        *,
        image_path: str,
        prompt: str,
        save_path: str,
        duration: int = 5,
    ) -> str:
        """根据首帧图片 + 文本提示词生成动态视频片段。

        Args:
            image_path: 关键帧图片本地路径(作为生成视频的首帧)
            prompt: 视频动作/运镜描述(对应 StoryboardShot.video_prompt)
            save_path: 输出 MP4 文件路径
            duration: 目标时长(秒),Provider 自行 clamp 到模型支持范围

        Returns:
            生成的 MP4 文件路径
        """
