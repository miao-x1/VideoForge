"""Mock LLM Provider。

第一阶段用预置的"假如古代人有手机"主题数据，保证 Pipeline 立刻可跑通。
未来接真实 LLM 时，仅替换此实现，Agent 层零改动。

设计要点：即使输入其他创意，也能基于通用模板产出一个可消费的 Storyboard，
让骨架测试不依赖特定输入。
"""
from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


def _requirement_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    duration = int(ctx.get("duration") or 30)
    style = ctx.get("style") or "古装喜剧"
    user_input = ctx.get("user_input") or "假如古代人有手机"
    return {
        "topic": user_input,
        "genre": "轻喜剧",
        "duration": duration,
        "style": style,
        "audience": "大众",
        "characters": [
            {"name": "书生", "description": "穿青衫、手持手机的古代读书人"},
            {"name": "皇帝", "description": "龙袍,沉迷短视频"},
            {"name": "太监", "description": "捧着奏折,神情焦急"},
        ],
        "scenes": [
            {"location": "书房", "description": "书生挑灯夜读,手机屏幕亮着"},
            {"location": "金銮殿", "description": "皇帝批奏折,龙案上摆着手机"},
        ],
        "tone": "轻松搞笑",
        "visual_style": "古典工笔+现代手机元素混搭",
        "output_requirement": "1280x720, 16:9",
    }


def _script_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    req = ctx.get("requirement") or {}
    duration = int(req.get("duration") or 30)
    topic = req.get("topic") or "假如古代人有手机"
    # 按 5 秒一个分场切分
    per = 5
    n = max(1, duration // per)
    scenes = []
    for i in range(n):
        scenes.append({
            "scene_id": i + 1,
            "duration": per,
            "location": ["书房", "金銮殿", "街道"][i % 3],
            "characters": ["书生", "皇帝", "太监"][i % 3: i % 3 + 1],
            "visual": f"第{i+1}幕:古代人玩手机,引发笑料",
            "dialogue": "",
            "voiceover": f"假如古代人有手机,第{i+1}幕:古人也躲不开消息轰炸。",
        })
    return {
        "title": topic,
        "hook": "皇帝批奏折刷短视频停不下来,太监急得直跺脚",
        "scenes": scenes,
        "ending": "原来古人有了手机,一样被消息淹没。",
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
        shots.append({
            "scene_id": sid,
            "duration": duration,
            "shot_type": shot_types[i % len(shot_types)],
            "camera_movement": cams[i % len(cams)],
            "visual_description": visual,
            "character_action": "人物低头看手机,表情丰富",
            "dialogue": sc.get("dialogue", ""),
            "voiceover": voiceover,
            "background_music": "轻快古风BGM",
            "sound_effect": "消息提示音",
            "image_prompt": (
                f"ancient Chinese {sc.get('location','')} scene, "
                f"a character in traditional robe holding a glowing smartphone, "
                f"cinematic lighting, humorous, detailed illustration"
            ),
            "video_prompt": f"{visual}, slow motion, humorous ancient-modern mashup",
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
