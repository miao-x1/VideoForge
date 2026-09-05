"""MiniMax 视频模型 Provider(H3 直连,V2 API)。

通过 MiniMax 官方直连 API 调用 MiniMax-H3 / MiniMax-H3-Max:
  - 提交: POST {base}/v2/video_generation(content 多模态数组: text + image_url)
  - 轮询: GET  {base}/v2/query/video_generation/{task_id}
  - 下载: task.content.url(官方 CDN 直链,无需 files/retrieve)

计费: pay-as-you-go,按输出秒计费(768P $0.08/s, 2K $0.13/s)。
Base URL 可配置: 国际 https://api.minimax.io / 国内 https://api.minimax.cn。
"""
from __future__ import annotations

import asyncio
import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from ...core.config import settings
from ...core.exceptions import InsufficientBalanceError, ProviderError
from ...core.logging import logger
from .base import ModelRequest, ModelResponse, VideoModelProvider
from .capabilities import ModelCapabilities

_POLL_INTERVAL = 5.0
_POLL_TIMEOUT = 900.0  # 15 分钟,与云端生成上限对齐

# H3 支持的输出时长(整数 4~15 秒)
_DURATION_MIN, _DURATION_MAX = 4, 15


def _parse_v2_error(resp: dict) -> ProviderError | None:
    """解析 V2 错误响应 {"type":"error","error":{"type","message","http_code"}}。"""
    err = resp.get("error")
    if not isinstance(err, dict):
        return None
    etype = str(err.get("type", ""))
    msg = str(err.get("message", ""))
    if "insufficient_balance" in etype:
        return InsufficientBalanceError("video/minimax", msg)
    if "authorized" in etype or "authentication" in etype:
        return ProviderError("video/minimax", f"API Key 无效: {msg}", error_code="INVALID_API_KEY")
    if "rate" in etype:
        return ProviderError("video/minimax", f"请求被限流: {msg}", error_code="RATE_LIMITED")
    return ProviderError("video/minimax", msg, error_code="MINIMAX_ERROR")


class MiniMaxVideoProvider(VideoModelProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.minimax_api_key
        if not self.api_key:
            raise RuntimeError("MiniMax 视频生成缺少 API Key")
        self._model = model or settings.minimax_video_model or "MiniMax-H3"
        self.base_url = (base_url or settings.minimax_base_url).rstrip("/")

    @property
    def name(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_duration=15,
            supported_ratios=["9:16", "16:9", "1:1", "4:3", "3:4"],
            max_resolution="2K",
            quality_score=9.5,
            speed_score=7,
            cost_per_sec=0.08,
            supports_image_input=True,
            supports_video_input=True,
            supports_audio_output=True,
            supports_first_frame=True,
            supports_last_frame=True,
            supports_motion_control=True,
        )

    # ---------------------------------------------------------------- HTTP
    def _request(self, method: str, path: str, *, json_body: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                perr = _parse_v2_error(json.loads(body_text))
                if perr:
                    raise perr from None
            except (json.JSONDecodeError, ValueError):
                pass
            if e.code == 402:
                raise InsufficientBalanceError("video/minimax", f"账户余额不足: {body_text[:200]}") from e
            if e.code == 401:
                raise ProviderError("video/minimax", "API Key 无效", error_code="INVALID_API_KEY") from e
            if e.code == 429:
                raise ProviderError("video/minimax", "请求被限流", error_code="RATE_LIMITED") from e
            raise ProviderError(
                "video/minimax", f"HTTP {e.code}: {body_text[:200] or e.reason}", error_code="HTTP_ERROR"
            ) from e

    # ---------------------------------------------------------------- 生成
    async def generate(self, request: ModelRequest) -> ModelResponse:
        content: list[dict] = [{"type": "text", "text": request.prompt}]
        if request.image_path:
            data_uri = await asyncio.to_thread(self._encode_image, request.image_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
                "role": "first_frame",
            })
        if request.last_frame_path:
            # 首尾帧 I2V:H3 原生支持 last_frame role
            data_uri = await asyncio.to_thread(self._encode_image, request.last_frame_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
                "role": "last_frame",
            })
        for ref in request.reference_paths or []:
            # 参考素材(R2V):角色一致性/风格/场景参考
            data_uri = await asyncio.to_thread(self._encode_image, ref)
            content.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
                "role": "reference",
            })

        duration = max(_DURATION_MIN, min(_DURATION_MAX, int(round(request.duration))))
        body = {
            "model": self._model,
            "content": content,
            "resolution": "768P",
            "duration": duration,
            "ratio": request.aspect_ratio or "16:9",
        }
        logger.info(
            "MiniMax 视频提交: model=%s dur=%ds ratio=%s img=%s last_frame=%s refs=%d",
            self._model, duration, body["ratio"], bool(request.image_path),
            bool(request.last_frame_path), len(request.reference_paths or []),
        )

        resp = await asyncio.to_thread(self._request, "POST", "/v2/video_generation", json_body=body)
        perr = _parse_v2_error(resp)
        if perr:
            raise perr
        task_id = resp.get("task_id")
        if not task_id:
            raise ProviderError("video/minimax", f"视频提交失败,无 task_id: {resp}", error_code="SUBMIT_FAILED")

        video_url = await self._poll(task_id)
        data = await asyncio.to_thread(self._download, video_url)
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(data)
        logger.info("MiniMax 视频已保存: %s (%d bytes)", request.save_path, len(data))
        return ModelResponse(
            video_path=request.save_path, duration=duration, model=self._model, task_id=task_id
        )

    async def _poll(self, task_id: str) -> str:
        """轮询任务直至终态,返回视频下载 URL。"""
        deadline = asyncio.get_event_loop().time() + _POLL_TIMEOUT
        while True:
            r = await asyncio.to_thread(
                self._request, "GET", f"/v2/query/video_generation/{task_id}"
            )
            task = r.get("task") or {}
            status = task.get("status", "")
            logger.debug("MiniMax 视频轮询 status=%s", status)
            if status == "succeeded":
                url = (task.get("content") or {}).get("url", "")
                if not url:
                    raise ProviderError("video/minimax", "任务成功但无视频 URL", error_code="NO_OUTPUT")
                return url
            if status in ("failed", "cancelled"):
                raise ProviderError(
                    "video/minimax", f"视频生成失败: {status} {task.get('error', '')}", error_code="GENERATION_FAILED"
                )
            if asyncio.get_event_loop().time() > deadline:
                raise ProviderError("video/minimax", f"轮询超时({_POLL_TIMEOUT:.0f}s)", error_code="POLL_TIMEOUT")
            await asyncio.sleep(_POLL_INTERVAL)

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """本地图片 → data URI(H3 支持 base64 输入;关键帧 PNG 通常 <2MB,远低于 64MB 限制)。"""
        path = Path(str(image_path).split("?", 1)[0].split("#", 1)[0])
        if not path.is_file():
            raise ProviderError("video/minimax", f"首帧图片不存在：{path.name}", error_code="BAD_IMAGE")
        data = path.read_bytes()
        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    @staticmethod
    def _download(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "videoforge/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
