"""Project Memory:每个项目维护跨任务的结构化记忆。

存储:创作设定 / 主体 / 场景 / 风格 / Prompt 摘要 / 历史视频 / 用户修改记录。
落库:projects.memory_json(JSON 列),任务完成或局部重生成完成时增量合并。
用途:同项目新任务自动继承设定,专业创作者做系列内容时保持一致性。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from ..core.logging import logger
from ..db.database import get_session
from ..db.models import Project, TaskRecord
from ..models.state import VideoGenerationState


def _merge_list(existing: list, new_items: list, max_len: int = 20) -> list:
    """去重合并列表(新项在前,保序),超长截断。"""
    out = [i for i in new_items if i not in existing]
    out.extend(existing)
    seen, uniq = set(), []
    for i in out:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return uniq[:max_len]


def extract_memory_from_state(state: VideoGenerationState) -> dict:
    """从任务状态抽取可沉淀进项目记忆的信息。"""
    ci = state.creative_intent
    memory: dict = {
        "subjects": [],
        "scenes": [],
        "styles": [],
        "prompts": [],
        "modifications": [],
        "videos": [],
    }
    # 创作设定
    settings: dict = {"duration": state.duration, "aspect_ratio": state.aspect_ratio}
    if state.style:
        settings["style"] = state.style
    if ci:
        if ci.subject:
            memory["subjects"].append(ci.subject)
        if ci.scene:
            memory["scenes"].append(ci.scene)
        if ci.visual_style:
            memory["styles"].append(ci.visual_style)
    if state.spec:
        # 主体:创作元素(排除环境类)
        env_types = {"landscape", "abstract"}
        for el in state.spec.creative_elements:
            if el.name and el.type.value not in env_types:
                memory["subjects"].append(el.name)
        # 场景
        if state.spec.environment and state.spec.environment.location:
            memory["scenes"].append(state.spec.environment.location)
        # 风格(Style Stack 多选)
        for s in state.spec.visual_style:
            if s.name:
                memory["styles"].append(s.name)
        if state.spec.custom_style:
            memory["styles"].append(state.spec.custom_style)
    memory["settings"] = settings

    # 脚本/分镜摘要
    if state.script:
        memory["script_summary"] = {"title": state.script.title}
    if state.storyboard:
        memory["storyboard_summary"] = {"shot_count": len(state.storyboard.shots)}

    # Prompt 摘要(模型感知的最终 Prompt 片段)
    pe = state.prompt_engineering_result or {}
    model_id = pe.get("model_id", "")
    for p in (pe.get("prompts") or [])[:8]:
        prompt_text = p.get("raw_image_prompt") or p.get("raw_video_prompt") or ""
        if prompt_text:
            memory["prompts"].append(
                {"model_id": model_id, "shot_index": p.get("shot_index", 0), "text": prompt_text[:200]}
            )

    # 生成结果
    if state.video_path:
        grade = (state.quality_report or {}).get("grade") if isinstance(state.quality_report, dict) else None
        memory["videos"].append({
            "task_id": state.task_id, "video_path": state.video_path,
            "model": state.model_used, "grade": grade,
        })

    # 用户修改记录(版本历史 reason 聚合)
    memory["modifications"] = [
        {"node_type": v.node_type, "version": v.version, "reason": v.reason}
        for v in state.version_history if v.reason
    ]
    return memory


def merge_memory(existing: Optional[dict], new: dict) -> dict:
    """合并新旧记忆:列表去重合并,生成结果按 task 去重。"""
    existing = existing or {}
    merged = dict(existing)
    merged["subjects"] = _merge_list(existing.get("subjects", []), new.get("subjects", []))
    merged["scenes"] = _merge_list(existing.get("scenes", []), new.get("scenes", []))
    merged["styles"] = _merge_list(existing.get("styles", []), new.get("styles", []))

    old_prompts = existing.get("prompts", [])
    new_prompts = [p for p in new.get("prompts", []) if p not in old_prompts]
    merged["prompts"] = (new_prompts + old_prompts)[:30]

    old_videos = existing.get("videos", [])
    old_task_ids = {v.get("task_id") for v in old_videos}
    new_videos = [v for v in new.get("videos", []) if v.get("task_id") not in old_task_ids]
    merged["videos"] = (new_videos + old_videos)[:30]

    old_mods = existing.get("modifications", [])
    new_mods = [m for m in new.get("modifications", []) if m not in old_mods]
    merged["modifications"] = (new_mods + old_mods)[:50]

    if new.get("settings"):
        merged["settings"] = new["settings"]
    for key in ("script_summary", "storyboard_summary"):
        if new.get(key):
            merged[key] = new[key]
    return merged


def update_project_memory(state: VideoGenerationState) -> None:
    """任务完成/局部修改后,把本次任务的记忆增量合并进项目记忆(同步,失败不影响主流程)。"""
    project_id = state.project_id
    if not project_id:
        return
    try:
        new_memory = extract_memory_from_state(state)
        with get_session() as session:
            project = session.scalar(
                select(Project).where(Project.id == project_id)
            )
            if project is None:
                return
            merged = merge_memory(project.memory_json, new_memory)
            project.memory_json = merged
            session.commit()
        logger.info(
            "项目记忆已更新: project=%s subjects=%d videos=%d",
            project_id, len(merged.get("subjects", [])), len(merged.get("videos", [])),
        )
    except Exception as e:  # 项目记忆失败不影响主流程
        logger.warning("项目记忆更新失败(不影响任务): %s", e)


def load_project_memory(project_id: Optional[str]) -> dict:
    """加载项目记忆(供同项目新任务继承:注入 RequirementAgent 上下文保持系列一致性)。"""
    if not project_id:
        return {}
    try:
        with get_session() as session:
            project = session.scalar(
                select(Project).where(Project.id == project_id)
            )
            return project.memory_json if project else {}
    except Exception:
        return {}


def build_memory_hints(memory: dict) -> dict:
    """把项目记忆压缩为需求理解阶段的上下文提示(仅保留轻量字段,不含历史长列表)。"""
    if not memory:
        return {}
    hints: dict = {}
    if memory.get("settings"):
        hints["series_settings"] = memory["settings"]
    for key in ("subjects", "scenes", "styles"):
        seen: set = set()
        items: list = []
        for i in memory.get(key, []):
            if i and i not in seen:
                seen.add(i)
                items.append(i)
        items = items[:8]
        if items:
            hints[f"series_{key}"] = items
    return hints


def get_task_project_id(task_id: str) -> Optional[str]:
    """从 TaskRecord 反查项目 ID(state 无 project_id 时兜底)。"""
    try:
        with get_session() as session:
            record = session.scalar(
                select(TaskRecord).where(TaskRecord.task_id == task_id)
            )
            return record.project_id if record else None
    except Exception:
        return None
