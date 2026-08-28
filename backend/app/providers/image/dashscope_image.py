"""DashScope 通义万相文生图 Provider。

通过 DashScope 原生异步 API 调用通义万相(wan 系列)模型,真实按 prompt 生成图片。
复用 settings.llm_api_key(同一把 DashScope Key 既能调 LLM 也能调文生图)。

调用流程(异步任务):
1. POST 提交文生图任务,返回 task_id
   端点: https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
   Header: Authorization: Bearer <key>, X-DashScope-Async: enable, Content-Type: application/json
2. GET 轮询任务状态,SUCCEEDED 后取 output.results[0].url
3. 下载图片,用 PIL 转存为 PNG 统一格式

设计:
- 全程标准库 urllib(无额外依赖),HTTP 用 asyncio.to_thread 包裹不阻塞
- 轮询上限 60 次(每次 2 秒),共 120 秒超时
- resize 到目标尺寸保证分镜图分辨率一致
"""
from __future__ import annotations

import asyncio
import io
import json
import urllib.request

from PIL import Image

from ...core.config import settings
from ...core.logging import logger
from .base import ImageProvider


class DashScopeImageProvider(ImageProvider):
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key or settings.dashscope_api_key
        if not self.api_key:
            raise RuntimeError("DashScope 文生图缺少 API Key")
        self.model = settings.image_model or "wan2.1-t2i-turbo"
        self.submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    async def generate(self, *, prompt: str, save_path: str, width: int = 1280, height: int = 720) -> str:
        size = f"{width}*{height}"
        body = json.dumps(
            {
                "model": self.model,
                "input": {"prompt": prompt},
                "parameters": {"size": size, "n": 1},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        logger.info("DashScope 文生图提交: model=%s size=%s prompt=%s", self.model, size, prompt[:50])

        # 1) 提交任务
        def _submit() -> dict:
            req = urllib.request.Request(self.submit_url, data=body, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())

        resp = await asyncio.to_thread(_submit)
        task_id = (resp.get("output") or {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"DashScope 文生图提交失败: {resp}")

        # 2) 轮询结果
        img_url = await self._poll(task_id)

        # 3) 下载并转存
        def _download() -> bytes:
            req = urllib.request.Request(img_url, headers={"User-Agent": "ai-video-agent/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()

        data = await asyncio.to_thread(_download)
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.size != (width, height):
            img = img.resize((width, height), Image.LANCZOS)
        img.save(save_path, "PNG")
        logger.info("DashScope 图片已保存: %s (%d bytes)", save_path, len(data))
        return save_path

    async def _poll(self, task_id: str, max_attempts: int = 60, interval: float = 2.0) -> str:
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for _ in range(max_attempts):
            await asyncio.sleep(interval)

            def _query() -> dict:
                req = urllib.request.Request(task_url, headers={"Authorization": f"Bearer {self.api_key}"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read())

            r = await asyncio.to_thread(_query)
            out = r.get("output") or {}
            status = out.get("task_status")
            if status == "SUCCEEDED":
                results = out.get("results") or []
                if not results:
                    raise RuntimeError(f"文生图成功但无结果: {r}")
                url = results[0].get("url") or results[0].get("b64_image")
                if not url:
                    raise RuntimeError(f"文生图结果无 url: {r}")
                return url
            if status == "FAILED":
                raise RuntimeError(f"DashScope 文生图失败: {r}")
        raise TimeoutError("DashScope 文生图轮询超时(120s)")
