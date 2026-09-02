"""FastAPI 路由。

对外接口:
  POST /api/video/tasks                      创建任务并立即返回 task_id,后台异步执行
  GET   /api/video/tasks                    任务列表
  GET   /api/video/tasks/{task_id}          任务全量状态
  GET   /api/video/tasks/{task_id}/status   仅 status + logs(轮询用)
  GET   /api/video/tasks/{task_id}/result    终态产物
  GET   /api/video/tasks/{task_id}/stream    SSE 实时推送
"""
from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..models.state import VideoGenerationState
from ..services.task_service import task_store
from ..orchestrator.orchestrator import orchestrator


router = APIRouter(prefix="/api/video", tags=["video"])


class CreateTaskRequest(BaseModel):
    user_input: str = Field(..., description="用户的视频创意")
    duration: int = Field(30, description="视频时长(秒)")
    style: str = Field("", description="视频风格")
    aspect_ratio: str = Field("9:16", description="视频比例")
    compliance_enabled: bool = Field(True, description="是否启用合规预审")


class TaskBrief(BaseModel):
    task_id: str
    user_input: str
    status: str
    created_at: float


@router.post("/tasks", response_model=TaskBrief)
async def create_task(req: CreateTaskRequest) -> TaskBrief:
    state = task_store.create(
        user_input=req.user_input, duration=req.duration, style=req.style,
        aspect_ratio=req.aspect_ratio, compliance_enabled=req.compliance_enabled,
    )
    # 后台异步执行 Pipeline,不阻塞响应
    asyncio.create_task(orchestrator.execute(state))
    return TaskBrief(
        task_id=state.task_id,
        user_input=state.user_input,
        status=state.status.value,
        created_at=state.created_at,
    )


@router.get("/tasks", response_model=List[TaskBrief])
async def list_tasks() -> List[TaskBrief]:
    return [
        TaskBrief(
            task_id=s.task_id, user_input=s.user_input,
            status=s.status.value, created_at=s.created_at,
        )
        for s in task_store.list()
    ]


def _get_or_404(task_id: str) -> VideoGenerationState:
    s = task_store.get(task_id)
    if s is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return s


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    return _get_or_404(task_id).model_dump()


@router.get("/tasks/{task_id}/status")
async def get_status(task_id: str) -> dict:
    s = _get_or_404(task_id)
    return {
        "task_id": s.task_id,
        "status": s.status.value,
        "logs": [l.model_dump() for l in s.logs],
        "error": s.error,
    }


@router.get("/tasks/{task_id}/result")
async def get_result(task_id: str) -> dict:
    s = _get_or_404(task_id)
    return {
        "task_id": s.task_id,
        "status": s.status.value,
        "video_path": s.video_path,
        "video_url": f"/storage/videos/{task_id}.mp4" if s.video_path else None,
        "title": s.script.title if s.script else None,
        "created_at": s.created_at,
        # 各阶段结构化产物(供前端生成结束后展示报告面板)
        "requirement": s.requirement.model_dump() if s.requirement else None,
        "script": s.script.model_dump() if s.script else None,
        "storyboard": s.storyboard.model_dump() if s.storyboard else None,
        "compliance_report": s.compliance_report,
        "content_guard_report": s.content_guard_report,
        "quality_report": s.quality_report,
        "revision_count": s.revision_count,
        "human_review_required": s.human_review_required,
        "failure_detail": s.failure_detail,
    }


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str) -> StreamingResponse:
    if task_store.get(task_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_source():
        async for state in task_store.stream(task_id):
            payload = json.dumps(
                {
                    "task_id": state.task_id,
                    "status": state.status.value,
                    "logs": [l.model_dump() for l in state.logs],
                    "error": state.error,
                    "video_path": state.video_path,
                    "failure_detail": state.failure_detail,
                    # 渐进推送各阶段产物(生成中逐步填充,前端实时展示)
                    "requirement": state.requirement.model_dump() if state.requirement else None,
                    "script": state.script.model_dump() if state.script else None,
                    "storyboard": state.storyboard.model_dump() if state.storyboard else None,
                    "compliance_report": state.compliance_report,
                    "content_guard_report": state.content_guard_report,
                    "quality_report": state.quality_report,
                    "revision_count": state.revision_count,
                    "human_review_required": state.human_review_required,
                },
                ensure_ascii=False,
                default=str,
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
