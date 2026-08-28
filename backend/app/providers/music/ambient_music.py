"""程序化 Ambient 背景音乐 Provider。

用 numpy 生成带和弦进行的 ambient pad,比 Mock 的单一正弦波更接近真实 BGM。
无需外部 API,零依赖(仅 numpy + wave),适合 MVP 稳定自动化。

特点:
- 4 小节和弦循环(根据 mood 选调式)
- 每个音叠加 root+fifth+octave,微 detune 增加厚度
- 慢 attack/release 包络,柔和起伏
- 和弦间 crossfade,无突变
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import struct
import wave

import numpy as np

from .base import MusicProvider

logger = logging.getLogger("ai_video_agent")

_SR = 22050  # 采样率

# mood → 和弦频率组(root, fifth, octave,高一八度root),单位 Hz
_CHORDS = {
    "light": [
        (261.63, 392.00, 523.25, 587.33),   # C-G-C-D
        (392.00, 293.66, 587.33, 440.00),   # G-D-G-A
        (329.63, 440.00, 659.25, 523.25),   # E-A-E-C
        (349.23, 261.63, 523.25, 392.00),   # F-C-F-G
    ],
    "emotional": [
        (220.00, 329.63, 440.00, 523.25),   # Am-E-A-C
        (261.63, 349.23, 523.25, 440.00),   # C-F-C-A
        (349.23, 440.00, 698.46, 523.25),   # F-A-F-C
        (329.63, 392.00, 659.25, 493.88),   # E-G-E-B
    ],
    "tense": [
        (196.00, 293.66, 392.00, 466.16),   # G-D-G-Bb
        (220.00, 329.63, 440.00, 523.25),   # A-E-A-C
        (233.08, 349.23, 466.16, 587.33),   # Bb-F-Bb-D
        (196.00, 293.66, 392.00, 466.16),   # G-D-G-Bb
    ],
}


class AmbientMusicProvider(MusicProvider):
    """程序化生成 ambient pad 背景音乐。"""

    async def generate(self, *, save_path: str, duration: int, mood: str = "light") -> str:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        path = await asyncio.to_thread(self._render, save_path, duration, mood)
        size = os.path.getsize(path)
        logger.info("Ambient BGM 已保存: %s (%d bytes)", path, size)
        return path

    def _render(self, save_path: str, duration: int, mood: str) -> str:
        chords = _CHORDS.get(mood, _CHORDS["light"])
        total_samples = int(_SR * max(duration, 4))
        buf = np.zeros(total_samples, dtype=np.float32)

        chord_beats = max(1, len(chords))
        beat_len = total_samples // chord_beats

        for i, chord in enumerate(chords):
            start = i * beat_len
            end = min(start + beat_len, total_samples)
            n = end - start
            if n <= 0:
                continue
            t = np.arange(n, dtype=np.float32) / _SR
            # 叠加 root+fifth+octave,微 detune
            tone = np.zeros(n, dtype=np.float32)
            for j, freq in enumerate(chord):
                detune = 1.0 + (j * 0.002)  # 轻微 detune 增加厚度
                tone += np.sin(2 * np.pi * freq * detune * t) * 0.25
            # 慢 attack/release 包络
            env = np.ones(n, dtype=np.float32)
            atk = min(n // 4, _SR)  # 1 秒 attack
            rel = min(n // 4, _SR)  # 1 秒 release
            env[:atk] = np.linspace(0, 1, atk, dtype=np.float32)
            env[-rel:] = np.linspace(1, 0, rel, dtype=np.float32)
            buf[start:end] += tone * env * 0.5

        # 简单移动平均"低通",让声音更柔和
        kernel = 8
        if len(buf) > kernel:
            buf = np.convolve(buf, np.ones(kernel, dtype=np.float32) / kernel, mode="same")

        # 归一化 + fade in/out 全曲
        peak = np.max(np.abs(buf)) or 1.0
        buf = buf / peak * 0.7
        fi = min(_SR, len(buf) // 4)
        fo = min(_SR, len(buf) // 4)
        buf[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        buf[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)

        # 转 16-bit PCM 写 WAV
        pcm = (buf * 32767).clip(-32768, 32767).astype(np.int16)
        with wave.open(save_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(_SR)
            w.writeframes(pcm.tobytes())

        return save_path
