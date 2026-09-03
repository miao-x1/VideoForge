"""Pipeline 状态机与任务状态。

VideoGenerationState 是贯穿整个 Orchestrator 的可变状态对象，
记录从用户输入到最终 MP4 产出的全部中间产物与执行轨迹。
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.requirement import StructuredRequirement
from ..schemas.script import VideoScript
from ..schemas.specification import VideoSpecification
from ..schemas.storyboard import Storyboard
from ..schemas.creative_intent import CreativeIntent
from ..schemas.structured_prompt import PromptEngineeringResult
from ..director.project_state import ProjectState


class InputSourceItem(BaseModel):
    """用户提供的多模态输入项(文本/图片/视频/URL)。"""
    type: str = Field(..., description="输入类型: text/image/video/url")
    content: str = Field(..., description="文本内容/文件路径/URL")
    purpose: str = Field("overall", description="参考用途: subject/scene/style/camera/action/overall 等")


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"  # 需求理解中
    SCRIPTING = "SCRIPTING"  # 脚本生成中
    COMPLIANCE_CHECKING = "COMPLIANCE_CHECKING"  # 合规预审中
    SCRIPT_REVIEW = "SCRIPT_REVIEW"  # 脚本待用户确认(Gate 2,AI协作/专业模式)
    STORYBOARDING = "STORYBOARDING"  # 分镜生成中
    STORYBOARD_REVIEW = "STORYBOARD_REVIEW"  # 分镜待用户确认(Gate 3,AI协作/专业模式)
    GENERATING_ASSETS = "GENERATING_ASSETS"  # 素材生成中
    PROMPT_REVIEW = "PROMPT_REVIEW"  # Prompt待用户确认(Gate 4,AI协作/专业模式)
    ASSEMBLING = "ASSEMBLING"  # 视频合成中
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HUMAN_REVIEW = "HUMAN_REVIEW"  # 需人工审核(合规不通过且修订耗尽)


# 每个 status 对应的中文进度文案，前端时间线直接映射
STATUS_LABELS = {
    TaskStatus.PENDING: "任务已创建",
    TaskStatus.ANALYZING: "正在理解视频需求",
    TaskStatus.SCRIPTING: "正在生成脚本",
    TaskStatus.COMPLIANCE_CHECKING: "正在内容合规预审",
    TaskStatus.SCRIPT_REVIEW: "脚本待确认",
    TaskStatus.STORYBOARDING: "正在生成分镜",
    TaskStatus.STORYBOARD_REVIEW: "分镜待确认",
    TaskStatus.GENERATING_ASSETS: "正在生成素材",
    TaskStatus.PROMPT_REVIEW: "Prompt待确认",
    TaskStatus.ASSEMBLING: "正在合成视频",
    TaskStatus.COMPLETED: "视频生成完成",
    TaskStatus.FAILED: "生成失败",
    TaskStatus.HUMAN_REVIEW: "需人工审核",
}


class LogEntry(BaseModel):
    ts: float = Field(default_factory=time.time)
    status: TaskStatus
    message: str


# 支持版本控制的关键节点类型
VERSIONED_NODES = {
    "creative_intent": "创作方案",
    "script": "脚本",
    "storyboard": "分镜",
    "prompt": "Prompt",
}


class NodeVersion(BaseModel):
    """单个节点的版本快照:随 state_json 持久化,任务级隔离。"""

    version: int
    ts: float = Field(default_factory=time.time)
    node_type: str  # creative_intent | script | storyboard | prompt
    label: str = ""
    reason: str = ""  # 变更原因(初始生成/用户编辑/重新生成/局部修改)
    data: dict = Field(default_factory=dict)  # 产物快照


class VideoVersion(BaseModel):
    """成片视频的文件版本:每次合成产生新文件,旧文件保留可回看。"""

    version: int
    path: str
    ts: float = Field(default_factory=time.time)
    reason: str = ""  # 初始合成 / 局部修改 / 重新生成


class TimelineSegment(BaseModel):
    """音轨时间轴:成片内单个镜头的时段与音轨绑定。"""

    shot_index: int
    start: float  # 成片内起始秒
    end: float  # 成片内结束秒
    duration: float
    narration_path: Optional[str] = None
    narration_duration: Optional[float] = None
    subtitle_text: str = ""
    subtitle_enabled: bool = True


class VideoGenerationState(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = ""
    user_input: str
    duration: int = 30
    style: str = ""
    aspect_ratio: str = "9:16"
    compliance_enabled: bool = Field(True, description="任务级合规预审开关(False 跳过 Compliance Agent)")
    input_sources: List[InputSourceItem] = Field(default_factory=list, description="多模态输入源列表")
    multimodal_context: str = Field("", description="多模态输入理解后的文本上下文(注入 RequirementAgent)")
    spec: Optional[VideoSpecification] = Field(None, description="结构化创作意图(VideoSpecification)")
    mode: str = Field("quick", description="创作模式: quick(快速创作) / collaborative(AI协作) / professional(专业工作流)")
    review_gates: List[str] = Field(default_factory=list, description="需用户确认的关键节点(Human-in-the-loop Gate): script/storyboard/prompt")
    project_id: Optional[str] = Field(None, description="关联项目 ID(用于 Project Memory 维护)")
    project_state: Optional[ProjectState] = Field(
        None,
        description="作品级状态(AI Director 十二态:故事/人物/世界观/风格/场景/镜头/资产/生成/音频/剪辑/质检)",
    )
    version_history: List[NodeVersion] = Field(default_factory=list, description="关键节点版本历史(任务级,随 state_json 持久化)")

    # 各阶段产物
    requirement: Optional[StructuredRequirement] = None
    creative_intent: Optional[CreativeIntent] = Field(None, description="AI 对用户创意的深度理解(主体/场景/动作/情绪/风格/镜头/光线)")
    prompt_engineering_result: Optional[dict] = Field(None, description="Prompt Engineering Agent 输出(结构化Prompt/模型专用Prompt/negative_prompt)")
    script: Optional[VideoScript] = None
    storyboard: Optional[Storyboard] = None
    assets: List[str] = Field(default_factory=list, description="生成的素材文件路径列表")
    video_path: Optional[str] = None
    video_versions: List[VideoVersion] = Field(default_factory=list, description="成片视频文件版本(每次合成分文件保留,不覆盖)")
    timeline: List[TimelineSegment] = Field(default_factory=list, description="音轨时间轴:镜头时段/旁白/字幕绑定(合成时构建)")
    model_used: Optional[str] = Field(None, description="视频生成使用的模型名称")
    routing_decision: Optional[dict] = Field(None, description="模型路由决策(strategy/selected_provider/scored_models),供审计")
    image_model_used: Optional[str] = Field(None, description="图片生成使用的模型名称")
    image_routing_decision: Optional[dict] = Field(None, description="图片模型路由决策")
    voice_model_used: Optional[str] = Field(None, description="语音合成使用的模型名称")
    # 视频质量校验报告(Assembly 后由 validate_video 生成)
    quality_report: Optional[dict] = Field(None, description="VideoQualityReport 质量校验报告(grade/duration/resolution/has_audio/checks/...)")
    # ContentGuard 预检查报告(在 media 生成前评估三维度风险)
    content_guard_report: Optional[dict] = Field(None, description="ContentGuard 风险评估报告(safe/overall_risk/warnings/suggestions)")
    # Compliance Agent(脚本级合规预审):结构化报告 + 修订次数 + 人工审核标记
    compliance_report: Optional[dict] = Field(None, description="ComplianceResult 结构化报告(status/risk_level/violations/...)")
    compliance_audit: List[dict] = Field(default_factory=list, description="合规审核审计记录列表(每次检查/修订一条)")
    human_review_required: bool = Field(False, description="是否需要人工审核(review/reject 耗尽)")
    revision_count: int = Field(0, description="合规自动修订次数")

    # 运行时
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    failure_detail: Optional[dict] = Field(None, description="结构化失败信息(stage/reason/input_files),供前端展示失败降级")
    logs: List[LogEntry] = Field(default_factory=list)

    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def append_log(self, status: TaskStatus, message: str) -> None:
        self.logs.append(LogEntry(status=status, message=message))
        self.status = status
        self.updated_at = time.time()

    def get_or_create_project_state(self) -> ProjectState:
        """获取作品级状态,不存在则初始化(决策类 Agent 入口统一用此方法)。"""
        if self.project_state is None:
            self.project_state = ProjectState()
        return self.project_state

    def record_video_version(self, path: str, reason: str = "") -> int:
        """登记一次成片合成,返回版本号(文件由调用方按版本命名,旧文件不覆盖)。"""
        entry = VideoVersion(version=len(self.video_versions) + 1, path=path, reason=reason)
        self.video_versions.append(entry)
        return entry.version

    def save_version(self, node_type: str, data: dict, *, label: str = "", reason: str = "") -> int:
        """保存节点版本快照,返回版本号(同一 node_type 递增)。"""
        existing = [v for v in self.version_history if v.node_type == node_type]
        entry = NodeVersion(
            version=len(existing) + 1, node_type=node_type,
            label=label or VERSIONED_NODES.get(node_type, node_type),
            reason=reason, data=data,
        )
        self.version_history.append(entry)
        return entry.version

    def get_versions(self, node_type: str, *, include_data: bool = False) -> List[dict]:
        """获取节点版本历史(默认不含快照数据,倒序:最新在前)。"""
        out = []
        for v in self.version_history:
            if v.node_type != node_type:
                continue
            d = {"version": v.version, "ts": v.ts, "label": v.label, "reason": v.reason}
            if include_data:
                d["data"] = v.data
            out.append(d)
        return list(reversed(out))

    def list_versioned_nodes(self) -> List[dict]:
        """列出有版本历史的节点及最新版本信息。"""
        result = []
        for node_type, label in VERSIONED_NODES.items():
            versions = [v for v in self.version_history if v.node_type == node_type]
            if not versions:
                continue
            latest = versions[-1]
            result.append({
                "node_type": node_type, "label": label,
                "latest_version": latest.version, "version_count": len(versions),
                "latest_reason": latest.reason, "latest_ts": latest.ts,
            })
        return result

    def find_version(self, node_type: str, version: int) -> Optional[NodeVersion]:
        """查找指定版本快照。"""
        for v in self.version_history:
            if v.node_type == node_type and v.version == version:
                return v
        return None

    def mark_failed(self, message: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = message
        self.logs.append(LogEntry(status=TaskStatus.FAILED, message=message))
        self.updated_at = time.time()
