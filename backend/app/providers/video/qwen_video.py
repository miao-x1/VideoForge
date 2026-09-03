"""Qwen(DashScope)视频模型 Provider。

通过 DashScope 异步 API 调用通义万相 wan2.6-i2v-flash,把关键帧图片变成 N 秒动态视频。
封装 API Key/Endpoint/参数/请求/响应/错误处理/任务查询/视频下载。
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from ...core.config import settings
from ...core.exceptions import InsufficientBalanceError, ProviderError
from ...core.logging import logger
from .base import ModelRequest, ModelResponse, VideoModelProvider
from .capabilities import ModelCapabilities

_MIN_DURATION = 2
_MAX_DURATION = 15
_POLL_MAX_ATTEMPTS = 60
_POLL_INTERVAL = 5.0


def _parse_dashscope_error(resp: dict) -> ProviderError | None:
    """解析 DashScope API 错误响应,返回对应的 ProviderError 子类。"""
    code = (resp.get("code") or "").upper()
    msg = resp.get("message", "")
    if not code:
        return None
    if "INSUFFICIENT" in code or "BALANCE" in code:
        return InsufficientBalanceError("video/qwen", f"{code}: {msg}")
    if "INVALID_API_KEY" in code or "UNAUTHORIZED" in code:
        return ProviderError("video/qwen", f"API Key 无效: {code}: {msg}", error_code="INVALID_API_KEY")
    if "ACCESS_DENIED" in code or "PERMISSION" in code:
        return ProviderError("video/qwen", f"无权访问模型: {code}: {msg}", error_code="ACCESS_DENIED")
    if "THROTTLED" in code or "RATE" in code:
        return ProviderError("video/qwen", f"请求被限流: {code}: {msg}", error_code="RATE_LIMITED")
    return ProviderError("video/qwen", f"{code}: {msg}", error_code="DASHSCOPE_ERROR")


class QwenVideoProvider(VideoModelProvider):
    def __init__(self) -> None:
        self.api_key = settings.qwen_api_key or settings.llm_api_key or settings.dashscope_api_key
        if not self.api_key:
            raise RuntimeError("Qwen 视频生成缺少 API Key")
        self._model = settings.qwen_video_model or "wan2.6-i2v-flash"
        self.submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"

    @property
    def name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_duration=_MAX_DURATION,
            supported_ratios=["9:16", "16:9", "1:1"],
            max_resolution="720P",
            quality_score=8,
            speed_score=6,
            cost_per_sec=0.5,
            supports_image_input=True,
            supports_video_input=False,
            supports_audio_output=False,
            # wan2.6-i2v-flash 为纯图生视频模型,不支持 T2V/尾帧
            supports_text_to_video=False,
            supports_first_frame=True,
            supports_last_frame=False,
            supports_negative_prompt=False,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not request.image_path:
            raise ProviderError(
                "video/qwen",
                f"{self._model} 仅支持图生视频(I2V),该镜头缺少首帧关键帧,"
                "请补生成关键帧或切换支持 T2V 的模型",
                error_code="MODE_UNSUPPORTED",
            )
        dur = max(_MIN_DURATION, min(_MAX_DURATION, request.duration))
        img_b64 = await asyncio.to_thread(self._encode_image, request.image_path)
        body = json.dumps(
            {
                "model": self._model,
                "input": {"prompt": request.prompt, "img_url": img_b64},
                "parameters": {"resolution": "720P", "duration": dur},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        logger.info("Qwen 视频提交: model=%s dur=%ss img=%s", self._model, dur, os.path.basename(request.image_path))

        def _submit() -> dict:
            req = urllib.request.Request(self.submit_url, data=body, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
                try:
                    err_resp = json.loads(body_text)
                    perr = _parse_dashscope_error(err_resp)
                    if perr:
                        raise perr from None
                except (json.JSONDecodeError, ValueError):
                    pass
                raise ProviderError("video/qwen", f"HTTP {e.code}: {body_text or e.reason}", error_code="HTTP_ERROR") from e

        resp = await asyncio.to_thread(_submit)

        # 检查提交响应中的错误
        perr = _parse_dashscope_error(resp)
        if perr:
            raise perr

        task_id = (resp.get("output") or {}).get("task_id")
        if not task_id:
            raise ProviderError("video/qwen", f"视频提交失败,无 task_id: {resp}", error_code="SUBMIT_FAILED")

        video_url = await self._poll(task_id)
        data = await asyncio.to_thread(self._download, video_url)
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(request.save_path, "wb") as f:
            f.write(data)
        logger.info("Qwen 视频已保存: %s (%d bytes)", request.save_path, len(data))
        return ModelResponse(video_path=request.save_path, duration=dur, model=self._model, task_id=task_id)

    @staticmethod
    def _encode_image(image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = "jpeg" if ext in ("jpg", "jpeg") else "png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/{mime};base64,{b64}"

    async def _poll(self, task_id: str) -> str:
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for attempt in range(_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL)

            def _query() -> dict:
                req = urllib.request.Request(task_url, headers={"Authorization": f"Bearer {self.api_key}"})
                try:
                    with urllib.request.urlopen(req, timeout=30) as r:
                        return json.loads(r.read())
                except urllib.error.HTTPError as e:
                    body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
                    try:
                        err_resp = json.loads(body_text)
                        perr = _parse_dashscope_error(err_resp)
                        if perr:
                            raise perr from None
                    except (json.JSONDecodeError, ValueError):
                        pass
                    raise ProviderError("video/qwen", f"轮询 HTTP {e.code}: {body_text or e.reason}", error_code="HTTP_ERROR") from e

            r = await asyncio.to_thread(_query)
            out = r.get("output") or {}
            status = out.get("task_status")
            logger.debug("Qwen 视频轮询[%d/%d] status=%s", attempt + 1, _POLL_MAX_ATTEMPTS, status)
            if status == "SUCCEEDED":
                url = out.get("video_url")
                if not url:
                    raise ProviderError("video/qwen", f"视频成功但无 video_url: {r}", error_code="NO_VIDEO_URL")
                return url
            if status == "FAILED":
                # 解析失败原因
                perr = _parse_dashscope_error(r)
                if perr:
                    raise perr
                err_msg = out.get("message", "未知原因")
                raise ProviderError("video/qwen", f"视频生成失败: {err_msg}", error_code="GENERATION_FAILED")
        raise ProviderError("video/qwen", f"轮询超时({_POLL_MAX_ATTEMPTS * _POLL_INTERVAL}s)", error_code="POLL_TIMEOUT")

    @staticmethod
    def _download(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-video-agent/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
