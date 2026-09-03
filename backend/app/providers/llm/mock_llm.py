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
    requirement = {
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
    # RequirementAgent 契约:creative_intent(深度理解) + requirement(结构化需求)
    creative_intent = {
        "concept": user_input,
        "subject": "由创意决定的画面主体",
        "subject_description": f"与「{user_input}」直接相关的核心主体",
        "scene": "由创意决定的场景",
        "scene_description": f"围绕「{user_input}」构建的场景氛围",
        "action": "主体在画面中的核心动作",
        "action_description": "",
        "emotion": style,
        "visual_style": f"{style}风格",
        "camera_style": "自然叙事镜头",
        "lighting": "自然光",
        "color_mood": "色彩统一",
        "duration": duration,
        "aspect_ratio": "9:16",
        "references": [],
        "creative_goal": f"完整呈现「{user_input}」",
        "constraints": [],
        "inferred_needs": ["节奏紧凑", "画面连贯"],
    }
    return {"creative_intent": creative_intent, "requirement": requirement}


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
    # 作品级规划上下文(Phase 4:连续性 mock 消费 Bible)
    char_bibles = ctx.get("characters") or []
    world = ctx.get("world") or {}
    bible_names = [c.get("name", "") for c in char_bibles if c.get("name")]
    world_scenes = {s.get("name", ""): s for s in (world.get("scenes") or []) if isinstance(s, dict)}
    time_slots = ["清晨", "正午", "傍晚", "深夜"]
    lightings = ["柔和晨光", "顶光日光", "暖黄昏光", "冷青夜色"]
    emotions = ["neutral", "surprise", "tension", "calm", "humor", "joy"]
    shots = []
    shot_types = ["medium shot", "close-up", "wide shot", "medium shot", "close-up", "wide shot"]
    cams = ["slow push in", "static", "slow pan", "slow push in", "static", "slow pull out"]
    for i, sc in enumerate(src_scenes):
        sid = sc.get("scene_id", i + 1)
        duration = int(sc.get("duration", 5))
        visual = sc.get("visual", "")
        voiceover = sc.get("voiceover", "")
        location = sc.get("location", "")
        # 人物:优先脚本场景人物,其次 Character Bible 姓名
        scene_chars = sc.get("characters") or []
        if isinstance(scene_chars, str):
            scene_chars = [scene_chars]
        characters = [c for c in scene_chars if c] or bible_names
        # 时段/光线:优先 World Bible 匹配场景,否则按序循环
        ws = world_scenes.get(location) or {}
        time_of_day = ws.get("time_of_day") or time_slots[i % len(time_slots)]
        lighting = ws.get("lighting") or lightings[i % len(lightings)]
        emotion_start = emotions[i % len(emotions)]
        emotion_end = emotions[(i + 1) % len(emotions)]
        continuity_out = f"{visual}结束后的状态保持:人物情绪与场景布置延续到下一镜"
        continuity_in = "" if i == 0 else f"承接上一镜: {src_scenes[i - 1].get('visual', '')} 后的人物状态与场景"
        causal_note = "" if i == 0 else f"上一镜事件( {src_scenes[i - 1].get('visual', '')} )直接导致本镜发生"
        char_kw = ""
        if characters:
            char_kw = ", ".join(f"{n} consistent appearance" for n in characters) + ", "
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
                f"{location} scene, {char_kw}{visual}, "
                f"cinematic lighting, detailed illustration, high quality"
            ),
            "video_prompt": f"{visual}, smooth motion, cinematic",
            "characters": characters,
            "location": location,
            "time_of_day": time_of_day,
            "lighting": lighting,
            "emotion": emotion_start,
            "emotion_end": emotion_end,
            "continuity_in": continuity_in,
            "continuity_out": continuity_out,
            "causal_note": causal_note,
            "desired_mode": "",
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


def _prompt_engineering_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock Prompt Engineering:基于 storyboard 基础 Prompt 生成结构化增强结果。

    真实编译由 DashScopeLLMProvider + PROMPT_ENGINEERING_PROMPT 完成,
    Mock 仅做确定性的结构转换,保证测试 Pipeline 可跑通。
    """
    storyboard = ctx.get("storyboard") or {}
    shots = storyboard.get("shots") or []
    model_info = ctx.get("model_info") or {}
    model_id = model_info.get("model_id") or "mock-video-model"
    model_name = model_info.get("model_name") or "mock"
    capabilities = ctx.get("model_capabilities") or {}
    supports_negative = capabilities.get("supports_negative_prompt", False)

    creative_intent = ctx.get("creative_intent") or {}
    visual_style = creative_intent.get("visual_style") or "cinematic"
    lighting = creative_intent.get("lighting") or "natural light"
    emotion = creative_intent.get("emotion") or ""

    prompts = []
    # 局部重生成场景:上下文携带原始 shot_index,单镜头时保持原索引
    base_index = ctx.get("shot_index")
    for i, shot in enumerate(shots):
        shot_index = base_index if (base_index is not None and len(shots) == 1) else i
        visual = shot.get("visual_description") or shot.get("image_prompt") or ""
        image_prompt = shot.get("image_prompt") or ""
        video_prompt = shot.get("video_prompt") or ""
        subject = creative_intent.get("subject") or "main subject"
        scene = creative_intent.get("scene") or ""
        raw_image = (
            f"{image_prompt}, {subject} in {scene}, {visual_style} style, "
            f"{lighting}, highly detailed, high quality"
        )
        raw_video = (
            f"{video_prompt or visual}, smooth motion, "
            f"{shot.get('camera_movement', 'static')}, cinematic quality"
        )
        negative = "blurry, low quality, distorted, watermark, text artifacts" if supports_negative else ""
        prompts.append({
            "shot_index": shot_index,
            "subject": subject,
            "environment": scene,
            "action": shot.get("character_action") or "",
            "composition": shot.get("shot_type") or "",
            "camera": shot.get("camera_movement") or "",
            "lighting": lighting,
            "visual_style": visual_style,
            "emotion": emotion,
            "sound": shot.get("background_music") or "",
            "rhythm": "",
            "raw_image_prompt": raw_image,
            "raw_video_prompt": raw_video,
            "negative_prompt": negative,
            "generation_params": {},
            "model_id": model_id,
            "model_convention": f"mock convention for {model_name}",
        })

    return {
        "prompts": prompts,
        "model_id": model_id,
        "model_capabilities": capabilities,
        "compilation_notes": f"Mock 编译:基于 {len(prompts)} 个镜头的基础 Prompt 生成,适配 {model_name}",
    }


def _story_planning_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 故事规划:确定性生成 5 个节拍 + 每个人物一条弧光。"""
    req = ctx.get("requirement") or {}
    topic = req.get("topic") or ctx.get("user_input") or "短视频创意"
    genre = req.get("genre") or "剧情"
    characters = req.get("characters") or [{"name": "主角"}]
    beat_specs = [
        ("beat_01", "开端", f"引出「{topic}」的核心情境,人物登场", "好奇"),
        ("beat_02", "发展", "人物关系与目标建立,观众投入情感", "投入"),
        ("beat_03", "冲突", f"核心矛盾爆发,「{topic}」的张力形成", "紧张"),
        ("beat_04", "高潮", "矛盾推向顶点,人物做出关键抉择", "强烈"),
        ("beat_05", "结局", "冲突收束,情感落点清晰,留下余味", "回味"),
    ]
    arcs = []
    for i, ch in enumerate(characters):
        name = ch.get("name") or f"角色{i + 1}"
        arcs.append({
            "character_id": f"character_{i + 1:03d}",
            "character_name": name,
            "arc_summary": f"{name}在「{topic}」中经历的处境与心境变化",
            "start_state": "故事开始时的状态",
            "end_state": "故事结束时的状态",
        })
    return {
        "title": topic,
        "theme": f"围绕「{topic}」展开的{genre}故事",
        "logline": f"一个关于{topic}的故事:人物在困境中追寻目标。",
        "core_conflict": "人物愿望与现实阻碍之间的冲突",
        "ending_tone": "余味悠长",
        "beats": [
            {"beat_id": bid, "name": name, "summary": summary, "emotion": emotion, "scene_refs": []}
            for bid, name, summary, emotion in beat_specs
        ],
        "character_arcs": arcs,
    }


def _character_bible_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 人物 Bible:为 requirement.characters 中每个人物建立确定性档案。"""
    req = ctx.get("requirement") or {}
    chars = req.get("characters") or [{"name": "主角", "description": "核心角色"}]
    out = []
    for i, ch in enumerate(chars):
        name = ch.get("name") or f"角色{i + 1}"
        desc = ch.get("description") or ""
        out.append({
            "character_id": f"character_{i + 1:03d}",
            "name": name,
            "age": "",
            "gender": "",
            "identity": desc or f"「{name}」故事主要人物",
            "personality": "性格鲜明,动机清晰",
            "appearance": f"{name}的辨识外貌特征" + (f":{desc}" if desc else ""),
            "hairstyle": "与身份相符的发型",
            "clothing": "符合时代与身份的服装",
            "body_type": "普通体型",
            "speech_style": "自然口语,符合身份",
            "emotion_traits": "情绪随剧情起伏",
            "relations": [],
            "background": "",
            "visual_keywords": [name, "辨识度外貌", "符合身份的服装"],
        })
    return {"characters": out}


def _world_bible_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 世界观/风格 Bible:从 requirement.scenes 与 creative_intent 确定性生成。"""
    req = ctx.get("requirement") or {}
    ci = ctx.get("creative_intent") or {}
    scenes = req.get("scenes") or [{"location": "主场景", "description": ""}]
    style = req.get("style") or ci.get("visual_style") or "电影感"
    world_scenes = []
    for i, sc in enumerate(scenes):
        loc = sc.get("location") or f"场景{i + 1}"
        world_scenes.append({
            "scene_key": f"scene_{i + 1:02d}",
            "name": loc,
            "location": loc,
            "time_of_day": "",
            "weather": "",
            "lighting": ci.get("lighting") or "自然光",
            "description": sc.get("description") or ci.get("scene_description") or "",
        })
    return {
        "world": {
            "era": "",
            "region": "",
            "architecture": "",
            "weather_base": "",
            "time_span": "",
            "props_system": [],
            "world_rules": "",
            "scenes": world_scenes,
        },
        "style": {
            "visual_style": ci.get("visual_style") or style,
            "photography_style": ci.get("camera_style") or "自然叙事镜头",
            "color_palette": ci.get("color_mood") or "色调统一",
            "color_temperature": "",
            "saturation": "",
            "contrast": "",
            "color_grading": "",
            "lighting_base": ci.get("lighting") or "自然光",
            "lens_language": "",
            "texture": "",
            "negative_keywords": [],
        },
    }


def _audio_planning_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 音频规划:从分镜逐镜产出 cue,音乐情绪从节拍/题材推断。"""
    storyboard = ctx.get("storyboard") or {}
    shots = storyboard.get("shots") or []
    cues = []
    for i, shot in enumerate(shots):
        emotion = shot.get("emotion") or "neutral"
        if shot.get("voiceover"):
            cues.append({"shot_index": i, "narration": True, "narration_emotion": emotion})
        if shot.get("dialogue"):
            cues.append({"shot_index": i, "dialogue": True, "dialogue_emotion": emotion})
        if shot.get("sound_effect"):
            cues.append({"shot_index": i, "sfx": shot.get("sound_effect")})
    # 音乐情绪:从节拍情绪与题材确定性推断
    beats = ctx.get("beats") or []
    emotions = " ".join(b.get("emotion", "") for b in beats)
    genre = ctx.get("genre") or ""
    text = f"{emotions} {genre} {ctx.get('style', '')}"
    if any(k in text for k in ("紧张", "冲突", "高潮", "tension")):
        mood, style_music = "tense", "suspenseful orchestral"
    elif any(k in text for k in ("悲", "遗憾", "虐", "sad")):
        mood, style_music = "melancholic", "soft emotional piano"
    elif any(k in text for k in ("幽默", "轻松", "喜剧", "humor")):
        mood, style_music = "light", "playful upbeat"
    else:
        mood, style_music = "light", "cinematic ambient"
    return {"cues": cues, "music_mood": mood, "music_style": style_music}


def _editing_planning_data(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 剪辑决策:叙事顺序,转场按镜头情绪给倾向(规则兜底在 Agent 侧)。"""
    shots = ctx.get("shots") or []
    n = len(shots)
    transitions: Dict[str, str] = {}
    for i in range(n - 1):
        emotion = (shots[i].get("emotion_end") or shots[i].get("emotion") or "").lower()
        if any(k in emotion for k in ("tension", "surprise", "humor", "紧张", "惊讶")):
            transitions[f"{i}->{i + 1}"] = "cut"
        elif any(k in emotion for k in ("sad", "calm", "悲", "平静")):
            transitions[f"{i}->{i + 1}"] = "dissolve"
        else:
            transitions[f"{i}->{i + 1}"] = "fade"
    return {
        "shot_order": list(range(n)),
        "transitions": transitions,
        "pacing_note": "开场留白铺垫,中段按情绪节拍推进,高潮快切,结尾收束" if n > 3 else "匀速叙事",
    }


class MockLLMProvider(LLMProvider):
    async def describe_image(self, image_path: str, prompt: str = "描述这张图片的内容、主体、风格、色调和氛围") -> str:
        import os
        return f"[Mock 图片理解] 文件: {os.path.basename(image_path)}"

    async def generate(self, *, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if task == "requirement":
            return _requirement_data(context)
        if task == "story_planning":
            return _story_planning_data(context)
        if task == "character_bible":
            return _character_bible_data(context)
        if task == "world_bible":
            return _world_bible_data(context)
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
        if task == "prompt_engineering":
            return _prompt_engineering_data(context)
        if task == "audio_planning":
            return _audio_planning_data(context)
        if task == "editing_planning":
            return _editing_planning_data(context)
        if task == "semantic_summary":
            raw = context.get("raw_content", "")
            return {"summary": raw[:200] if len(raw) > 200 else raw}
        raise ValueError(f"未知 LLM 任务类型: {task}")
