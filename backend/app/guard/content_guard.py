"""ContentGuard 核心实现:三维度内容风险预检查。

通过 LLM 对 storyboard 的 image_prompt / video_prompt / voiceover / subtitle / visual_description
做语义评估,输出三维度风险等级 + 修改建议。

调用约定:
- 复用 LLMProvider(同 qwen-plus),不接外部 API
- CONTENT_GUARD_PROMPT 约束输出 JSON schema
- 失败时返回 safe=False + human_review_required(进入人工审核,不自动放行)
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from ..models.state import VideoGenerationState
from ..providers.llm.base import LLMProvider

RiskLevel = Literal["low", "medium", "high"]


class ContentGuardReport(BaseModel):
    """ContentGuard 风险评估报告。"""

    safe: bool = Field(False, description="整体是否可放行(需 LLM 确认 low/medium 风险后才设 True)")
    overall_risk: RiskLevel = Field("low", description="整体风险等级")
    safety_risk: RiskLevel = Field("low", description="内容安全风险(违法/色情/暴力/毒品/赌博/欺诈)")
    platform_risk: RiskLevel = Field("low", description="平台审核风险(敏感议题/严重争议)")
    cultural_risk: RiskLevel = Field("low", description="文化/历史一致性风险(时代错误/服饰不匹配/文化误导)")
    warnings: List[str] = Field(default_factory=list, description="风险提示(用'内容风险/平台风险/文化历史一致性风险'措辞,不说'违法')")
    suggestions: List[str] = Field(default_factory=list, description="具体修改建议")


class ContentGuard:
    """内容风险预检查器(独立模块,不继承 BaseAgent,不增加 Agent 数量)。"""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def check(self, state: VideoGenerationState) -> ContentGuardReport:
        """对 storyboard 内容做三维度风险评估。

        在 _run_media 之前调用,避免高风险内容消耗素材生成 API。
        LLM 调用失败时返回 safe=False(进入人工审核,不自动放行)。
        """
        if state.storyboard is None:
            return ContentGuardReport(
                safe=False,
                warnings=["storyboard 未生成,无法进行风险预检查"],
            )

        # 提取需评估的内容字段
        shots_payload = []
        for i, shot in enumerate(state.storyboard.shots):
            shots_payload.append({
                "index": i,
                "image_prompt": shot.image_prompt,
                "video_prompt": shot.video_prompt,
                "voiceover": shot.voiceover,
                "subtitle": shot.subtitle,
                "visual_description": shot.visual_description,
                "character_action": shot.character_action,
            })

        context = {
            "title": state.script.title if state.script else "",
            "user_input": state.user_input,
            "shots": shots_payload,
        }

        try:
            data = await self.llm.generate(task="content_guard", context=context)
            report = ContentGuardReport(**data)
            # overall_risk=high 时 safe 自动设 False(可被 LLM 输出覆盖)
            if report.overall_risk == "high" and report.safe:
                report.safe = False
            return report
        except Exception as e:
            # LLM 调用失败:返回 safe=False,进入人工审核,不自动放行
            return ContentGuardReport(
                safe=False,
                overall_risk="medium",
                warnings=[f"ContentGuard 预检查异常(LLM 不可用): {type(e).__name__}: {e}"],
                suggestions=["请检查 LLM API Key 和账户状态后重试"],
            )
