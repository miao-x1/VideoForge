"""ComfyUI Cloud Service:云端 Workflow 执行的统一客户端。

职责(全项目唯一允许直接请求 ComfyUI 的地方):
  - 上传输入文件(POST /api/upload/image)
  - 提交 Workflow(POST /api/prompt,payload 为 API Format)
  - 轮询执行状态(GET /api/job/{id}/status)
  - 获取输出(GET /api/history/{id} + GET /api/view)

API Key 仅从环境变量读取(settings.comfy_api_key),禁止进入前端/数据库/Git。

Cloud API(实验性,文档: docs.comfy.org/development/cloud/api-reference):
  Base: https://cloud.comfy.org   Auth: X-API-Key header
  终态: success | error | non_retryable_error | lost | cancelled
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import InsufficientBalanceError, ProviderError
from app.core.logging import logger

_POLL_INTERVAL = 5.0
_POLL_TIMEOUT = 900.0  # 视频生成最长达 15 分钟

# 输出文件可能的字段名(SaveVideo/SaveImage 及兼容 VHS 的命名)
_OUTPUT_KEYS = ("videos", "video", "images", "gifs")


class ComfyCloudClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.comfy_base_url).rstrip("/")
        self.api_key = api_key or settings.comfy_api_key
        if not self.api_key:
            raise ProviderError(
                "video/comfy", "未配置 COMFY_API_KEY(云端 ComfyUI)", error_code="NOT_CONFIGURED"
            )

    # ---------------------------------------------------------------- HTTP 基础
    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        form: tuple | None = None,
        timeout: float = 60.0,
    ) -> dict | bytes:
        url = f"{self.base_url}{path}"
        headers = {"X-API-Key": self.api_key}
        data = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        elif form is not None:
            filename, content = form
            boundary = "----videoforge-boundary-7d1a2c"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
            data = body
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
            self._raise_http_error(e.code, detail)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ProviderError(
                "video/comfy", f"云端 ComfyUI 不可达: {e}", error_code="COMFY_UNAVAILABLE"
            ) from e
        return raw

    @staticmethod
    def _raise_http_error(code: int, detail: str) -> None:
        if code in (401, 403):
            raise ProviderError("video/comfy", f"API Key 无效 (HTTP {code})", error_code="INVALID_API_KEY")
        if code == 402:
            raise InsufficientBalanceError("video/comfy", f"云端额度不足: {detail[:200]}")
        if code == 404:
            raise ProviderError("video/comfy", f"资源不存在: {detail[:200]}", error_code="NOT_FOUND")
        if code == 429:
            raise ProviderError("video/comfy", "请求被限流", error_code="RATE_LIMITED")
        raise ProviderError("video/comfy", f"HTTP {code}: {detail[:200]}", error_code="HTTP_ERROR")

    @staticmethod
    def _json(raw: bytes) -> dict:
        return json.loads(raw.decode("utf-8"))

    # ---------------------------------------------------------------- 对外接口
    def upload_image(self, image_path: str) -> str:
        """上传输入图片,返回云端文件名(供 LoadImage 节点引用)。"""
        path = Path(image_path)
        if not path.exists():
            raise ProviderError("video/comfy", f"输入图片不存在: {image_path}", error_code="INPUT_NOT_FOUND")
        raw = self._request(
            "POST", "/api/upload/image", form=(path.name, path.read_bytes()),
        )
        resp = self._json(raw)
        name = resp.get("name")
        if not name:
            raise ProviderError("video/comfy", f"上传响应缺少文件名: {resp}", error_code="UPLOAD_FAILED")
        logger.info("ComfyUI 输入上传: %s → %s", path.name, name)
        return name

    def submit(self, prompt: dict) -> str:
        """提交 Workflow(API Format),返回 prompt_id。"""
        raw = self._request("POST", "/api/prompt", json_body={"prompt": prompt})
        resp = self._json(raw)
        if resp.get("error") or resp.get("node_errors"):
            raise ProviderError(
                "video/comfy",
                f"Workflow 校验失败: {str(resp.get('error') or resp.get('node_errors'))[:300]}",
                error_code="WORKFLOW_INVALID",
            )
        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            raise ProviderError("video/comfy", f"提交失败无 prompt_id: {resp}", error_code="SUBMIT_FAILED")
        return prompt_id

    async def poll(self, prompt_id: str) -> None:
        """轮询任务状态直至终态。失败/超时抛 ProviderError。"""
        loop = asyncio.get_running_loop()
        deadline = asyncio.get_event_loop().time() + _POLL_TIMEOUT
        while True:
            raw = await loop.run_in_executor(
                None, lambda: self._request("GET", f"/api/job/{prompt_id}/status")
            )
            status = self._json(raw).get("status", "")
            if status == "success":
                return
            if status in ("error", "non_retryable_error", "lost", "cancelled"):
                raise ProviderError(
                    "video/comfy", f"Workflow 执行失败: {status}", error_code="GENERATION_FAILED"
                )
            if asyncio.get_event_loop().time() > deadline:
                raise ProviderError(
                    "video/comfy", f"轮询超时({_POLL_TIMEOUT:.0f}s)", error_code="POLL_TIMEOUT"
                )
            await asyncio.sleep(_POLL_INTERVAL)

    def fetch_video(self, prompt_id: str) -> bytes:
        """从执行历史取回视频输出(优先视频类输出)。"""
        raw = self._request("GET", f"/api/history/{prompt_id}")
        history = self._json(raw)
        outputs = (history.get(prompt_id) or {}).get("outputs") or {}
        for node_outputs in outputs.values():
            for key in _OUTPUT_KEYS:
                for item in node_outputs.get(key, []):
                    filename = item.get("filename")
                    if not filename:
                        continue
                    query = urllib.parse.urlencode({
                        "filename": filename,
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    })
                    video = self._request("GET", f"/api/view?{query}", timeout=300.0)
                    if isinstance(video, bytes) and video:
                        return video
        raise ProviderError(
            "video/comfy", "执行历史中无视频输出", error_code="NO_OUTPUT"
        )


def get_comfy_client() -> ComfyCloudClient:
    """工厂:按配置返回云端客户端。"""
    return ComfyCloudClient()
