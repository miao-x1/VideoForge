"""Pipeline 状态机与任务状态。

VideoGenerationState 是贯穿整个 Orchestrator 的可变状态对象，
记录从用户输入到最终 MP4 产出的全部中间产物与执行轨迹。
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ..schemas.requirement import StructuredRequirement
from ..schemas.script import VideoScript
from ..schemas.storyboard import Storyboard


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"  # 需求理解中
    SCRIPTING = "SCRIPTING"  # 脚本生成中
    COMPLIANCE_CHECKING = "COMPLIANCE_CHECKING"  # 合规预审中
    STORYBOARDING = "STORYBOARDING"  # 分镜生成中
    GENERATING_ASSETS = "GENERATING_ASSETS"  # 素材生成中
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
    TaskStatus.STORYBOARDING: "正在生成分镜",
    TaskStatus.GENERATING_ASSETS: "正在生成素材",
    TaskStatus.ASSEMBLING: "正在合成视频",
    TaskStatus.COMPLETED: "视频生成完成",
    TaskStatus.FAILED: "生成失败",
    TaskStatus.HUMAN_REVIEW: "需人工审核",
}


class LogEntry(BaseModel):
    ts: float = Field(default_factory=time.time)
    status: TaskStatus
    message: str


class VideoGenerationState(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_input: str
    duration: int = 30
    style: str = ""
    aspect_ratio: str = "9:16"
    compliance_enabled: bool = Field(True, description="任务级合规预审开关(False 跳过 Compliance Agent)")

    # 各阶段产物
    requirement: Optional[StructuredRequirement] = None
    script: Optional[VideoScript] = None
    storyboard: Optional[Storyboard] = None
    assets: List[str] = Field(default_factory=list, description="生成的素材文件路径列表")
    video_path: Optional[str] = None
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

    def mark_failed(self, message: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = message
        self.logs.append(LogEntry(status=TaskStatus.FAILED, message=message))
        self.updated_at = time.time()
