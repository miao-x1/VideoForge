"""FastAPI 视频路由。

所有端点均需 JWT 鉴权，用户只能访问自己的任务。

对外接口:
  POST /api/video/tasks                      创建任务
  GET   /api/video/tasks                    当前用户任务列表
  GET   /api/video/tasks/{task_id}          任务全量状态
  GET   /api/video/tasks/{task_id}/status   仅 status + logs(轮询用)
  GET   /api/video/tasks/{task_id}/result    终态产物
  GET   /api/video/tasks/{task_id}/stream    SSE 实时推送
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_sse
from ..core.config import settings, storage_dir
from ..db.models import User
from ..knowledge.video_searcher import video_searcher
from ..models.state import VideoGenerationState, InputSourceItem, TaskStatus
from ..services.task_service import task_store
from ..orchestrator.orchestrator import orchestrator
from ..providers.video import list_available_models
from ..providers.llm import get_llm_provider
from ..router.model_registry import registry
from ..schemas.specification import VideoSpecification
from ..graph import dependency_graph


router = APIRouter(prefix="/api/video", tags=["video"])


class CreateTaskRequest(BaseModel):
    user_input: str = Field("", description="用户的视频创意(spec 存在时从 spec.prompt 取)")
    duration: int = Field(30, description="视频时长(秒)")
    style: str = Field("", description="视频风格")
    aspect_ratio: str = Field("9:16", description="视频比例")
    compliance_enabled: bool = Field(True, description="是否启用合规预审")
    input_sources: list[InputSourceItem] = Field(default_factory=list, description="多模态输入源")
    preferred_model: str = Field("", description="偏好模型: qwen/minimax,空则自动选择")
    spec: VideoSpecification | None = Field(None, description="结构化创作意图(提供时覆盖扁平字段)")
    mode: str = Field("quick", description="创作模式: quick / professional")
    project_id: str = Field("", description="关联项目 ID(可选)")
    confirmed_intent: dict | None = Field(None, description="用户已确认的创作方案(Gate 1),提供时 Pipeline 跳过需求重新理解")


class UnderstandRequest(BaseModel):
    """独立需求理解:输入创意(含多模态),返回 AI 结构化的创作意图。"""
    user_input: str = Field(..., description="用户的视频创意")
    duration: int = Field(30, description="视频时长(秒)")
    style: str = Field("", description="视频风格")
    aspect_ratio: str = Field("9:16", description="视频比例")
    input_sources: list[InputSourceItem] = Field(default_factory=list, description="多模态输入源(带用途标注)")


class ScriptConfirmRequest(BaseModel):
    """Gate 2 脚本确认:可携带用户编辑后的脚本。"""
    script: dict | None = Field(None, description="用户编辑后的脚本(VideoScript 结构),不传则确认当前脚本")


class StoryboardConfirmRequest(BaseModel):
    """Gate 3 分镜确认:可携带用户编辑后的分镜。"""
    storyboard: dict | None = Field(None, description="用户编辑后的分镜(Storyboard 结构),不传则确认当前分镜")


class StoryboardRegenerateRequest(BaseModel):
    """Gate 3 分镜重新生成:整体或单个镜头。"""
    shot_index: int | None = Field(None, description="要重新生成的镜头索引(0 起),不传则重新生成全部分镜")
    feedback: str | None = Field(None, description="用户反馈:哪里不满意,注入重生成上下文定向修改")


class RegenerateRequest(BaseModel):
    """Decision Loop 重新生成:可选的用户反馈。"""
    feedback: str | None = Field(None, description="用户反馈:哪里不满意,注入重生成上下文定向修改")


class PromptConfirmRequest(BaseModel):
    """Gate 4 Prompt 确认:可携带用户编辑后的 Prompt Engineering 结果。"""
    prompt_result: dict | None = Field(None, description="用户编辑后的 PromptEngineeringResult 结构,不传则确认当前 Prompt")


class ModelSelectRequest(BaseModel):
    """Gate 4 手动切换视频模型。"""
    model_id: str = Field(..., description="目标视频模型 ID(来自 /api/video/models)")


class TaskRetryRequest(BaseModel):
    """失败重试:从失败阶段恢复,保留已完成阶段产物。"""
    retry: bool = Field(True, description="保留字段,兼容请求体")


class ShotLockRequest(BaseModel):
    """锁定/解锁镜头。"""
    locked: bool = Field(..., description="True=锁定(局部重生成跳过),False=解锁")


class ShotReviseRequest(BaseModel):
    """局部重生成:修改指定镜头后仅重新生成受影响内容。"""
    shot_indices: List[int] = Field(..., description="要修改/重生成的镜头索引列表(0 起)")
    edits: Optional[dict] = Field(None, description="镜头编辑 {索引: 部分字段},如 {\"2\": {visual_description: ...}}")
    feedback: Optional[str] = Field(None, description="用户反馈:期望的修改方向,注入单镜头 Prompt 重编译")


class SceneReviseRequest(BaseModel):
    """Scene 级局部重生成:编辑脚本场景后仅重生成该场景关联镜头链。"""
    scene_edits: Optional[dict] = Field(None, description="场景编辑(部分字段),如 {visual: ..., dialogue: ...}")
    feedback: Optional[str] = Field(None, description="用户反馈:期望的修改方向,注入镜头重生成上下文")


class AnalyzeRequest(BaseModel):
    spec: VideoSpecification | None = Field(None, description="结构化创作意图")
    prompt: str = Field("", description="纯文本创意(spec 为空时使用)")
    duration: int = Field(30)
    style: str = Field("")
    aspect_ratio: str = Field("9:16")


class TaskBrief(BaseModel):
    model_config = {"protected_namespaces": ()}
    task_id: str
    user_input: str
    status: str
    created_at: float
    model_used: str = ""


@router.get("/models")
async def list_models(user: User = Depends(get_current_user)) -> list[dict]:
    """列出可用视频模型及能力描述。"""
    return list_available_models()


@router.get("/workflows")
async def list_workflows(user: User = Depends(get_current_user)) -> list[dict]:
    """列出已接入的云端 ComfyUI Workflow(供专业用户查看可用能力与输入规范)。"""
    from workflows.registry import workflow_registry
    return [
        {
            "workflow_id": c.workflow_id,
            "provider": c.provider,
            "category": c.category,
            "model": c.model,
            "version": c.version,
            "source": c.source,
            "description": c.description,
            "inputs": {name: {"type": s.type, "required": s.required} for name, s in c.inputs.items()},
        }
        for c in workflow_registry.list_workflows()
    ]


@router.get("/models/registry")
async def list_registry_models(
    model_type: str = Query("", description="按类型过滤: reasoning/general_llm/text_to_image/image_to_video/tts/music/embedding"),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """列出 Model Registry 中所有已注册模型,支持按类型过滤。"""
    if model_type:
        entries = registry.list_by_type(model_type)
    else:
        entries = registry.list_enabled()
    return [m.to_dict() for m in entries]


@router.get("/models/recommend")
async def recommend_model(
    q: str = Query("", description="用户创意文本"),
    duration: int = Query(30, ge=5, le=120),
    style: str = Query(""),
    aspect_ratio: str = Query("9:16"),
    preferred_model: str = Query(""),
    strategy: str = Query("auto", description="路由策略: auto/best_quality/lowest_cost/fastest"),
    user: User = Depends(get_current_user),
) -> dict:
    """根据需求参数返回推荐模型 + 评分理由。"""
    from ..router import model_router
    decision = model_router.select(
        user_input=q, duration=duration, style=style,
        aspect_ratio=aspect_ratio, preferred_model=preferred_model or None,
        strategy=strategy,
    )
    return decision.to_dict()


@router.post("/analyze")
async def analyze_creative_intent(
    req: AnalyzeRequest, user: User = Depends(get_current_user),
) -> dict:
    """分析创作意图:编译 prompt + 推荐模型 + 维度摘要。

    前端在用户编辑 spec 时调用,用于右侧 AI 计划面板实时预览。
    """
    if req.spec:
        spec = req.spec
    else:
        spec = VideoSpecification(
            prompt=req.prompt, duration=req.duration,
            aspect_ratio=req.aspect_ratio,
        )

    from ..agents.prompt_compiler import PromptCompiler
    compiled_prompt = PromptCompiler.compile_full_prompt(spec)

    from ..router import model_router
    style_str = _spec_style_str(spec)
    decision = model_router.select(
        user_input=spec.prompt, duration=spec.duration, style=style_str,
        aspect_ratio=spec.aspect_ratio, preferred_model=spec.preferred_model or None,
    )

    return {
        "compiled_prompt": compiled_prompt,
        "recommended_model": decision.to_dict(),
        "dimensions": _summarize_dimensions(spec),
    }


def _spec_style_str(spec: VideoSpecification) -> str:
    from ..agents.prompt_compiler import _compile_visual_style
    return _compile_visual_style(spec.visual_style, spec.custom_style)


def _summarize_dimensions(spec: VideoSpecification) -> dict:
    dims: dict[str, bool] = {}
    dims["prompt"] = bool(spec.prompt)
    dims["creative_elements"] = len(spec.creative_elements) > 0
    dims["environment"] = spec.environment is not None and any(
        v for v in spec.environment.model_dump().values()
    ) if spec.environment else False
    dims["narrative"] = spec.narrative is not None and any(
        v for v in spec.narrative.model_dump().values()
    ) if spec.narrative else False
    dims["motion"] = spec.motion is not None and any(
        v for v in spec.motion.model_dump().values()
    ) if spec.motion else False
    dims["visual_style"] = len(spec.visual_style) > 0 or bool(spec.custom_style)
    dims["camera"] = spec.camera is not None and any(
        v for v in spec.camera.model_dump().values()
    ) if spec.camera else False
    dims["audio"] = spec.audio is not None and any(
        v for v in spec.audio.model_dump().values()
    ) if spec.audio else False
    dims["references"] = len(spec.references) > 0
    dims["advanced"] = spec.advanced is not None
    return dims


@router.post("/understand")
async def understand_creative_intent(
    req: UnderstandRequest, user: User = Depends(get_current_user),
) -> dict:
    """AI 理解用户创意,返回结构化创作意图(Gate 1 前的 AI 结构化步骤)。

    不创建任务、不落库。用户在前端确认/修改后,通过 confirmed_intent 传入
    POST /tasks 才真正进入生成 Pipeline。
    """
    try:
        state = await orchestrator.understand(
            user_input=req.user_input,
            duration=req.duration,
            style=req.style,
            aspect_ratio=req.aspect_ratio,
            input_sources=[s.model_dump() for s in req.input_sources],
        )
    except Exception as e:
        raise HTTPException(502, f"创意理解失败: {e}")
    if state.creative_intent is None:
        raise HTTPException(502, "AI 未能理解该创意,请补充描述后重试")
    return {"creative_intent": state.creative_intent.to_dict()}


@router.post("/tasks", response_model=TaskBrief)
async def create_task(req: CreateTaskRequest, user: User = Depends(get_current_user)) -> TaskBrief:
    if req.spec:
        spec = req.spec
        user_input = spec.prompt or req.user_input
        duration = spec.duration
        style = _spec_style_str(spec)
        aspect_ratio = spec.aspect_ratio
        preferred_model = spec.preferred_model or req.preferred_model
        compliance_enabled = req.compliance_enabled
        if spec.advanced:
            compliance_enabled = spec.advanced.compliance_enabled
    else:
        # 快速模式:从扁平字段构建最小 VideoSpecification,确保 Pipeline 收敛
        spec = VideoSpecification(
            prompt=req.user_input,
            duration=req.duration,
            aspect_ratio=req.aspect_ratio,
            preferred_model=req.preferred_model,
            custom_style=req.style,
        )
        user_input = req.user_input
        duration = req.duration
        style = req.style
        aspect_ratio = req.aspect_ratio
        preferred_model = req.preferred_model
        compliance_enabled = req.compliance_enabled

    state = await task_store.create(
        user_id=user.id, user_input=user_input, duration=duration,
        style=style, aspect_ratio=aspect_ratio,
        compliance_enabled=compliance_enabled,
        input_sources=[s.model_dump() for s in req.input_sources],
        spec=spec.model_dump(),
        mode=req.mode,
        project_id=req.project_id or None,
        confirmed_intent=req.confirmed_intent,
    )
    from ..router import model_router
    decision = model_router.select(
        user_input=user_input, duration=duration, style=style,
        aspect_ratio=aspect_ratio, preferred_model=preferred_model or None,
    )
    asyncio.create_task(orchestrator.execute(state, preferred_model=preferred_model or None))
    return TaskBrief(
        task_id=state.task_id,
        user_input=state.user_input,
        status=state.status.value,
        created_at=state.created_at,
        model_used=decision.selected_provider,
    )


@router.get("/tasks", response_model=List[TaskBrief])
async def list_tasks(user: User = Depends(get_current_user)) -> List[TaskBrief]:
    states = await task_store.list_by_user(user.id)
    return [
        TaskBrief(
            task_id=s.task_id, user_input=s.user_input,
            status=s.status.value, created_at=s.created_at,
            model_used=s.model_used or "",
        )
        for s in states
    ]


@router.post("/tasks/{task_id}/script/confirm")
async def confirm_script(
    task_id: str, req: ScriptConfirmRequest, user: User = Depends(get_current_user),
) -> dict:
    """Gate 2:确认脚本(可携带编辑),继续执行后续 Pipeline(分镜/Prompt/生成)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.SCRIPT_REVIEW:
        raise HTTPException(409, "当前任务不在脚本待确认阶段")
    asyncio.create_task(orchestrator.confirm_script(state, edited_script=req.script))
    return {"task_id": task_id, "status": "CONFIRMING", "message": "脚本已确认,正在继续生成"}


@router.post("/tasks/{task_id}/script/regenerate")
async def regenerate_script(
    task_id: str, req: RegenerateRequest | None = None, user: User = Depends(get_current_user),
) -> dict:
    """Gate 2:重新生成脚本草稿(替换当前待确认脚本,可携带用户反馈)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.SCRIPT_REVIEW:
        raise HTTPException(409, "当前任务不在脚本待确认阶段")
    feedback = req.feedback if req else None
    asyncio.create_task(orchestrator.regenerate_script(state, feedback=feedback))
    return {"task_id": task_id, "status": "SCRIPTING", "message": "正在重新生成脚本"}


class SceneAIRequest(BaseModel):
    """Gate 2 剧本局部 AI 操作:续写/改写/扩写/缩写单个场景。"""
    scene_index: int = Field(..., description="目标场景索引(0 起)")
    action: str = Field(..., description="操作: continue(续写新场景) / rewrite(改写) / expand(扩写) / condense(缩写)")
    instruction: str | None = Field(None, description="用户具体要求(可选),如'对白更幽默'")
    scene: dict = Field(..., description="当前场景草稿(用户可能已编辑,以此为准)")


@router.post("/tasks/{task_id}/script/scene-ai")
async def script_scene_ai(
    task_id: str, req: SceneAIRequest, user: User = Depends(get_current_user),
) -> dict:
    """Gate 2:剧本局部 AI(续写/改写/扩写/缩写)。

    同步返回 AI 结果场景(不写库):前端更新审核草稿,用户继续编辑,
    确认时经 script/confirm 全量提交 —— 用户始终保有最终编辑权。
    """
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.SCRIPT_REVIEW:
        raise HTTPException(409, "当前任务不在脚本待确认阶段")
    if req.action not in ("continue", "rewrite", "expand", "condense"):
        raise HTTPException(400, f"不支持的操作: {req.action}")
    if not state.script or not (0 <= req.scene_index < len(state.script.scenes)):
        raise HTTPException(400, f"场景索引越界: {req.scene_index}")

    # 组装上下文:目标场景(用户草稿)+ 前后场景摘要 + 作品设定
    scenes = state.script.scenes
    context: dict = {
        "action": req.action,
        "script_title": state.script.title,
        "scene": req.scene,
        "scene_position": f"第 {req.scene_index + 1} / {len(scenes)} 场",
    }
    if req.scene_index > 0:
        prev = scenes[req.scene_index - 1]
        context["previous_scene_summary"] = {
            "location": prev.location, "visual": prev.visual,
            "dialogue": prev.dialogue, "voiceover": prev.voiceover,
        }
    if req.scene_index < len(scenes) - 1:
        nxt = scenes[req.scene_index + 1]
        context["next_scene_summary"] = {
            "location": nxt.location, "visual": nxt.visual,
            "dialogue": nxt.dialogue, "voiceover": nxt.voiceover,
        }
    if req.instruction:
        context["instruction"] = req.instruction
    # 作品设定注入:人物一致性(姓名/性格/服装)是局部改写的核心约束
    ps = state.project_state
    if ps is not None:
        if ps.character_state.bibles:
            context["characters"] = [
                {"name": b.name, "identity": b.identity, "personality": b.personality,
                 "appearance": b.appearance, "clothing": b.clothing}
                for b in ps.character_state.bibles
            ]
        if ps.story_state.beats:
            context["story_theme"] = ps.story_state.theme

    llm = get_llm_provider()
    data = await llm.generate(task="script_scene_ai", context=context)
    # 基础字段防御:缺失字段补默认,保证前端草稿结构完整
    data.setdefault("scene_id", req.scene_index + 2 if req.action == "continue" else req.scene_index + 1)
    data.setdefault("duration", scenes[req.scene_index].duration)
    for k in ("location", "visual", "dialogue", "voiceover"):
        data.setdefault(k, "")
    data.setdefault("characters", [])
    return {"task_id": task_id, "action": req.action, "scene": data}


@router.post("/tasks/{task_id}/storyboard/confirm")
async def confirm_storyboard(
    task_id: str, req: StoryboardConfirmRequest, user: User = Depends(get_current_user),
) -> dict:
    """Gate 3:确认分镜(可携带编辑),继续执行后续 Pipeline(Prompt/生成)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.STORYBOARD_REVIEW:
        raise HTTPException(409, "当前任务不在分镜待确认阶段")
    asyncio.create_task(orchestrator.confirm_storyboard(state, edited_storyboard=req.storyboard))
    return {"task_id": task_id, "status": "CONFIRMING", "message": "分镜已确认,正在继续生成"}


@router.post("/tasks/{task_id}/storyboard/regenerate")
async def regenerate_storyboard(
    task_id: str, req: StoryboardRegenerateRequest | None = None, user: User = Depends(get_current_user),
) -> dict:
    """Gate 3:重新生成分镜(整体或单个镜头)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.STORYBOARD_REVIEW:
        raise HTTPException(409, "当前任务不在分镜待确认阶段")
    shot_index = req.shot_index if req else None
    feedback = req.feedback if req else None
    if shot_index is not None:
        n = len(state.storyboard.shots) if state.storyboard else 0
        if not (0 <= shot_index < n):
            raise HTTPException(400, f"镜头索引越界: {shot_index}(共 {n} 个镜头)")
        asyncio.create_task(orchestrator.regenerate_shot(state, shot_index, feedback=feedback))
        return {"task_id": task_id, "status": "STORYBOARDING", "message": f"正在重新生成镜头 {shot_index + 1}"}
    asyncio.create_task(orchestrator.regenerate_storyboard(state, feedback=feedback))
    return {"task_id": task_id, "status": "STORYBOARDING", "message": "正在重新生成分镜"}


@router.post("/tasks/{task_id}/prompt/confirm")
async def confirm_prompt(
    task_id: str, req: PromptConfirmRequest, user: User = Depends(get_current_user),
) -> dict:
    """Gate 4:确认 Prompt(可携带编辑),继续执行后续 Pipeline(媒体生成)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.PROMPT_REVIEW:
        raise HTTPException(409, "当前任务不在 Prompt 待确认阶段")
    asyncio.create_task(orchestrator.confirm_prompt(state, edited_result=req.prompt_result))
    return {"task_id": task_id, "status": "CONFIRMING", "message": "Prompt 已确认,正在开始生成"}


@router.post("/tasks/{task_id}/prompt/regenerate")
async def regenerate_prompt(
    task_id: str, req: RegenerateRequest | None = None, user: User = Depends(get_current_user),
) -> dict:
    """Gate 4:重新编译 Prompt 草稿(可携带用户反馈定向修改)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.PROMPT_REVIEW:
        raise HTTPException(409, "当前任务不在 Prompt 待确认阶段")
    feedback = req.feedback if req else None
    asyncio.create_task(orchestrator.regenerate_prompt(state, feedback=feedback))
    return {"task_id": task_id, "status": "GENERATING_ASSETS", "message": "正在重新编译 Prompt"}


@router.post("/tasks/{task_id}/model/select")
async def select_model(
    task_id: str, req: ModelSelectRequest, user: User = Depends(get_current_user),
) -> dict:
    """Gate 4:手动切换视频模型,按新模型能力重新编译 Prompt(模型感知)。"""
    from ..router.model_registry import registry

    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.PROMPT_REVIEW:
        raise HTTPException(409, "当前任务不在 Prompt 待确认阶段")
    entry = registry.get(req.model_id)
    if entry is None or entry.model_type not in ("image_to_video", "text_to_video"):
        raise HTTPException(400, f"模型不可用或不支持视频生成: {req.model_id}")
    asyncio.create_task(orchestrator.switch_model(state, model_id=req.model_id))
    return {"task_id": task_id, "status": "GENERATING_ASSETS", "message": f"已切换模型,正在按新模型重新编译 Prompt"}


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str, req: TaskRetryRequest, user: User = Depends(get_current_user),
) -> dict:
    """失败重试:从失败阶段恢复执行,已完成阶段的产物(脚本/分镜/Prompt/素材)保留。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.FAILED:
        raise HTTPException(409, "仅失败任务可重试")
    asyncio.create_task(orchestrator.retry(state))
    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": "已开始重试,将从失败阶段恢复,已完成部分不会重新生成",
    }


class SubtitleUpdateItem(BaseModel):
    """单条字幕编辑。"""
    shot_index: int
    text: Optional[str] = None
    enabled: Optional[bool] = None
    font_size: Optional[int] = None


class SubtitleUpdateRequest(BaseModel):
    """字幕批量编辑:更新后自动重新合成(新版本)。"""
    items: list[SubtitleUpdateItem]


def _timeline_payload(state) -> list[dict]:
    """时间轴视图:优先已构建 timeline,无则按分镜推算时段。"""
    if state.timeline:
        return [seg.model_dump() for seg in state.timeline]
    if state.storyboard is None:
        return []
    t = 0.0
    out = []
    for i, shot in enumerate(state.storyboard.shots):
        d = float(max(shot.duration, 1))
        out.append({
            "shot_index": i, "start": t, "end": t + d, "duration": d,
            "narration_path": shot.audio_path, "narration_duration": None,
            "subtitle_text": shot.subtitle or shot.voiceover or shot.visual_description or "",
            "subtitle_enabled": shot.subtitle_enabled,
        })
        t += d
    return out


@router.get("/tasks/{task_id}/timeline")
async def get_timeline(task_id: str, user: User = Depends(get_current_user)) -> dict:
    """音轨时间轴:每个镜头在成片中的时段、旁白与字幕绑定。"""
    state = await _get_owned_or_404(task_id, user)
    return {
        "task_id": task_id,
        "segments": _timeline_payload(state),
        "bgm": next((a for a in state.assets if a.endswith("_bgm.wav")), None),
        "total_duration": sum(s.duration for s in state.storyboard.shots) if state.storyboard else 0,
    }


@router.get("/tasks/{task_id}/subtitles")
async def get_subtitles(task_id: str, user: User = Depends(get_current_user)) -> dict:
    """字幕列表(逐镜头):文本/开关/字号/时段。"""
    state = await _get_owned_or_404(task_id, user)
    items = []
    for seg in _timeline_payload(state):
        shot = state.storyboard.shots[seg["shot_index"]]
        items.append({
            "shot_index": seg["shot_index"],
            "text": shot.subtitle or shot.voiceover or shot.visual_description or "",
            "enabled": shot.subtitle_enabled,
            "font_size": shot.subtitle_font_size,
            "start": seg["start"],
            "end": seg["end"],
        })
    return {"task_id": task_id, "items": items}


@router.put("/tasks/{task_id}/subtitles")
async def update_subtitles(
    task_id: str, req: SubtitleUpdateRequest, user: User = Depends(get_current_user),
) -> dict:
    """字幕逐条编辑(文本/是否烧录/字号):更新后自动重新合成为新版本。"""
    state = await _get_owned_or_404(task_id, user)
    if state.storyboard is None:
        raise HTTPException(409, "任务尚无分镜,无法编辑字幕")
    asyncio.create_task(
        orchestrator.update_subtitles(state, [i.model_dump() for i in req.items])
    )
    return {"task_id": task_id, "status": "ASSEMBLING", "message": "字幕已更新,正在重新合成新版本"}


@router.get("/tasks/{task_id}/subtitles/export")
async def export_subtitles(task_id: str, user: User = Depends(get_current_user)) -> StreamingResponse:
    """导出 SRT 字幕文件(按音轨时间轴)。"""
    state = await _get_owned_or_404(task_id, user)
    srt = orchestrator.export_srt(state)
    return StreamingResponse(
        iter([srt.encode("utf-8")]),
        media_type="application/x-subrip",
        headers={"Content-Disposition": f'attachment; filename="{task_id}.srt"'},
    )


@router.post("/tasks/{task_id}/shots/impact")
async def analyze_shot_impact(
    task_id: str, req: ShotReviseRequest, user: User = Depends(get_current_user),
) -> dict:
    """依赖图影响预览:修改指定镜头后,哪些内容会/不会受影响(不执行重生成)。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.COMPLETED:
        raise HTTPException(409, "局部修改仅在视频完成后可用")
    if state.storyboard is None:
        raise HTTPException(400, "任务没有分镜数据")
    n = len(state.storyboard.shots)
    for i in req.shot_indices:
        if not (0 <= i < n):
            raise HTTPException(400, f"镜头索引越界: {i}(共 {n} 个镜头)")
    impact = orchestrator.analyze_dependencies(state, req.shot_indices)
    return {
        "task_id": task_id,
        "affected": [i + 1 for i in impact["affected"]],
        "unaffected": [i + 1 for i in impact["unaffected"]],
        "locked": [i + 1 for i in impact["locked"]],
        "message": (
            f"将重新生成镜头 {[i + 1 for i in impact['affected']]} 的 Prompt/图片/音视频并重新合成;"
            f"镜头 {[i + 1 for i in impact['unaffected']]} 保持不变"
            if impact["affected"] else "所有镜头已锁定,不会重新生成"
        ),
    }


@router.post("/tasks/{task_id}/shots/{shot_index}/lock")
async def toggle_shot_lock(
    task_id: str, shot_index: int, req: ShotLockRequest, user: User = Depends(get_current_user),
) -> dict:
    """锁定/解锁单个镜头:锁定后局部重生成不会修改该镜头。"""
    state = await _get_owned_or_404(task_id, user)
    if state.storyboard is None or not (0 <= shot_index < len(state.storyboard.shots)):
        raise HTTPException(400, f"镜头索引越界: {shot_index}")
    await orchestrator.toggle_shot_lock(state, shot_index, locked=req.locked)
    return {"task_id": task_id, "shot_index": shot_index, "locked": req.locked}


@router.post("/tasks/{task_id}/shots/revise")
async def revise_shots(
    task_id: str, req: ShotReviseRequest, user: User = Depends(get_current_user),
) -> dict:
    """局部重生成:仅重新生成受影响镜头的 Prompt/图/音/视频,未受影响镜头复用既有素材。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.COMPLETED:
        raise HTTPException(409, "局部修改仅在视频完成后可用")
    if state.storyboard is None:
        raise HTTPException(400, "任务没有分镜数据")
    n = len(state.storyboard.shots)
    for i in req.shot_indices:
        if not (0 <= i < n):
            raise HTTPException(400, f"镜头索引越界: {i}(共 {n} 个镜头)")
    asyncio.create_task(orchestrator.revise_shots(state, req.shot_indices, edits=req.edits, feedback=req.feedback))
    return {"task_id": task_id, "status": "GENERATING_ASSETS", "message": "正在局部重新生成受影响内容"}


@router.post("/tasks/{task_id}/scenes/{scene_index}/impact")
async def analyze_scene_impact(
    task_id: str, scene_index: int, user: User = Depends(get_current_user),
) -> dict:
    """Scene 级依赖影响预览:修改指定脚本场景后,哪些镜头链路会/不会受影响(不执行重生成)。

    依赖传播:Scene 编辑 → 关联 Shot(scene_id) → Shot Prompt → 关键帧图 → I2V 片段 → 重新合成。
    """
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.COMPLETED:
        raise HTTPException(409, "局部修改仅在视频完成后可用")
    if state.script is None or not (0 <= scene_index < len(state.script.scenes)):
        raise HTTPException(400, f"场景索引越界: {scene_index}")
    impact = orchestrator.analyze_scene_dependencies(state, scene_index)
    return {
        "task_id": task_id,
        "scene_index": scene_index,
        "scene_id": scene_index + 1,
        "affected": [i + 1 for i in impact["affected"]],
        "unaffected": [i + 1 for i in impact["unaffected"]],
        "locked": [i + 1 for i in impact["locked"]],
        "message": (
            f"将重新生成场景 {scene_index + 1} 关联镜头 {[i + 1 for i in impact['affected']]} "
            f"的分镜/Prompt/图片/音视频并重新合成;其余镜头保持不变"
            if impact["affected"] else "该场景没有关联的可重生成镜头(可能全部被锁定)"
        ),
    }


@router.post("/tasks/{task_id}/scenes/{scene_index}/revise")
async def revise_scene(
    task_id: str, scene_index: int, req: SceneReviseRequest, user: User = Depends(get_current_user),
) -> dict:
    """Scene 级局部重生成:应用场景编辑后,仅重生成该场景关联镜头的完整链路,其余镜头素材复用。"""
    state = await _get_owned_or_404(task_id, user)
    if state.status != TaskStatus.COMPLETED:
        raise HTTPException(409, "局部修改仅在视频完成后可用")
    if state.script is None or not (0 <= scene_index < len(state.script.scenes)):
        raise HTTPException(400, f"场景索引越界: {scene_index}")
    asyncio.create_task(orchestrator.revise_scene(
        state, scene_index, scene_edits=req.scene_edits, feedback=req.feedback,
    ))
    return {"task_id": task_id, "status": "GENERATING_ASSETS", "message": "正在按场景局部重新生成受影响内容"}


@router.get("/search")
async def search_videos(
    q: str = Query(..., description="自然语言搜索查询"),
    top_k: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """自然语言语义搜索历史视频,按相似度排序。"""
    results = await video_searcher.search(query=q, user_id=user.id, top_k=top_k)
    return [
        {
            "video_id": r["video_id"],
            "score": r["score"],
            "semantic_description": r["semantic_description"],
            "metadata": r["metadata"],
            "video_url": (
                f"/storage/videos/{os.path.basename(r['metadata']['video_path'])}"
                if r.get("metadata", {}).get("video_path") else None
            ),
        }
        for r in results
    ]


async def _get_owned_or_404(task_id: str, user: User) -> VideoGenerationState:
    state = await task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if state.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该任务")
    return state


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user: User = Depends(get_current_user)) -> dict:
    state = await _get_owned_or_404(task_id, user)
    return state.model_dump()


@router.get("/tasks/{task_id}/status")
async def get_status(task_id: str, user: User = Depends(get_current_user)) -> dict:
    state = await _get_owned_or_404(task_id, user)
    return {
        "task_id": state.task_id,
        "status": state.status.value,
        "logs": [l.model_dump() for l in state.logs],
        "error": state.error,
        "failure_detail": state.failure_detail,
        "model_used": state.model_used,
        "routing_decision": state.routing_decision,
        "image_model_used": state.image_model_used,
        "image_routing_decision": state.image_routing_decision,
        "voice_model_used": state.voice_model_used,
        "creative_intent": state.creative_intent.model_dump() if state.creative_intent else None,
        "prompt_engineering_result": state.prompt_engineering_result,
    }


@router.get("/tasks/{task_id}/result")
async def get_result(task_id: str, user: User = Depends(get_current_user)) -> dict:
    state = await _get_owned_or_404(task_id, user)
    video_file = os.path.basename(state.video_path) if state.video_path else None
    return {
        "task_id": state.task_id,
        "status": state.status.value,
        "video_path": state.video_path,
        "video_url": f"/storage/videos/{video_file}" if video_file else None,
        "video_versions": [
            {
                "version": v.version,
                "url": f"/storage/videos/{os.path.basename(v.path)}",
                "reason": v.reason,
                "ts": v.ts,
                "current": v.path == state.video_path,
            }
            for v in state.video_versions
        ],
        "title": state.script.title if state.script else None,
        "created_at": state.created_at,
        "model_used": state.model_used,
        "routing_decision": state.routing_decision,
        "image_model_used": state.image_model_used,
        "image_routing_decision": state.image_routing_decision,
        "voice_model_used": state.voice_model_used,
        "creative_intent": state.creative_intent.model_dump() if state.creative_intent else None,
        "prompt_engineering_result": state.prompt_engineering_result,
        "requirement": state.requirement.model_dump() if state.requirement else None,
        "script": state.script.model_dump() if state.script else None,
        "storyboard": state.storyboard.model_dump() if state.storyboard else None,
        "project_state": state.project_state.model_dump() if state.project_state else None,
        "compliance_report": state.compliance_report,
        "content_guard_report": state.content_guard_report,
        "quality_report": state.quality_report,
        "revision_count": state.revision_count,
        "human_review_required": state.human_review_required,
        "failure_detail": state.failure_detail,
    }


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str, user: User = Depends(get_current_user_sse)) -> StreamingResponse:
    await _get_owned_or_404(task_id, user)

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
                    "model_used": state.model_used,
                    "routing_decision": state.routing_decision,
                    "image_model_used": state.image_model_used,
                    "image_routing_decision": state.image_routing_decision,
                    "voice_model_used": state.voice_model_used,
                    "creative_intent": state.creative_intent.model_dump() if state.creative_intent else None,
                    "prompt_engineering_result": state.prompt_engineering_result,
                    "requirement": state.requirement.model_dump() if state.requirement else None,
                    "script": state.script.model_dump() if state.script else None,
                    "storyboard": state.storyboard.model_dump() if state.storyboard else None,
                    "project_state": state.project_state.model_dump() if state.project_state else None,
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


# ---- 文件上传 ----

upload_router = APIRouter(prefix="/api/upload", tags=["upload"])

_ALLOWED_IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_ALLOWED_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@upload_router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_IMAGE:
        raise HTTPException(400, f"不支持的图片格式: {ext}")
    data = await file.read()
    if len(data) > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(413, f"文件过大,上限 {settings.upload_max_size_mb}MB")
    upload_dir = storage_dir("uploads")
    save_name = f"{user.id}_{int(time.time() * 1000)}{ext}"
    save_path = os.path.join(str(upload_dir), save_name)
    with open(save_path, "wb") as f:
        f.write(data)
    return {"file_path": save_path, "file_name": file.filename, "size": len(data)}


@upload_router.post("/video")
async def upload_video(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_VIDEO:
        raise HTTPException(400, f"不支持的视频格式: {ext}")
    data = await file.read()
    if len(data) > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(413, f"文件过大,上限 {settings.upload_max_size_mb}MB")
    upload_dir = storage_dir("uploads")
    save_name = f"{user.id}_{int(time.time() * 1000)}{ext}"
    save_path = os.path.join(str(upload_dir), save_name)
    with open(save_path, "wb") as f:
        f.write(data)
    return {"file_path": save_path, "file_name": file.filename, "size": len(data)}


# ======================== 依赖图 + 版本控制 ========================

@router.get("/dependency-graph")
async def get_dependency_graph(user: User = Depends(get_current_user)) -> dict:
    """获取当前 Pipeline 依赖图。"""
    return dependency_graph.to_dict()


@router.get("/dependency-graph/affected")
async def get_affected_nodes(
    node: str = Query(..., description="发生变化的节点 ID"),
    user: User = Depends(get_current_user),
) -> dict:
    """计算受影响的下游节点。"""
    return dependency_graph.compute_affected_detail(node)


# ======================== 版本控制(任务级) ========================

@router.get("/tasks/{task_id}/versions")
async def list_task_versions(
    task_id: str, user: User = Depends(get_current_user),
) -> dict:
    """列出任务内有版本历史的关键节点。"""
    state = await _get_owned_or_404(task_id, user)
    return {"task_id": task_id, "nodes": state.list_versioned_nodes()}


class ProjectStateUpdateRequest(BaseModel):
    """作品设定(Bible)整体更新:用户编辑后的完整 ProjectState 结构。"""
    project_state: dict = Field(..., description="完整 ProjectState 结构(前端编辑后的全量数据)")


@router.put("/tasks/{task_id}/project-state")
async def update_project_state(
    task_id: str,
    body: ProjectStateUpdateRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """更新作品设定(故事/人物/世界观/风格)。

    仅允许在审核 Gate 或终态编辑(避免与进行中的 Agent 写入竞争);
    编辑后的设定作为后续阶段(分镜/Prompt/生成)的上下文。
    """
    state = await _get_owned_or_404(task_id, user)
    editable = {"SCRIPT_REVIEW", "STORYBOARD_REVIEW", "PROMPT_REVIEW", "COMPLETED", "FAILED", "HUMAN_REVIEW"}
    if state.status.value not in editable:
        raise HTTPException(409, "任务处理中,暂不能编辑作品设定,请等待当前阶段完成")
    from ..director.project_state import ProjectState

    try:
        state.project_state = ProjectState.model_validate(body.project_state)
    except Exception as e:
        raise HTTPException(422, f"作品设定数据不合法: {e}")
    state.append_log(state.status, "作品设定已更新(用户编辑)")
    await task_store.save(state)
    return {"task_id": task_id, "updated": True}


@router.get("/tasks/{task_id}/versions/{node_type}")
async def get_task_version_history(
    task_id: str,
    node_type: str,
    include_data: bool = Query(False, description="是否包含版本快照数据"),
    user: User = Depends(get_current_user),
) -> dict:
    """获取任务内指定节点的版本历史(倒序,最新在前)。"""
    from ..models.state import VERSIONED_NODES

    if node_type not in VERSIONED_NODES:
        raise HTTPException(400, f"不支持版本控制的节点: {node_type}(可选: {list(VERSIONED_NODES)})")
    state = await _get_owned_or_404(task_id, user)
    return {"task_id": task_id, "node_type": node_type, "versions": state.get_versions(node_type, include_data=include_data)}


@router.post("/tasks/{task_id}/versions/{node_type}/restore/{version}")
async def restore_task_version(
    task_id: str, node_type: str, version: int,
    user: User = Depends(get_current_user),
) -> dict:
    """恢复指定版本:把历史快照写回任务当前内容,后续操作(重新生成/局部修改)将基于该版本。

    恢复动作本身也会记入版本历史(reason=版本回退),保证可追溯。
    """
    from ..models.state import VERSIONED_NODES

    if node_type not in VERSIONED_NODES:
        raise HTTPException(400, f"不支持版本控制的节点: {node_type}")
    state = await _get_owned_or_404(task_id, user)
    entry = state.find_version(node_type, version)
    if entry is None:
        raise HTTPException(404, f"版本不存在: {node_type} v{version}")

    try:
        if node_type == "creative_intent":
            from ..schemas.creative_intent import CreativeIntent
            state.creative_intent = CreativeIntent(**entry.data)
        elif node_type == "script":
            from ..schemas.script import VideoScript
            state.script = VideoScript(**entry.data)
        elif node_type == "storyboard":
            from ..schemas.storyboard import Storyboard
            state.storyboard = Storyboard(**entry.data)
        elif node_type == "prompt":
            state.prompt_engineering_result = entry.data
    except Exception as e:
        raise HTTPException(500, f"版本数据无法恢复(结构不兼容): {e}")

    state.save_version(node_type, entry.data, label=entry.label, reason=f"回退自 v{version}")
    state.append_log(state.status, f"已恢复{VERSIONED_NODES[node_type]} v{version}(来自 {entry.reason})")
    await task_store.save(state)
    return {
        "task_id": task_id, "node_type": node_type, "version": version,
        "restored": True,
        "message": f"已恢复{VERSIONED_NODES[node_type]} v{version},可基于该版本继续重新生成",
    }
