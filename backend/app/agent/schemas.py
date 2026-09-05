"""DirectorContext / Tool / Operation 的文档化结构。执行以导演台状态为准。"""
from __future__ import annotations

from typing import Any, TypedDict


class Vec3Dict(TypedDict):
    x: float
    y: float
    z: float


class PlannedCall(TypedDict, total=False):
    name: str
    arguments: dict[str, Any]
    note: str


class PlanResult(TypedDict, total=False):
    thinking: list[str]
    calls: list[PlannedCall]
    error: str | None


class DirectorPlanDict(TypedDict, total=False):
    plan_id: str
    project_id: str
    scene_id: str
    intent: str
    summary: str
    actions: list[dict[str, Any]]
    camera: dict[str, Any]
    generation: dict[str, Any]
    required_assets: list[str]
    tool_calls: list[PlannedCall]
    risk_level: str
    requires_confirmation: bool
