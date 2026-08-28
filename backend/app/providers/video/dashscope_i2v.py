"""DashScope 万相图生视频(I2V)Provider。

通过 DashScope 异步 API 调用通义万相 wan2.6-i2v-flash,把关键帧图片变成 N 秒动态视频。
突破 Ken Burns 只能缩放平移静态图的局限,让画面里的人物/场景真正"动起来"。

调用流程(异步任务):
1. POST 提交图生视频任务,返回 task_id
   端点: https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
   Header: Authorization: Bearer <key>, X-DashScope-Async: enable, Content-Type: application/json
   Body: {"model": "wan2.6-i2v-flash", "input": {"prompt": ..., "img_url": "data:image/png;base64,..."},
          "parameters": {"resolution": "720P", "duration": 5}}
2. GET 轮询任务状态,SUCCEEDED 后取 output.video_url
3. 下载 MP4 保存到本地

设计:
- 全程标准库 urllib(无额外依赖),阻塞 IO 用 asyncio.to_thread 包裹
- 首帧图片用 base64 编码传入(无需公网图床,适合本地素材)
- 轮询上限 60 次(每次 5 秒),共 5 分钟超时(I2V 比 T2I 慢 3-5 倍)
- wan2.6-i2v-flash 时长支持 [2, 15],分辨率 720P/1080P,9:16 由输入图宽高比自动适配
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import urllib.request
from pathlib import Path

from ...core.config import settings
from ...core.logging import logger
from .base import VideoProvider

# wan2.6-i2v-flash 时长范围 [2, 15]
_MIN_DURATION = 2
_MAX_DURATION = 15
# 轮询参数(I2V 比 T2I 慢,5 分钟超时)
_POLL_MAX_ATTEMPTS = 60
_POLL_INTERVAL = 5.0


class DashScopeI2VProvider(VideoProvider):
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key or settings.dashscope_api_key
        if not self.api_key:
            raise RuntimeError("DashScope 图生视频缺少 API Key")
        self.model = settings.i2v_model or "wan2.6-i2v-flash"
        self.submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"

    async def generate(
        self,
        *,
        image_path: str,
        prompt: str,
        save_path: str,
        duration: int = 5,
    ) -> str:
        # clamp 到模型支持范围
        dur = max(_MIN_DURATION, min(_MAX_DURATION, duration))
        # 首帧图片转 base64
        img_b64 = await asyncio.to_thread(self._encode_image, image_path)
        body = json.dumps(
            {
                "model": self.model,
                "input": {"prompt": prompt, "img_url": img_b64},
                "parameters": {"resolution": "720P", "duration": dur},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        logger.info(
            "DashScope 图生视频提交: model=%s dur=%ss img=%s prompt=%s",
            self.model, dur, os.path.basename(image_path), prompt[:80],
        )

        # 1) 提交任务
        def _submit() -> dict:
            req = urllib.request.Request(self.submit_url, data=body, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())

        resp = await asyncio.to_thread(_submit)
        task_id = (resp.get("output") or {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"DashScope 图生视频提交失败: {resp}")

        # 2) 轮询结果
        video_url = await self._poll(task_id)

        # 3) 下载 MP4
        def _download() -> bytes:
            req = urllib.request.Request(video_url, headers={"User-Agent": "ai-video-agent/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()

        data = await asyncio.to_thread(_download)
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(data)
        logger.info("DashScope 视频已保存: %s (%d bytes)", save_path, len(data))
        return save_path

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """读取本地图片并编码为 data URL。"""
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
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read())

            r = await asyncio.to_thread(_query)
            out = r.get("output") or {}
            status = out.get("task_status")
            logger.debug("图生视频轮询[%d/%d] status=%s", attempt + 1, _POLL_MAX_ATTEMPTS, status)
            if status == "SUCCEEDED":
                url = out.get("video_url")
                if not url:
                    raise RuntimeError(f"图生视频成功但无 video_url: {r}")
                return url
            if status == "FAILED":
                raise RuntimeError(f"DashScope 图生视频失败: {r}")
        raise TimeoutError(f"DashScope 图生视频轮询超时({_POLL_MAX_ATTEMPTS * _POLL_INTERVAL}s)")
