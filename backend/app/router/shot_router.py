"""ShotRouter:逐镜头生成模式决策(任务书第 11/12 节)。

与整条视频级别的 model_router 不同,ShotRouter 对**每个镜头**独立决策:
- t2v(纯文生视频):无人物空镜/转场镜,不需要关键帧
- i2v(图生视频):有关键帧首帧,人物动作镜头
- r2v(参考生视频):靠角色参考图/用户参考图保持主体一致,无固定首帧
- first_last(首尾帧):需要严格衔接下一镜画面,模型支持尾帧输入

决策是纯函数(确定性、可单测、可审计),输出 mode + 原因 + 请求组装标志位。
厂商选择仍由 pipeline 级 model_router 决定;模式由镜头规划(desired_mode)
与素材就位情况(首帧/尾帧/参考图)共同决定。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..providers.video.capabilities import ModelCapabilities

VALID_MODES = ("t2v", "i2v", "r2v", "first_last")


@dataclass
class ShotModeDecision:
    """单镜头模式决策结果。"""

    mode: str  # t2v / i2v / r2v / first_last / unsupported
    reason: str
    use_first_frame: bool = False
    use_last_frame: bool = False
    use_references: bool = False

    @property
    def feasible(self) -> bool:
        return self.mode != "unsupported"


def decide_video_mode(
    *,
    desired_mode: str,
    has_first_frame: bool,
    has_last_frame: bool,
    has_references: bool,
    caps: ModelCapabilities,
) -> ShotModeDecision:
    """按镜头规划与素材就位情况决策生成模式。

    优先级(高 → 低):
    1. first_last:首帧+尾帧都就位且模型支持尾帧 → 严格画面衔接
    2. r2v:Agent 规划 r2v,或(无首帧但有参考图)→ 参考图保主体一致
    3. i2v:有首帧 → 关键帧驱动(参考图可同时附加增强一致性)
    4. t2v:Agent 规划 t2v 或无任何图片素材,且模型支持纯文生视频
    5. unsupported:无首帧/无参考图且模型不支持 T2V → 交由失败分析处理
    """
    desired = (desired_mode or "").strip().lower()
    if desired not in VALID_MODES:
        desired = ""

    # 1) 首尾帧衔接:素材就位 + 模型支持 + Agent 未显式要求其他模式
    if (
        has_first_frame and has_last_frame and caps.supports_last_frame
        and desired in ("", "first_last", "i2v")
    ):
        return ShotModeDecision(
            mode="first_last",
            reason="首帧与下一镜首帧(尾帧)均就位,模型支持尾帧输入,严格衔接画面",
            use_first_frame=True,
            use_last_frame=True,
            use_references=has_references,
        )

    # 2) R2V:显式规划,或无首帧但有参考图
    if desired == "r2v" or (not has_first_frame and has_references):
        if caps.supports_image_input:
            return ShotModeDecision(
                mode="r2v",
                reason="无固定首帧,通过角色/用户参考图保持主体一致性(R2V)",
                use_references=True,
            )
        if caps.supports_text_to_video:
            return ShotModeDecision(
                mode="t2v",
                reason="模型不支持参考图输入,R2V 降级为纯文生视频(T2V)",
            )
        return ShotModeDecision(
            mode="unsupported",
            reason="镜头规划为 R2V 但模型既不支持图片输入也不支持文生视频",
        )

    # 3) I2V:有首帧
    if has_first_frame and caps.supports_image_input:
        if desired == "t2v":
            # Agent 想要 T2V 但关键帧已生成 → 首帧能提供更强一致性,采纳更优路径
            return ShotModeDecision(
                mode="i2v",
                reason="关键帧已就位,图生视频(I2V)一致性优于纯文生,采纳首帧",
                use_first_frame=True,
                use_references=has_references,
            )
        return ShotModeDecision(
            mode="i2v",
            reason="有关键帧首帧,图生视频(I2V)驱动镜头",
            use_first_frame=True,
            use_references=has_references,
        )

    # 4) T2V:无首帧(空镜/转场)或显式规划
    if caps.supports_text_to_video:
        return ShotModeDecision(
            mode="t2v",
            reason="无关键帧的空镜/转场镜头,模型支持纯文生视频(T2V)",
        )

    # 5) 无路可走
    return ShotModeDecision(
        mode="unsupported",
        reason=(
            f"镜头规划为 {desired or 'T2V'} 但模型不支持文生视频,"
            "且缺少可用首帧/参考图(需补关键帧或切换模型)"
        ),
    )
