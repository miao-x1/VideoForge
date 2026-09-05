"""创意理解 → 导演方案 + Tool 序列。

这是新 Agent 的主路径：理解剧情/角色/场景/镜头/情绪，再调用底层 previs 与生成 Tool。
简单位移指令仍走 planner.plan 的规则路径。
"""
from __future__ import annotations

import re
from typing import Any


def visual_refs(context: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("image_url", "composition_url", "backdrop_url"):
        val = context.get(key)
        if isinstance(val, str) and val.strip():
            urls.append(val.strip())
    extra = context.get("attachment_urls") or []
    if isinstance(extra, list):
        urls.extend(u.strip() for u in extra if isinstance(u, str) and u.strip())
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def looks_like_scene_brief(message: str) -> bool:
    t = re.sub(r"\s+", "", message or "")
    if len(t) < 8:
        return False
    if re.fullmatch(r"(请|帮我)?(让.{0,8})?(坐下|坐下来|走路|走过来|跑步|挥手|站着|站立)", t):
        return False
    return True


def _duration(message: str, context: dict[str, Any]) -> float:
    matched = re.search(r"(\d+(?:\.\d+)?)秒", message or "")
    if matched:
        return max(1.0, min(15.0, float(matched.group(1))))
    raw = context.get("gen_duration") or context.get("shot_duration") or 5
    try:
        return max(1.0, min(15.0, float(raw)))
    except (TypeError, ValueError):
        return 5.0


def is_director_brief(text: str) -> bool:
    t = re.sub(r"\s+", "", text or "")
    keys = (
        "拍一个", "拍一段", "帮我拍", "做一个", "做成", "拆成", "分镜", "生成画面", "生成这个镜头",
        "发送构图", "发回画布", "空间参考",
        "做成视频", "生成视频", "预览", "回到家", "回家", "疲惫", "跟拍", "特写",
        "近景", "远景", "中景", "五个镜头", "5个镜头", "换成", "参考图", "上传的角色",
        "场景", "出片",
    )
    if "客厅" in t and any(k in t for k in ("坐下", "回家", "沙发", "女生")):
        return True
    return any(k in t for k in keys) or len(t) >= 24


def plan_director(message: str, context: dict[str, Any]) -> dict[str, Any]:
    text = re.sub(r"\s+", "", message or "")
    thinking: list[str] = []
    calls: list[dict] = []
    plan: dict[str, Any] = {
        "story": message.strip(),
        "scene": "客厅" if any(k in text for k in ("客厅", "回家", "沙发")) else (context.get("scene_name") or ""),
        "time_of_day": "夜晚" if any(k in text for k in ("晚上", "夜晚", "深夜")) else "",
        "emotion": "疲惫、安静" if any(k in text for k in ("疲惫", "安静", "累")) else "",
        "shots": [],
    }

    if re.search(r"发送构图|发回画布|空间参考", text):
        thinking.extend(["从当前机位截取构图", "写回画布节点 compositionUrl"])
        calls.append({"name": "send_composition", "arguments": {}, "note": "发送构图到画布"})
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    mixed = bool(re.search(r"走|窗|坐|转身|看向|镜头|移到|站到", text))
    if re.search(r"生成(这个)?镜头的画面|生成画面|生成参考图|出一张图", text) and not mixed:
        thinking.extend(["正在理解当前镜头", "将导演台状态编成 Image Prompt", "调用图片模型"])
        calls.append({"name": "generate_image", "arguments": {"kind": "image"}, "note": "生成当前镜头参考画面"})
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    if re.search(r"做成.*视频|生成视频|图生视频|5秒视频|五秒视频", text) and not mixed:
        thinking.extend(["读取当前镜头参考图与动作", "编成 Video Prompt", "调用视频模型"])
        dur = _duration(message, context)
        aspect = str(context.get("aspect_ratio") or context.get("gen_aspect") or "9:16")
        calls.append({
            "name": "generate_video",
            "arguments": {"duration": dur, "aspect_ratio": aspect, "prompt": message.strip()},
            "note": f"生成 {dur}s 视频并绑定镜头",
        })
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    if visual_refs(context) and looks_like_scene_brief(message) and not re.search(r"改成|换成|拆成|自动分镜", text):
        dur = _duration(message, context)
        aspect = str(context.get("aspect_ratio") or context.get("gen_aspect") or "9:16")
        thinking.extend(["读取当前定制镜头与场景照片", "用文字场景编成 Video Prompt", "调用视频模型"])
        calls.append({
            "name": "update_shot",
            "arguments": {"description": message.strip(), "duration": dur},
            "note": "写入镜头场景",
        })
        calls.append({
            "name": "generate_video",
            "arguments": {"duration": dur, "aspect_ratio": aspect, "prompt": message.strip()},
            "note": f"按当前镜头生成 {dur}s 视频",
        })
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    if re.search(r"特写|近景|脸", text) and re.search(r"改成|换成|最后|这个镜头|镜头", text):
        thinking.extend(["识别目标：最后一个/当前镜头", "Camera → close-up"])
        calls.append({"name": "set_shot_type", "arguments": {"shot_type": "close-up", "fov": 28}, "note": "改为脸部特写"})
        calls.append({"name": "set_camera_target", "arguments": {}, "note": "对准角色面部"})
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    if re.search(r"跟拍|跟着她|从门口", text):
        thinking.extend(["镜头语言：tracking", "角色路径：门口 → 沙发"])
        if not _has_prop(context, "sofa", "沙发"):
            calls.append({"name": "add_prop", "arguments": {"catalog_id": "sofa", "position": [0, 0, 1.15]}, "note": "沙发"})
        calls.append({"name": "move_character", "arguments": {"near": "sofa", "animate": True}, "note": "走向沙发"})
        calls.append({"name": "set_camera_motion", "arguments": {"motion": "tracking"}, "note": "跟拍"})
        calls.append({
            "name": "update_shot",
            "arguments": {"description": "门口跟拍走到沙发", "shot_type": "medium shot", "camera_movement": "tracking"},
            "note": "更新镜头方案",
        })
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    if re.search(r"换成.*角色|上传的角色|我的角色", text):
        thinking.append("需要用角色库中的指定资产替换当前实例")
        lib = context.get("characters") or []
        uploaded = next((c for c in lib if c.get("sourceType") in ("upload", "image") or "上传" in str(c.get("name") or "")), None)
        recent = (context.get("characters") or [None])[-1] if context.get("characters") else None
        target = uploaded or recent
        if not target:
            return {"thinking": thinking, "calls": [], "error": "角色库里没有可替换的上传角色。请先上传角色资产。", "director_plan": plan}
        calls.append({"name": "remove_character_from_scene", "arguments": {}, "note": "移出当前角色"})
        calls.append({"name": "add_character_to_scene", "arguments": {"character_id": target.get("id")}, "note": "换上指定角色"})
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    shots = _split_shots(text, plan)
    if shots:
        thinking.append("正在理解剧情")
        thinking.append(f"已识别场景：{plan['scene'] or '当前分镜'}")
        thinking.append(f"已拆分 {len(shots)} 个 Shot")
        plan["shots"] = shots
        if plan["scene"] in ("客厅",) or "客厅" in text or "回家" in text:
            calls.append({"name": "place_room_preset", "arguments": {"preset": "room"}, "note": "建立客厅空间"})
            if "沙发" in text or any("沙发" in s.get("visual_description", "") for s in shots):
                calls.append({"name": "add_prop", "arguments": {"catalog_id": "sofa", "position": [0, 0, 1.15]}, "note": "沙发"})
        if any(k in text for k in ("女", "她", "女生")):
            calls.append({
                "name": "create_character",
                "arguments": {"template_id": "human_female_young_01", "name": "女主角", "add_to_scene": True},
                "note": "创建/使用女主",
            })
        for i, shot in enumerate(shots):
            meta = {
                "name": shot["name"],
                "duration": shot["duration"],
                "description": shot["visual_description"],
                "shot_type": shot["shot_type"],
                "camera_movement": shot["camera_movement"],
                "emotion": shot.get("emotion") or plan["emotion"],
                "time_of_day": plan["time_of_day"],
            }
            if i == 0:
                calls.append({"name": "update_shot", "arguments": meta, "note": f"设定 {shot['name']}"})
            else:
                calls.append({
                    "name": "create_shot",
                    "arguments": {**meta, "copy_current": True},
                    "note": f"创建 {shot['name']}",
                })
            if shot.get("character_action") == "walk":
                calls.append({"name": "move_character", "arguments": {"near": shot.get("near") or "sofa", "animate": True}, "note": "走路预演"})
            if shot.get("character_action") == "sit":
                calls.append({"name": "set_character_pose", "arguments": {"pose": "sit"}, "note": "坐下预演"})
            if shot.get("shot_type") == "close-up":
                calls.append({"name": "set_shot_type", "arguments": {"shot_type": "close-up", "fov": 28}, "note": "近景/特写"})
            elif shot.get("camera_movement") == "tracking":
                calls.append({"name": "set_camera_motion", "arguments": {"motion": "tracking"}, "note": "跟拍预演"})
            elif shot.get("camera_movement") == "push_in":
                calls.append({"name": "set_camera_motion", "arguments": {"motion": "push_in"}, "note": "推进预演"})
            if shot.get("look_at"):
                calls.append({"name": "set_camera_target", "arguments": {}, "note": "对准角色"})
        if re.search(r"生成预览|生成画面|做出预览|并生成", text):
            calls.append({"name": "generate_image", "arguments": {}, "note": "为当前镜头生成参考画面"})
        return {"thinking": thinking, "calls": calls, "error": None, "director_plan": plan}

    return {"thinking": ["未能形成导演方案"], "calls": [], "error": None, "director_plan": plan}


def _has_prop(context: dict, *needles: str) -> bool:
    for obj in context.get("objects") or []:
        blob = f"{obj.get('name')}{obj.get('catalogId')}"
        if any(n in blob for n in needles):
            return True
    return False


def _split_shots(text: str, plan: dict) -> list[dict]:
    if re.search(r"回家|疲惫|跟拍|放包|晚上回到|深夜", text) or (
        re.search(r"坐下", text) and re.search(r"客厅|沙发", text) and re.search(r"进门|走|跟|特写|五个|5个", text)
    ):
        night = "夜晚" if plan.get("time_of_day") == "夜晚" else ""
        tired = plan.get("emotion") or "安静"
        return [
            {
                "name": "Shot 01 进门",
                "duration": 4,
                "shot_type": "wide shot",
                "camera_movement": "static",
                "visual_description": f"{night}女生打开门进入客厅",
                "character_action": "walk",
                "near": "door",
                "emotion": tired,
            },
            {
                "name": "Shot 02 走向沙发",
                "duration": 5,
                "shot_type": "medium shot",
                "camera_movement": "tracking",
                "visual_description": "中景，镜头从门口跟着她走到沙发",
                "character_action": "walk",
                "near": "sofa",
                "emotion": tired,
            },
            {
                "name": "Shot 03 放包",
                "duration": 3,
                "shot_type": "medium close-up",
                "camera_movement": "static",
                "visual_description": "女生把包放到沙发上",
                "character_action": "stand",
                "near": "sofa",
                "emotion": tired,
            },
            {
                "name": "Shot 04 坐下",
                "duration": 4,
                "shot_type": "medium shot",
                "camera_movement": "static",
                "visual_description": "女生坐在沙发上",
                "character_action": "sit",
                "near": "sofa",
                "emotion": tired,
                "look_at": True,
            },
            {
                "name": "Shot 05 特写",
                "duration": 3,
                "shot_type": "close-up",
                "camera_movement": "push_in",
                "visual_description": "脸部特写，疲惫地看向前方",
                "character_action": "sit",
                "emotion": tired,
                "look_at": True,
            },
        ]
    if re.search(r"(\d+)个镜头|拆成|自动分镜", text):
        n = 5
        m = re.search(r"(\d+)个镜头", text)
        if m:
            n = max(2, min(8, int(m.group(1))))
        return [
            {
                "name": f"Shot {i+1:02d}",
                "duration": 4,
                "shot_type": "medium shot" if i < n - 1 else "close-up",
                "camera_movement": "static" if i == 0 else ("tracking" if i == 1 else "push_in" if i == n - 1 else "static"),
                "visual_description": text[:80],
                "character_action": "walk" if i == 1 else ("sit" if i >= n - 2 else "stand"),
                "emotion": plan.get("emotion") or "",
            }
            for i in range(n)
        ]
    if re.search(r"女生.*客厅.*坐下|客厅里坐下|做一个女生", text):
        return [
            {
                "name": "Shot 01 客厅坐下",
                "duration": 5,
                "shot_type": "medium shot",
                "camera_movement": "static",
                "visual_description": "女生在客厅坐下",
                "character_action": "sit",
                "near": "sofa",
                "look_at": True,
                "emotion": plan.get("emotion") or "安静",
            }
        ]
    return []
