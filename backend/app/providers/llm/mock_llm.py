"""Mock LLM Provider。

根据 user_input 动态生成通用 Pipeline 数据,不硬编码特定主题。
保证任意输入都能产出结构化 requirement/script/storyboard,让骨架测试不依赖特定题材。
未来接真实 LLM 时,仅替换此实现,Agent 层零改动。
"""
from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


def _requirement_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    duration = int(ctx.get("duration") or 30)
    style = ctx.get("style") or "轻松搞笑"
    user_input = ctx.get("user_input") or "短视频创意"
    return {
        "topic": user_input,
        "genre": "短视频",
        "duration": duration,
        "style": style,
        "audience": "大众",
        "characters": [
            {"name": "主角", "description": f"与「{user_input}」相关的核心角色"},
            {"name": "配角", "description": "辅助叙事的人物"},
        ],
        "scenes": [
            {"location": "场景一", "description": f"围绕「{user_input}」的开场画面"},
            {"location": "场景二", "description": f"围绕「{user_input}」的高潮画面"},
        ],
        "tone": style,
        "visual_style": f"{style}风格,贴合「{user_input}」主题",
        "output_requirement": "720x1280, 9:16",
    }


def _script_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    req = ctx.get("requirement") or {}
    duration = int(req.get("duration") or 30)
    topic = req.get("topic") or "短视频创意"
    style = req.get("style") or "轻松搞笑"
    # 按 5 秒一个分场切分
    per = 5
    n = max(1, duration // per)
    scenes = []
    for i in range(n):
        scenes.append({
            "scene_id": i + 1,
            "duration": per,
            "location": f"场景{i + 1}",
            "characters": ["主角"],
            "visual": f"第{i+1}幕:围绕「{topic}」展开,{style}风格",
            "dialogue": "",
            "voiceover": f"{topic}。第{i+1}幕:故事在这里展开,引人入胜。",
        })
    return {
        "title": topic,
        "hook": f"「{topic}」——一个让人忍不住看下去的故事",
        "scenes": scenes,
        "ending": f"故事在「{topic}」中落下帷幕,回味无穷。",
    }


def _storyboard_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    script = ctx.get("script") or {}
    src_scenes = script.get("scenes") or []
    shots = []
    shot_types = ["medium shot", "close-up", "wide shot", "medium shot", "close-up", "wide shot"]
    cams = ["slow push in", "static", "slow pan", "slow push in", "static", "slow pull out"]
    for i, sc in enumerate(src_scenes):
        sid = sc.get("scene_id", i + 1)
        duration = int(sc.get("duration", 5))
        visual = sc.get("visual", "")
        voiceover = sc.get("voiceover", "")
        location = sc.get("location", "")
        shots.append({
            "scene_id": sid,
            "duration": duration,
            "shot_type": shot_types[i % len(shot_types)],
            "camera_movement": cams[i % len(cams)],
            "visual_description": visual,
            "character_action": "主角在画面中活动,表情生动",
            "dialogue": sc.get("dialogue", ""),
            "voiceover": voiceover,
            "background_music": "轻快BGM",
            "sound_effect": "环境音效",
            "image_prompt": (
                f"{location} scene, {visual}, "
                f"cinematic lighting, detailed illustration, high quality"
            ),
            "video_prompt": f"{visual}, smooth motion, cinematic",
        })
    return {"shots": shots}


def _content_guard_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock ContentGuard:默认放行(low 风险),保持 Mock Pipeline 可跑通。

    真实评估由 DashScopeLLMProvider + CONTENT_GUARD_PROMPT 完成,Mock 仅作骨架占位。
    """
    return {
        "safe": True,
        "overall_risk": "low",
        "safety_risk": "low",
        "platform_risk": "low",
        "cultural_risk": "low",
        "warnings": [],
        "suggestions": [],
    }


def _compliance_check_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 合规预审:基于确定性 rule_hits 做离线判定,支撑无 LLM 环境的测试。

    真实语义判断由 DashScopeLLMProvider + COMPLIANCE_CHECK_PROMPT 完成。
    Mock 逻辑:
    - 任一 reject+high 规则命中 -> reject/high
    - 任一 reject 规则命中 -> reject
    - 任一 review 规则命中 -> review/medium
    - 无命中 -> pass/low
    """
    hits = ctx.get("rule_hits") or []
    content = ctx.get("content", "")
    violations, warnings, matched = [], [], []
    reject_high = False
    reject_any = False
    review_any = False
    for h in hits:
        matched.append(h["rule_id"])
        item = {
            "rule_id": h["rule_id"],
            "category": h["category"],
            "severity": h.get("severity", "medium"),
            "evidence": h.get("matched_text", ""),
            "explanation": h.get("description", ""),
        }
        action = h.get("action", "review")
        sev = h.get("severity", "medium")
        if action == "reject":
            reject_any = True
            if sev == "high":
                reject_high = True
            violations.append(item)
        else:
            review_any = True
            warnings.append(item)

    if reject_high:
        status, risk, score = "reject", "high", 20
    elif reject_any:
        status, risk, score = "reject", "high", 35
    elif review_any:
        status, risk, score = "review", "medium", 60
    else:
        status, risk, score = "pass", "low", 95

    suggestions = [f"移除或改写命中规则的内容: {', '.join(matched)}"] if matched else []
    return {
        "status": status,
        "risk_level": risk,
        "overall_score": score,
        "violations": violations,
        "warnings": warnings,
        "matched_rules": matched,
        "explanation": f"Mock 合规预审(基于规则命中),内容长度 {len(content)} 字",
        "revision_suggestions": suggestions,
        "human_review_required": status != "pass",
        "review_reason": "" if status == "pass" else f"mock_{status}",
    }


def _script_revision_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 脚本修订:原样返回原脚本(不真正修订)。

    真实修订由 DashScopeLLMProvider + SCRIPT_REVISION_PROMPT 完成。
    Mock 下原样返回会触发"复检仍不通过 -> 修订耗尽 -> HUMAN_REVIEW",恰好覆盖该测试路径。
    """
    orig = ctx.get("original_script") or {}
    return {
        "title": orig.get("title", "修订脚本"),
        "hook": orig.get("hook", ""),
        "scenes": orig.get("scenes", []),
        "ending": orig.get("ending"),
    }


class MockLLMProvider(LLMProvider):
    async def generate(self, *, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if task == "requirement":
            return _requirement_data(context)
        if task == "script":
            return _script_data(context)
        if task == "storyboard":
            return _storyboard_data(context)
        if task == "content_guard":
            return _content_guard_data(context)
        if task == "compliance_check":
            return _compliance_check_data(context)
        if task == "script_revision":
            return _script_revision_data(context)
        raise ValueError(f"未知 LLM 任务类型: {task}")
