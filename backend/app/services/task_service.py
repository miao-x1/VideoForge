"""任务存储与 SSE 推送。

DB 持久化 + 内存 SSE Queue 混合架构:
- 任务状态持久化到 SQLite，服务重启不丢失
- SSE 订阅队列保留在内存(asyncio.Queue)，连接断开即清除
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy import select, desc

from ..db.database import async_session
from ..db.models import TaskRecord
from ..models.state import VideoGenerationState, TaskStatus


def _apply_confirmed_intent(state: VideoGenerationState, intent: dict) -> None:
    """将用户确认的创作意图写入 state,并合成 StructuredRequirement 供后续阶段消费。

    Gate 1 语义:确认后的 CreativeIntent 是权威输入,RequirementAgent 将跳过重新理解。
    """
    from ..schemas.creative_intent import CreativeIntent
    from ..schemas.requirement import StructuredRequirement, Scene

    ci = CreativeIntent(**intent)
    state.creative_intent = ci
    state.duration = ci.duration or state.duration
    state.aspect_ratio = ci.aspect_ratio or state.aspect_ratio
    if ci.visual_style and not state.style:
        state.style = ci.visual_style
    scenes = []
    if ci.scene:
        scenes.append(Scene(location=ci.scene, description=ci.scene_description or ""))
    state.requirement = StructuredRequirement(
        topic=ci.concept or state.user_input[:50],
        genre=ci.visual_style or "",
        duration=state.duration,
        style=ci.visual_style or state.style,
        scenes=scenes,
        tone=ci.emotion or "",
        visual_style=ci.visual_style or "",
        output_requirement=f"比例 {state.aspect_ratio}",
    )


class TaskStore:
    def __init__(self) -> None:
        self._cache: Dict[str, VideoGenerationState] = {}
        self._queues: Dict[str, List[asyncio.Queue]] = {}

    async def create(
        self, *, user_id: str, user_input: str, duration: int, style: str,
        aspect_ratio: str = "9:16", compliance_enabled: bool = True,
        input_sources: list | None = None,
        spec: dict | None = None, mode: str = "quick",
        project_id: str | None = None,
        confirmed_intent: dict | None = None,
    ) -> VideoGenerationState:
        state = VideoGenerationState(
            user_id=user_id, user_input=user_input, duration=duration,
            style=style, aspect_ratio=aspect_ratio, compliance_enabled=compliance_enabled,
            input_sources=input_sources or [],
        )
        if spec:
            from ..schemas.specification import VideoSpecification
            state.spec = VideoSpecification(**spec)
        if confirmed_intent:
            _apply_confirmed_intent(state, confirmed_intent)
            # 同步确认后的时长/比例到 spec,保证后续阶段一致
            if state.spec:
                state.spec.duration = state.duration
                state.spec.aspect_ratio = state.aspect_ratio
        state.mode = mode
        state.project_id = project_id
        # AI协作/专业模式:关键节点需用户确认(Human-in-the-loop Gate)
        # 快速创作(quick)不暂停,AI 自动完成全流程
        state.review_gates = ["script", "storyboard", "prompt"] if mode in ("collaborative", "professional") else []
        self._cache[state.task_id] = state

        async with async_session() as db:
            record = TaskRecord(
                task_id=state.task_id, user_id=user_id, user_input=user_input,
                duration=duration, style=style, aspect_ratio=aspect_ratio,
                compliance_enabled=compliance_enabled, status=state.status.value,
                spec_json=spec, mode=mode, project_id=project_id,
            )
            db.add(record)
            await db.commit()
        return state

    async def get(self, task_id: str) -> Optional[VideoGenerationState]:
        if task_id in self._cache:
            return self._cache[task_id]
        async with async_session() as db:
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.task_id == task_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return None
            state_json = record.state_json
            if state_json:
                state = VideoGenerationState(**state_json)
            else:
                state = self._reconstruct_from_record(record)
            self._cache[task_id] = state
            return state

    async def list_by_user(self, user_id: str) -> List[VideoGenerationState]:
        async with async_session() as db:
            result = await db.execute(
                select(TaskRecord)
                .where(TaskRecord.user_id == user_id)
                .order_by(desc(TaskRecord.created_at))
            )
            records = result.scalars().all()
        states: List[VideoGenerationState] = []
        for record in records:
            if record.task_id in self._cache:
                states.append(self._cache[record.task_id])
            elif record.state_json:
                states.append(VideoGenerationState(**record.state_json))
            else:
                states.append(self._reconstruct_from_record(record))
        return states

    async def save(self, state: VideoGenerationState) -> None:
        self._cache[state.task_id] = state
        async with async_session() as db:
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.task_id == state.task_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return
            record.status = state.status.value
            record.video_path = state.video_path
            grade = None
            if state.quality_report and isinstance(state.quality_report, dict):
                grade = state.quality_report.get("grade")
            record.quality_grade = grade
            record.state_json = json.loads(state.model_dump_json())
            await db.commit()
        for q in self._queues.get(state.task_id, []):
            try:
                q.put_nowait(state.model_copy(deep=True))
            except asyncio.QueueFull:
                pass

    @staticmethod
    def _reconstruct_from_record(record: TaskRecord) -> VideoGenerationState:
        state = VideoGenerationState(
            task_id=record.task_id,
            user_id=record.user_id,
            user_input=record.user_input,
            duration=record.duration,
            style=record.style,
            aspect_ratio=record.aspect_ratio,
            compliance_enabled=record.compliance_enabled,
            status=TaskStatus(record.status),
            video_path=record.video_path,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        if record.spec_json:
            from ..schemas.specification import VideoSpecification
            state.spec = VideoSpecification(**record.spec_json)
        if record.mode:
            state.mode = record.mode
        return state

    def save_sync(self, state: VideoGenerationState) -> None:
        self._cache[state.task_id] = state
        for q in self._queues.get(state.task_id, []):
            try:
                q.put_nowait(state.model_copy(deep=True))
            except asyncio.QueueFull:
                pass

    def subscribe(self, task_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._queues.setdefault(task_id, []).append(q)
        state = self._cache.get(task_id)
        if state is not None:
            try:
                q.put_nowait(state.model_copy(deep=True))
            except asyncio.QueueFull:
                pass
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        if task_id in self._queues:
            try:
                self._queues[task_id].remove(q)
            except ValueError:
                pass
            if not self._queues[task_id]:
                del self._queues[task_id]

    async def stream(self, task_id: str) -> AsyncGenerator[VideoGenerationState, None]:
        q = self.subscribe(task_id)
        try:
            while True:
                state = await q.get()
                yield state
                if state.status in ("COMPLETED", "FAILED", "HUMAN_REVIEW", "SCRIPT_REVIEW", "STORYBOARD_REVIEW", "PROMPT_REVIEW"):
                    break
        finally:
            self.unsubscribe(task_id, q)


task_store = TaskStore()
