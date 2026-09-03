"""Voice Provider 抽象接口(TTS)。"""
from __future__ import annotations

from abc import abstractmethod

from ..base import ModelProvider


class VoiceProvider(ModelProvider):
    """语音合成(TTS)模型 Provider 抽象(对应任务书 VoiceModelProvider)。"""

    provider_type = "voice"

    @abstractmethod
    async def generate(self, *, text: str, save_path: str, duration: int) -> str:
        """根据 text 生成旁白音频并保存到 save_path,返回保存路径。

        duration 用于在 Mock 实现中生成指定时长的占位音频。
        """


# 任务书语义别名: VoiceModelProvider 即 VoiceProvider
VoiceModelProvider = VoiceProvider
