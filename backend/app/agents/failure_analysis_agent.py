"""FailureAnalysisAgent:生成失败的根因分析与修复决策(Agent 决策层)。

与传统 try/except 的区别(任务书第 10 节):
失败不是直接报错,而是结构化分析"为什么失败"并决策"下一步怎么修":
- 模式不被支持(MODE_UNSUPPORTED):T2V/R2V 在 I2V-only 模型上失败
  → 补关键帧降级为 I2V(add_keyframe),或首试直接切支持 T2V 的模型
- 瞬时错误(HTTP/轮询超时/限流):同参数重试(retry),第 2 次切厂商(switch_model)
- 账户/配置类(余额不足/Key 无效):本厂商不可修复 → 切厂商;无备选 → 人工介入(abort)
- 内容质检不通过(人物不一致/动作错位):重编译 prompt(regenerate_prompt)后再生成

决策是确定性的规则映射(可单测、可审计);Workflow 层只负责按决策执行
补帧/重试/切模型等固定动作,不做判断。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..core.logging import logger
from ..models.state import VideoGenerationState
from .base import BaseAgent

# ---- 修复动作 ----
ACTION_RETRY = "retry"                # 同参数重试(瞬时错误)
ACTION_ADD_KEYFRAME = "add_keyframe"  # 补关键帧 → 降级 I2V 重试
ACTION_SWITCH_MODEL = "switch_model"  # 切换厂商/模型重试
ACTION_REGENERATE_PROMPT = "regenerate_prompt"  # 内容问题:重编译 prompt 后再生成
ACTION_ABORT = "abort"                # 无自动修复路径,交人工

# 不可在本厂商修复、需要直接切厂商的错误码
_FATAL_PROVIDER_ERRORS = {
    "INSUFFICIENT_BALANCE",
    "INVALID_API_KEY",
    "ACCESS_DENIED",
    "PROVIDER_NOT_CONFIGURED",
    "PROVIDER_UNAVAILABLE",
    "MODEL_UNAVAILABLE",
}
# 瞬时错误:同参数重试通常可恢复
_TRANSIENT_ERRORS = {
    "HTTP_ERROR",
    "POLL_TIMEOUT",
    "POLL_ERROR",
    "RATE_LIMITED",
    "RATE_LIMIT",
    "GENERATION_FAILED",
    "PROVIDER_ERROR",
    "PIPELINE_ERROR",
}

MAX_AUTO_ATTEMPTS = 3  # 单镜头最大自动尝试次数(超过则 abort)


class RepairDecision(BaseModel):
    """单次失败的修复决策(Agent 产出,Workflow 执行)。"""

    action: str = Field(..., description="修复动作: retry/add_keyframe/switch_model/regenerate_prompt/abort")
    reason: str = Field("", description="根因分析:为什么失败、为什么这样修")
    force_mode: str = Field("", description="重试时强制的生成模式(如 add_keyframe 后强制 i2v)")
    repairable: bool = Field(True, description="是否存在自动修复路径")

    @property
    def should_abort(self) -> bool:
        return self.action == ACTION_ABORT


class FailureAnalysisAgent(BaseAgent):
    name = "failure_analysis"

    async def run(self, state: VideoGenerationState) -> None:
        """BaseAgent 接口:失败分析是事件驱动的,无全量 run 阶段(保留接口一致性)。"""
        return None

    def analyze_generation_failure(
        self,
        *,
        shot_index: int,
        error_code: str,
        error_message: str,
        mode: str,
        provider: str,
        attempt: int,
    ) -> RepairDecision:
        """分析视频生成失败,产出修复决策(纯规则,确定性)。

        attempt: 该镜头已经进行到第几次生成尝试(1-based,失败的这次计入)。
        """
        code = (error_code or "PROVIDER_ERROR").upper()

        # 0) 尝试次数耗尽 → 人工介入
        if attempt >= MAX_AUTO_ATTEMPTS:
            return RepairDecision(
                action=ACTION_ABORT,
                reason=f"镜头 {shot_index+1} 已自动尝试 {attempt} 次仍失败({code}),停止自动修复",
                repairable=False,
            )

        # 1) 模式不支持:补关键帧降级 I2V(T2V/R2V 镜头最常见的可修复失败)
        if code == "MODE_UNSUPPORTED":
            if mode in ("t2v", "r2v", ""):
                return RepairDecision(
                    action=ACTION_ADD_KEYFRAME,
                    force_mode="i2v",
                    reason=(
                        f"镜头 {shot_index+1} 规划为 {mode or 'T2V'} 但模型 {provider} 不支持"
                        f"(缺首帧/纯文生);补生成关键帧后降级 I2V 重试"
                    ),
                )
            return RepairDecision(
                action=ACTION_SWITCH_MODEL,
                reason=f"镜头 {shot_index+1} 模式 {mode} 在 {provider} 不可用且无法降级,尝试切换厂商",
            )

        # 2) 厂商致命错误(余额/Key/不可用):切厂商,无备选则上层 abort
        if code in _FATAL_PROVIDER_ERRORS:
            return RepairDecision(
                action=ACTION_SWITCH_MODEL,
                reason=f"镜头 {shot_index+1} 在 {provider} 遇到 {code}({error_message[:60]}),本厂商不可修复,切换备选厂商",
            )

        # 3) 瞬时错误:首次同参重试,之后切厂商
        if code in _TRANSIENT_ERRORS:
            if attempt == 1:
                return RepairDecision(
                    action=ACTION_RETRY,
                    reason=f"镜头 {shot_index+1} 遇到瞬时错误 {code},同参数重试一次",
                )
            return RepairDecision(
                action=ACTION_SWITCH_MODEL,
                reason=f"镜头 {shot_index+1} 瞬时错误 {code} 重试后仍失败,切换备选厂商",
            )

        # 4) 未知错误:保守重试一次,仍失败则切厂商
        if attempt == 1:
            return RepairDecision(
                action=ACTION_RETRY,
                reason=f"镜头 {shot_index+1} 遇到未分类错误 {code},重试一次观察",
            )
        return RepairDecision(
            action=ACTION_SWITCH_MODEL,
            reason=f"镜头 {shot_index+1} 未知错误 {code} 重试无效,切换备选厂商",
        )

    def analyze_quality_failure(self, *, shot_index: int, issues: list[str], attempt: int) -> RepairDecision:
        """分析内容级质检失败(人物不一致/动作错位/穿帮),产出修复决策。"""
        if attempt >= MAX_AUTO_ATTEMPTS:
            return RepairDecision(
                action=ACTION_ABORT,
                reason=f"镜头 {shot_index+1} 内容质检 {attempt} 次仍不通过({'; '.join(issues)[:80]}),交人工判断",
                repairable=False,
            )
        # 人物一致性类问题:重编译 prompt(强化 Bible 视觉关键词 + 参考图)再生成
        return RepairDecision(
            action=ACTION_REGENERATE_PROMPT,
            force_mode="r2v" if any("人物" in i or "一致" in i or "角色" in i for i in issues) else "",
            reason=(
                f"镜头 {shot_index+1} 内容质检不通过({'; '.join(issues)[:80]});"
                "重编译 prompt 强化 Bible 一致性约束后重新生成"
            ),
        )


def log_repair_decision(shot_index: int, decision: RepairDecision) -> None:
    logger.info(
        "shot%d 失败修复决策: action=%s force_mode=%s — %s",
        shot_index, decision.action, decision.force_mode or "-", decision.reason,
    )
