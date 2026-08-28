"""任务存储与 SSE 推送。

第一阶段用进程内字典 + asyncio.Queue,保证不引入外部依赖即可跑通。
后续可替换为 Redis/DB,Orchestrator 与 API 层逻辑不变。
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from ..models.state import VideoGenerationState


class TaskStore:
    def __init__(self) -> None:
        self._tasks: Dict[str, VideoGenerationState] = {}
        self._queues: Dict[str, List[asyncio.Queue]] = {}

    # ---- 任务 CRUD ----
    def create(self, *, user_input: str, duration: int, style: str) -> VideoGenerationState:
        state = VideoGenerationState(user_input=user_input, duration=duration, style=style)
        self._tasks[state.task_id] = state
        return state

    def get(self, task_id: str) -> Optional[VideoGenerationState]:
        return self._tasks.get(task_id)

    def list(self) -> List[VideoGenerationState]:
        return list(self._tasks.values())

    def save(self, state: VideoGenerationState) -> None:
        self._tasks[state.task_id] = state
        # 通知所有订阅者
        for q in self._queues.get(state.task_id, []):
            try:
                q.put_nowait(state.model_copy(deep=True))
            except asyncio.QueueFull:
                pass

    # ---- SSE 订阅 ----
    def subscribe(self, task_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._queues.setdefault(task_id, []).append(q)
        # 立即推送一次当前状态
        state = self._tasks.get(task_id)
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
                # 终止条件:任务进入终态
                if state.status in ("COMPLETED", "FAILED"):
                    break
        finally:
            self.unsubscribe(task_id, q)


# 进程内单例
task_store = TaskStore()
