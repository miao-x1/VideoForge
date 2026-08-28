"""DashScope Qwen-Audio-TTS 语音合成 Provider。

通过 DashScope 非实时 TTS HTTP API 合成真实语音。
复用 LLM_API_KEY(Bearer 鉴权),后端 Python 可直接调用。

调用流程:
  POST SpeechSynthesizer → JSON 含 output.audio.url → 下载 WAV → 保存

模型: qwen-audio-3.0-tts-flash(快、免费额度内可用)
音色: longanhuan_v3.6(Qwen-Audio-TTS 系统音色,中文女声)

注:CosyVoice 系列模型(cosyvoice-v2 等)当前报 Arrearage(需单独开通计费),
Qwen-Audio-TTS 系列可用同一把 Key 直接调用。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.parse
import urllib.request

from ...core.config import settings
from .base import VoiceProvider

logger = logging.getLogger("ai_video_agent")

_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
_DEFAULT_MODEL = "qwen-audio-3.0-tts-flash"
_DEFAULT_VOICE = "longanhuan_v3.6"


class DashScopeVoiceProvider(VoiceProvider):
    """Qwen-Audio-TTS 真实语音合成。"""

    def __init__(self) -> None:
        self._api_key = settings.llm_api_key
        self._model = getattr(settings, "tts_model", None) or _DEFAULT_MODEL
        self._voice = getattr(settings, "tts_voice", None) or _DEFAULT_VOICE
        if not self._api_key:
            raise RuntimeError("LLM_API_KEY 未配置,DashScope TTS 不可用")

    async def generate(self, *, text: str, save_path: str, duration: int) -> str:  # noqa: ARG002
        """将 text 合成为语音 WAV 并保存到 save_path。"""
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

        def _synth() -> str:
            body = json.dumps({
                "model": self._model,
                "input": {"text": text, "voice": self._voice},
                "parameters": {"format": "wav", "sample_rate": 22050},
            }).encode("utf-8")
            req = urllib.request.Request(
                _TTS_URL, data=body, method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())

            audio_url = result.get("output", {}).get("audio", {}).get("url", "")
            if not audio_url:
                raise RuntimeError(f"TTS 未返回音频 URL: {result}")

            audio_data = urllib.request.urlopen(audio_url, timeout=60).read()
            with open(save_path, "wb") as f:
                f.write(audio_data)

            return save_path

        path = await asyncio.to_thread(_synth)
        size = os.path.getsize(path)
        logger.info("DashScope TTS 已保存: %s (%d bytes)", path, size)
        return path
