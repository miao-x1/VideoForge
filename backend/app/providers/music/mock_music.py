"""Mock Music Provider:生成一段轻柔正弦波的 wav 占位。

避免环境依赖,保证 Pipeline 能跑。后续接真实 BGM 库/生成 API 时替换。
"""
from __future__ import annotations

import wave
import struct
import math

from .base import MusicProvider


def _write_tone_wav(path: str, duration: float, freq: float = 220.0, sample_rate: int = 22050) -> None:
    n_samples = int(duration * sample_rate)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        samples = []
        amp = 2000  # 较小的振幅,作为背景音
        for i in range(n_samples):
            # 简单正弦+缓慢淡入淡出
            env = min(1.0, min(i / sample_rate, (n_samples - i) / sample_rate))
            v = int(amp * env * math.sin(2 * math.pi * freq * (i / sample_rate)))
            samples.append(v)
        frames = struct.pack("<" + "h" * n_samples, *samples)
        wf.writeframes(frames)


class MockMusicProvider(MusicProvider):
    async def generate(self, *, save_path: str, duration: int, mood: str = "light") -> str:
        freq = 196.0 if mood == "light" else 110.0
        _write_tone_wav(save_path, float(duration), freq=freq)
        return save_path


def get_music_provider() -> MusicProvider:
    return MockMusicProvider()
