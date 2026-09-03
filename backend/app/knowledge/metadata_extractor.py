"""从 VideoGenerationState 提取视频元数据。"""
from __future__ import annotations

from typing import Dict, Any

from ..models.state import VideoGenerationState


def extract_metadata(state: VideoGenerationState) -> Dict[str, Any]:
    """从 Pipeline 最终状态提取结构化元数据,用于 SQL 持久化和向量检索。"""
    req = state.requirement
    script = state.script
    storyboard = state.storyboard

    tags = []
    if req:
        if req.genre:
            tags.append(req.genre)
        if req.tone:
            tags.append(req.tone)
        if req.style:
            tags.append(req.style)

    quality_grade = None
    if state.quality_report and isinstance(state.quality_report, dict):
        quality_grade = state.quality_report.get("grade")

    return {
        "task_id": state.task_id,
        "user_id": state.user_id,
        "title": script.title if script else state.user_input[:50],
        "topic": req.topic if req else state.user_input[:50],
        "style": state.style,
        "duration": state.duration,
        "aspect_ratio": state.aspect_ratio,
        "tags": tags,
        "video_path": state.video_path,
        "model_used": state.model_used,
        "quality_grade": quality_grade,
        "shot_count": len(storyboard.shots) if storyboard else 0,
        "compliance_status": state.compliance_report.get("status") if state.compliance_report else None,
    }
