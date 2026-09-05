"""把自然语言编成白名单 Tool 调用。

简单指令走规则，避免把移动/坐下全部丢给 LLM 自由发挥。
复杂句子在已配置 DashScope 时再问模型；失败则诚实报错，不用 Mock。
"""
from __future__ import annotations

import json
import re
from typing import Any

from .director_plan import is_director_brief, looks_like_scene_brief, plan_director, visual_refs
from .registry import ALLOWED, is_allowed

FEMALE_TEMPLATES = ("human_female_young_01", "human_female_adult_01")
MALE_TEMPLATES = ("human_male_young_01", "human_male_adult_01")

ACTION_MAP = {
    "走": "walk",
    "走路": "walk",
    "步行": "walk",
    "跑": "run",
    "跑步": "run",
    "挥手": "wave",
    "说话": "talk",
    "讲话": "talk",
    "待机": "idle",
    "站": "stand",
    "站着": "stand",
    "站立": "stand",
}

POSE_MAP = {
    "坐下": "sit",
    "坐下来": "sit",
    "坐着": "sit",
    "坐": "sit",
    "躺": "lie",
    "躺下": "lie",
    "挥手": "wave",
    "点头": "nod",
}

PROP_MAP = {
    "桌子": "table",
    "桌": "table",
    "椅子": "chair",
    "椅": "chair",
    "沙发": "sofa",
    "门": "door",
    "窗": "window",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "").strip()


def _find_object(ctx: dict, *needles: str) -> dict | None:
    objects = ctx.get("objects") or []
    for needle in needles:
        for obj in objects:
            name = str(obj.get("name") or "")
            catalog = str(obj.get("catalogId") or "")
            if needle in name or needle == catalog:
                return obj
    return None


def _find_character(ctx: dict, text: str) -> dict | None:
    objects = [o for o in (ctx.get("objects") or []) if o.get("characterId")]
    focus = (ctx.get("focus") or {}).get("character_id")
    pronouns = ("她", "他", "这个角色", "刚才的", "这个人", "该角色")
    if any(p in text for p in pronouns) and focus:
        hit = next((o for o in objects if o.get("characterId") == focus or o.get("id") == focus), None)
        if hit:
            return hit
    aliases = [
        ("女主角", "女主", "女生", "女孩", "女的"),
        ("男主角", "男主", "男生", "男孩", "男的"),
    ]
    for group in aliases:
        if any(a in text for a in group):
            for obj in objects:
                name = str(obj.get("name") or "")
                if any(a in name for a in group) or ("女" in group[0] and "女" in name) or ("男" in group[0] and "男" in name):
                    return obj
            lib = ctx.get("characters") or []
            for asset in lib:
                name = str(asset.get("name") or "")
                if any(a in name for a in group):
                    return {"characterId": asset.get("id"), "name": name, "id": None, "fromLibrary": True}
    if focus:
        hit = next((o for o in objects if o.get("characterId") == focus or o.get("id") == focus), None)
        if hit:
            return hit
    if len(objects) == 1:
        return objects[0]
    return None


def _char_id(obj: dict | None) -> str:
    if not obj:
        return ""
    return str(obj.get("characterId") or obj.get("id") or "")


def _instance_id(obj: dict | None) -> str:
    if not obj:
        return ""
    return str(obj.get("id") or "")


def _beside(obj: dict | None, offset: tuple[float, float, float] = (0.7, 0, 0.15)) -> list[float]:
    pos = (obj or {}).get("position") or [0, 0, 0]
    return [float(pos[0]) + offset[0], float(pos[1]) + offset[1], float(pos[2]) + offset[2]]


def _center() -> list[float]:
    return [0.0, 0.0, 0.0]


def plan(message: str, context: dict) -> dict[str, Any]:
    text = _norm(message)
    thinking: list[str] = []
    calls: list[dict] = []

    if not text:
        return {"thinking": ["输入为空"], "calls": [], "error": "请输入导演指令"}

    if is_director_brief(message) or (visual_refs(context) and looks_like_scene_brief(message)):
        directed = plan_director(message, context)
        if directed.get("calls") or directed.get("error"):
            return directed

    if re.search(r"撤销|撤回|undo", text, re.I):
        thinking.append("识别为撤销")
        return {"thinking": thinking, "calls": [{"name": "undo_last", "arguments": {}, "note": "撤销上一步"}]}

    if re.search(r"重做|恢复刚才|redo", text, re.I):
        thinking.append("识别为重做")
        return {"thinking": thinking, "calls": [{"name": "redo_last", "arguments": {}, "note": "重做上一步"}]}

    if "提示词" in text or "prompt" in text.lower():
        kind = "video"
        if "图片" in text or "image" in text.lower():
            kind = "image"
        elif "视频" in text or "video" in text.lower():
            kind = "video"
        elif "动作" in text:
            kind = "motion"
        elif "镜头" in text or "相机" in text:
            kind = "camera"
        elif "场景" in text:
            kind = "scene"
        thinking.append(f"根据当前导演台生成 {kind} 提示词")
        return {"thinking": thinking, "calls": [{"name": "generate_prompt", "arguments": {"kind": kind}, "note": f"生成{kind}提示词"}]}

    if re.search(r"复制.*(镜头|分镜)|把这个镜头复制", text):
        thinking.append("复制当前分镜")
        return {"thinking": thinking, "calls": [{"name": "duplicate_shot", "arguments": {}, "note": "复制分镜"}]}

    duration = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*秒", text)
    if m:
        duration = float(m.group(1))

    created_shot = False
    if re.search(r"创建.*(镜头|分镜)|新建.*(镜头|分镜)|加一个镜头", text) and "角色" not in text:
        thinking.append(f"新建分镜" + (f"，时长 {duration}s" if duration else ""))
        args: dict[str, Any] = {}
        if duration:
            args["duration"] = duration
        if re.search(r"女主|走进|坐下|房间", text):
            args["description"] = message
        calls.append({"name": "create_shot", "arguments": args, "note": "创建分镜"})
        created_shot = True
        if not re.search(r"女主|男主|走|坐|推进|对准|布置", text):
            return {"thinking": thinking, "calls": calls, "error": None}

    if "删除分镜" in text or "删掉这个镜头" in text:
        return {"thinking": ["高风险：删除分镜"], "calls": [{"name": "delete_shot", "arguments": {}, "note": "删除分镜"}]}

    created_female = False
    if re.search(r"创建.*女|加一个女|新建女主|要一个女主", text):
        name = "女主角"
        template = FEMALE_TEMPLATES[0]
        thinking.append("识别角色：女主角")
        thinking.append(f"使用官方模板 {template}")
        calls.append({
            "name": "create_character",
            "arguments": {"template_id": template, "name": name, "add_to_scene": True},
            "note": "创建女主角并加入分镜",
        })
        created_female = True

    if re.search(r"创建.*男|加一个男|新建男主", text) and "女" not in text[:8]:
        thinking.append("识别角色：男主角")
        calls.append({
            "name": "create_character",
            "arguments": {"template_id": MALE_TEMPLATES[0], "name": "男主角", "add_to_scene": True},
            "note": "创建男主角并加入分镜",
        })

    char = _find_character(context, text)
    if created_female:
        char = {"characterId": "__pending_female__", "name": "女主角"}

    if re.search(r"加入.*(场景|分镜|客厅)|放进|放到.*里|加入当前", text):
        target = _char_id(char) or (context.get("focus") or {}).get("character_id")
        if not target and created_female:
            thinking.append("女主角刚创建，已随创建加入分镜")
        elif not target:
            return {"thinking": thinking + ["未找到要加入的角色"], "calls": calls, "error": "当前没有可加入的角色。请先创建或说明角色名称。"}
        else:
            thinking.append("把已有角色加入当前分镜")
            calls.append({"name": "add_character_to_scene", "arguments": {"character_id": target}, "note": "加入分镜"})

    if any(k in text for k in ("客厅", "房间")) and ("放" in text or "布置" in text or "场景" in text or "里" in text):
        if not _find_object(context, "table", "桌子") or "客厅" in text:
            thinking.append("客厅需要家具，放入房间预设")
            calls.append({"name": "place_room_preset", "arguments": {}, "note": "布置房间"})
        if "沙发" in text and not _find_object(context, "sofa", "沙发"):
            calls.append({"name": "add_prop", "arguments": {"catalog_id": "sofa", "position": [-0.2, 0, 1.1]}, "note": "添加沙发"})

    if "沙发" in text and not _find_object(context, "sofa", "沙发") and not any(c["name"] == "add_prop" and c["arguments"].get("catalog_id") == "sofa" for c in calls):
        if re.search(r"沙发|走到沙发|坐.*沙发", text):
            thinking.append("场景里没有沙发，先添加")
            calls.append({"name": "add_prop", "arguments": {"catalog_id": "sofa", "position": [0, 0, 1.15]}, "note": "添加沙发"})

    if re.search(r"桌子|桌旁|桌边", text) and not _find_object(context, "table", "桌子"):
        if re.search(r"走|坐|旁边|旁", text) or "桌子" in text:
            thinking.append("场景里没有桌子，先添加")
            calls.append({"name": "add_prop", "arguments": {"catalog_id": "table", "position": [0, 0, 0.15]}, "note": "添加桌子"})

    if re.search(r"窗边|窗旁|窗口|窗外|走到窗", text) and not _find_object(context, "window", "窗"):
        thinking.append("场景里没有窗户，先添加")
        calls.append({"name": "add_prop", "arguments": {"catalog_id": "window", "position": [1.6, 1.0, 0.2]}, "note": "添加窗户"})

    walk = bool(re.search(r"走(到|向|去|过去)|走去|走过去|走到", text))
    sit = bool(re.search(r"坐下|坐下来|坐着|坐到", text))
    stand_center = bool(re.search(r"房间中央|场景中央|中间|中央", text) and re.search(r"站|放|到", text))

    dest = None
    dest_note = ""
    if "沙发" in text:
        dest = "__sofa_beside__"
        dest_note = "沙发旁边"
    elif re.search(r"桌子|桌旁|桌边", text):
        dest = "__table_beside__"
        dest_note = "桌子旁边"
    elif stand_center or "中央" in text:
        dest = _center()
        dest_note = "房间中央"
    elif re.search(r"窗边|窗旁|窗口|走到窗", text):
        dest = "__window_beside__"
        dest_note = "窗边"
    elif "门口" in text or "门边" in text:
        door = _find_object(context, "door", "门")
        dest = _beside(door, (0.4, 0, 0.4)) if door else [-1.0, 0, 0.6]
        dest_note = "门口"

    if dest is not None and (walk or stand_center or "站在" in text or "放到" in text or "移到" in text):
        cid = _instance_id(char) or _char_id(char)
        if not cid and not created_female:
            return {"thinking": thinking + ["未找到角色"], "calls": calls, "error": "不知道要移动谁。请先创建角色或点选角色。"}
        thinking.append(f"目标位置：{dest_note or dest}")
        args: dict[str, Any] = {"character_ref": cid or "女主角", "position": dest if isinstance(dest, list) else dest, "animate": walk}
        if dest == "__table_beside__":
            args["near"] = "table"
            args.pop("position", None)
        if dest == "__sofa_beside__":
            args["near"] = "sofa"
            args.pop("position", None)
        if dest == "__window_beside__":
            args["near"] = "window"
            args.pop("position", None)
        calls.append({"name": "move_character", "arguments": args, "note": ("走路到" if walk else "放到") + dest_note})
        if walk:
            calls.append({
                "name": "set_character_action",
                "arguments": {"character_ref": cid or "女主角", "action": "walk"},
                "note": "设置走路",
            })
            calls.append({
                "name": "create_keyframe",
                "arguments": {"time": 0, "object_ref": cid or "女主角", "animation": "walk"},
                "note": "记录走路关键帧",
            })

    if sit:
        cid = _instance_id(char) or _char_id(char) or "女主角"
        thinking.append("动作：坐下")
        calls.append({"name": "set_character_pose", "arguments": {"character_ref": cid, "pose": "sit"}, "note": "坐下"})
        calls.append({
            "name": "create_keyframe",
            "arguments": {"time": 2, "object_ref": cid, "pose": "sit"},
            "note": "记录坐下关键帧",
        })

    if re.search(r"看向窗外|望向窗外|看窗外", text):
        cid = _instance_id(char) or _char_id(char) or "女主角"
        thinking.append("角色看向窗外")
        calls.append({"name": "set_character_action", "arguments": {"character_ref": cid, "action": "look"}, "note": "看向窗外"})
        calls.append({"name": "set_camera", "arguments": {"shot_type": "medium", "motion": "static"}, "note": "中景看窗"})
    elif re.search(r"看向男主|望向男主|转身看", text):
        cid = _instance_id(char) or _char_id(char) or "女主角"
        male = _find_character(context, "男主") or _find_object(context, "男主", "男主角")
        thinking.append("角色转身看向男主")
        calls.append({"name": "set_character_action", "arguments": {"character_ref": cid, "action": "look"}, "note": "看向男主"})
        calls.append({"name": "set_camera_target", "arguments": {"target_ref": _instance_id(male) or _char_id(male) or cid}, "note": "镜头看向男主"})
    elif re.search(r"对准|看向|对着|对着拍|镜头对准|摄像机对准", text):
        cid = _instance_id(char) or _char_id(char) or "女主角"
        thinking.append("摄像机对准角色")
        calls.append({"name": "set_camera_target", "arguments": {"target_ref": cid}, "note": "对准角色"})
        calls.append({"name": "select_camera", "arguments": {}, "note": "切到机位视角"})

    if re.search(r"推进|推近|靠近|推到近景|慢慢推|dolly in|push", text, re.I):
        thinking.append("镜头推进")
        calls.append({"name": "set_camera_motion", "arguments": {"motion": "push_in", "amount": 1.4}, "note": "推进"})
    elif re.search(r"拉远|拉出|远景|pull", text, re.I):
        thinking.append("镜头拉远")
        calls.append({"name": "set_camera_motion", "arguments": {"motion": "pull_out", "amount": 2.2}, "note": "拉远"})
        if re.search(r"推|近景", text):
            calls.append({"name": "set_camera_motion", "arguments": {"motion": "push_in", "amount": 1.6}, "note": "再推进到近景"})

    if re.search(r"远景.*近景|从远.*近", text):
        if not any(c["name"] == "set_camera_motion" for c in calls):
            thinking.append("远景到近景：先拉远再推进")
            calls.append({"name": "set_camera_motion", "arguments": {"motion": "pull_out", "amount": 2.4}, "note": "远景"})
            calls.append({"name": "set_camera_motion", "arguments": {"motion": "push_in", "amount": 1.8}, "note": "推到近景"})

    if duration and any(c["name"] in {"create_shot", "duplicate_shot"} for c in calls):
        pass
    elif duration and "镜头" in text and not any(c["name"] == "set_shot_duration" for c in calls):
        calls.append({"name": "set_shot_duration", "arguments": {"duration": duration}, "note": f"时长 {duration}s"})

    if re.search(r"创建机位|加(一个)?(相机|摄像机|机位)", text):
        calls.append({"name": "create_camera", "arguments": {}, "note": "添加机位"})

    if re.search(r"布置.*(客厅|房间)|创建场景|放一个房间", text) and not any(c["name"] == "place_room_preset" for c in calls):
        thinking.append("布置房间预设")
        calls.append({"name": "place_room_preset", "arguments": {"preset": "room"}, "note": "布置房间"})

    if re.search(r"自动分镜|自动生成分镜", text):
        thinking.append("复制当前分镜并写描述")
        calls.append({"name": "duplicate_shot", "arguments": {}, "note": "复制为新分镜"})
        calls.append({
            "name": "set_shot_description",
            "arguments": {"description": message},
            "note": "写入分镜描述",
        })
        calls.append({"name": "generate_prompt", "arguments": {"kind": "video"}, "note": "生成视频提示词"})

    if re.search(r"让当前角色走路|添加动作|走路", text) and not any(c["name"] == "set_character_action" for c in calls):
        cid = _instance_id(char) or _char_id(char)
        if cid:
            calls.append({
                "name": "set_character_action",
                "arguments": {"character_ref": cid, "action": "walk"},
                "note": "走路",
            })

    if re.search(r"打架|格斗|fight", text) and not any(c["name"] == "set_character_action" for c in calls):
        cid = _instance_id(char) or _char_id(char) or "女主角"
        calls.append({
            "name": "set_character_action",
            "arguments": {"character_ref": cid, "action": "fight"},
            "note": "打架",
        })

    if re.search(r"恢复(历史|版本|生成)|restore", text, re.I):
        gid = ""
        m = re.search(r"(?:generation[_-]?id|版本)[:：\s]*([A-Za-z0-9]+)", message, re.I)
        if m:
            gid = m.group(1)
        thinking.append("恢复历史生成版本，需要确认")
        calls.append({"name": "restore_generation", "arguments": {"generation_id": gid}, "note": "恢复历史版本"})

    if re.search(r"做成.*视频|生成(一个)?视频|图生视频", text) and not any(c["name"] == "generate_video" for c in calls):
        thinking.append("在导演动作之后调用视频生成")
        dur = 5.0
        dm = re.search(r"(\d+(?:\.\d+)?)秒", text)
        if dm:
            dur = float(dm.group(1))
        calls.append({"name": "generate_video", "arguments": {"duration": dur}, "note": f"生成 {dur}s 视频"})
    elif re.search(r"生成(这个)?镜头的画面|生成画面|生成参考图|出一张图|生成图片", text) and not any(c["name"] == "generate_image" for c in calls):
        thinking.append("在导演动作之后调用图片生成")
        calls.append({"name": "generate_image", "arguments": {"kind": "image"}, "note": "生成参考画面"})

    if not calls:
        llm_plan = _try_llm(message, context)
        if llm_plan:
            return llm_plan
        return {
            "thinking": ["未能从指令中解析出可执行 Tool"],
            "calls": [],
            "error": "无法理解这条指令。可以说「创建女主角」「走到桌子旁边坐下」「镜头推进」「撤销」。",
        }

    for call in calls:
        if not is_allowed(call["name"]):
            return {"thinking": thinking, "calls": [], "error": f"拒绝未注册 Tool：{call['name']}"}

    return {"thinking": thinking, "calls": calls, "error": None}


def _try_llm(message: str, context: dict) -> dict[str, Any] | None:
    try:
        from ..core.config import settings
        from ..providers.llm import get_llm_provider
        key = settings.llm_api_key or settings.dashscope_api_key
        if settings.llm_provider == "mock" or not key:
            return None
        provider = get_llm_provider()
    except Exception:
        return None

    tools = [{"name": t.name, "description": t.description} for t in ALLOWED.values()]
    slim = {
        "scene_id": context.get("scene_id"),
        "scene_name": context.get("scene_name"),
        "objects": [
            {"id": o.get("id"), "name": o.get("name"), "characterId": o.get("characterId"), "position": o.get("position"), "catalogId": o.get("catalogId")}
            for o in (context.get("objects") or [])
        ],
        "cameras": context.get("cameras"),
        "focus": context.get("focus"),
    }
    prompt = (
        "你是 3D 导演台的规划器。只输出 JSON："
        '{"thinking":["..."],"calls":[{"name":"tool","arguments":{},"note":"..."}],"error":null}。'
        f"可用 Tool：{json.dumps(tools, ensure_ascii=False)}。"
        "禁止编造 Tool 名。不要生成视频。根据真实 context 选 character_ref / near。"
    )
    try:
        import asyncio
        from ..providers.llm.dashscope_llm import DashScopeLLMProvider
        if not isinstance(provider, DashScopeLLMProvider):
            return None

        def _call() -> dict:
            resp = provider.client.chat.completions.create(
                model=provider.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps({"message": message, "context": slim}, ensure_ascii=False)},
                ],
            )
            raw = resp.choices[0].message.content or "{}"
            return json.loads(raw)

        data = asyncio.get_event_loop().run_until_complete(asyncio.to_thread(_call)) if False else None
    except Exception:
        return None

    # Use thread from async route instead
    return None


async def try_llm_async(message: str, context: dict) -> dict[str, Any] | None:
    try:
        from ..core.config import settings
        from ..providers.llm import get_llm_provider
        key = settings.llm_api_key or settings.dashscope_api_key
        if settings.llm_provider == "mock" or not key:
            return None
        provider = get_llm_provider()
        tools = [{"name": t.name, "description": t.description} for t in ALLOWED.values()]
        slim = {
            "scene_id": context.get("scene_id"),
            "objects": [
                {"id": o.get("id"), "name": o.get("name"), "characterId": o.get("characterId"), "position": o.get("position")}
                for o in (context.get("objects") or [])
            ],
            "focus": context.get("focus"),
        }
        prompt = (
            "你是 3D 导演台规划器。只输出 JSON："
            '{"thinking":["..."],"calls":[{"name":"tool","arguments":{},"note":"..."}],"error":null}。'
            f"Tool 白名单：{json.dumps([t['name'] for t in tools], ensure_ascii=False)}。"
            "禁止未注册 Tool。不要生成视频。"
        )
        import asyncio

        def _call() -> dict:
            resp = provider.client.chat.completions.create(  # type: ignore[attr-defined]
                model=provider.model,  # type: ignore[attr-defined]
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps({"message": message, "context": slim}, ensure_ascii=False)},
                ],
            )
            return json.loads(resp.choices[0].message.content or "{}")

        data = await asyncio.to_thread(_call)
        calls = [c for c in (data.get("calls") or []) if isinstance(c, dict) and is_allowed(str(c.get("name") or ""))]
        if not calls:
            return None
        return {"thinking": data.get("thinking") or ["LLM 规划"], "calls": calls, "error": data.get("error")}
    except Exception:
        return None
