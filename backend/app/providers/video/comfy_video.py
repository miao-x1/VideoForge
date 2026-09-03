"""ComfyUI Cloud 视频 Provider:Agent → Workflow → Model 执行层。

实现统一 VideoModelProvider 接口:
  - 业务参数(首帧图+prompt+时长+比例)经 Capability Router 选择官方 MiniMax H3 Workflow
  - Adapter 完成 业务参数 → Workflow 参数 映射(prompt/首帧文件名/宽高/时长)
  - ComfyCloudClient 负责云端上传/提交/轮询/取回

Orchestrator / VideoWorkflow 与既有路由体系零改动接入。
"""
from __future__ import annotations

import asyncio
import random
from pathlib import Path

from ...core.exceptions import ProviderError
from ...core.logging import logger
from ...services.capability_router import select_workflow, WorkflowNotAvailableError
from ...services.comfy_service import get_comfy_client
from .base import ModelRequest, ModelResponse, VideoModelProvider
from .capabilities import ModelCapabilities
from workflows.adapter import (
    duration_to_length,
    resolve_aspect_ratio,
    workflow_adapter,
    WorkflowValidationError,
)

_MAX_ATTEMPTS = 2  # 首次 + 瞬态错误重试 1 次
# 不可重试的错误码(重试无意义)
_FATAL_CODES = {"INVALID_API_KEY", "NOT_CONFIGURED", "WORKFLOW_INVALID", "NO_OUTPUT", "PARAM_INVALID"}


class ComfyVideoProvider(VideoModelProvider):
    """MiniMax H3(经云端 ComfyUI 官方 Workflow)视频生成。"""

    def __init__(self, workflow_id: str | None = None) -> None:
        self.workflow_id = workflow_id
        self._client = get_comfy_client()

    @property
    def name(self) -> str:
        return "MiniMax-H3"

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_duration=10,
            supported_ratios=["9:16", "16:9", "1:1"],
            max_resolution="1080P",
            quality_score=10,
            speed_score=6,
            cost_per_sec=0.8,
            supports_image_input=True,
            supports_video_input=True,
            supports_audio_output=False,
            supports_first_frame=True,
            supports_last_frame=False,
            supports_motion_control=True,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        # ---- Agent 业务参数 → Workflow 选择 ----
        # 有参考素材(非首帧)时走 R2V 官方模板(角色/风格一致性)
        if request.reference_paths:
            task_type = "reference_to_video"
        else:
            task_type = "image_to_video" if request.image_path else "text_to_video"
        try:
            config = select_workflow(task_type, preferred_workflow=self.workflow_id)
        except WorkflowNotAvailableError as e:
            raise ProviderError("video/comfy", str(e), error_code="WORKFLOW_NOT_FOUND") from e

        # ---- 业务参数归一化(Adapter 语义参数) ----
        width, height = resolve_aspect_ratio(request.aspect_ratio)
        params: dict = {
            "prompt": request.prompt,
            "width": width,
            "height": height,
            "duration": float(request.duration),
            "seed": random.randint(0, 2**31 - 1),
        }
        if request.image_path:
            # 首帧图上传云端,LoadImage 引用云端文件名
            params["first_frame"] = await asyncio.to_thread(
                self._client.upload_image, request.image_path
            )
        if request.last_frame_path:
            params["last_frame"] = await asyncio.to_thread(
                self._client.upload_image, request.last_frame_path
            )
        for ref in request.reference_paths or []:
            params.setdefault("references", []).append(
                await asyncio.to_thread(self._client.upload_image, ref)
            )
        if "length" in config.inputs:  # R2V 用帧数,由秒换算
            params["length"] = duration_to_length(float(request.duration))

        try:
            prompt_api = workflow_adapter.build_prompt(config.workflow_id, params)
        except WorkflowValidationError as e:
            raise ProviderError("video/comfy", str(e), error_code="PARAM_INVALID") from e

        # ---- 提交 + 轮询 + 取回(瞬态错误重试) ----
        prompt_id, video_bytes = "", b""
        last_error: ProviderError | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                prompt_id = await asyncio.to_thread(self._client.submit, prompt_api)
                logger.info(
                    "ComfyUI Workflow 提交: %s job=%s (attempt %d/%d)",
                    config.workflow_id, prompt_id, attempt + 1, _MAX_ATTEMPTS,
                )
                await self._client.poll(prompt_id)
                video_bytes = await asyncio.to_thread(self._client.fetch_video, prompt_id)
                break
            except ProviderError as e:
                last_error = e
                if e.error_code in _FATAL_CODES:
                    raise
                logger.warning("ComfyUI 执行失败(第 %d 次): %s", attempt + 1, e)

        if not video_bytes:
            raise last_error or ProviderError("video/comfy", "生成失败", error_code="GENERATION_FAILED")

        # ---- 保存输出 ----
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(video_bytes)
        logger.info("ComfyUI 视频已保存: %s (%d bytes)", request.save_path, len(video_bytes))
        return ModelResponse(
            video_path=request.save_path, duration=request.duration, model=self.name, task_id=prompt_id
        )
