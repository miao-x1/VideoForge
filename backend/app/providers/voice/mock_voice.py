"""Mock Voice Provider:用标准库生成指定时长的静音 wav 占位。

不依赖系统 TTS 引擎,保证任何环境都能跑通。
未来接真实 TTS(DashScope/Edge-TTS)时仅替换本实现。
"""
from __future__ import annotations

import wave
import struct
import math

from .base import VoiceProvider


def _write_silent_wav(path: str, duration: float, sample_rate: int = 22050) -> None:
    n_samples = int(duration * sample_rate)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # 用零振幅填满
        frames = struct.pack("<" + "h" * n_samples, *([0] * n_samples))
        wf.writeframes(frames)


class MockVoiceProvider(VoiceProvider):
    async def generate(self, *, text: str, save_path: str, duration: int) -> str:
        _write_silent_wav(save_path, float(duration))
        return save_path


def get_voice_provider() -> VoiceProvider:
    return MockVoiceProvider()
