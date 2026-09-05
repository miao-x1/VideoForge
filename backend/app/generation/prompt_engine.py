"""把 DirectorContext + 镜头方案编成生成提示词。不把用户原话直接扔给模型。"""
from __future__ import annotations

from typing import Any


def compile_prompts(
    *,
    kind: str,
    context: dict[str, Any],
    shot: dict[str, Any] | None = None,
    extra: str = "",
) -> dict[str, str]:
    shot = shot or {}
    objects = context.get("objects") or []
    chars = [o for o in objects if o.get("characterId")]
    props = [o for o in objects if not o.get("characterId")]
    cam = next(
        (c for c in (context.get("cameras") or []) if c.get("id") == context.get("active_camera")),
        (context.get("cameras") or [{}])[0] if context.get("cameras") else {},
    )
    char_text = "；".join(
        f"{c.get('name')}，姿势 {c.get('pose') or 'stand'}，动作 {c.get('animation') or 'idle'}"
        for c in chars
    ) or "一位年轻女性"
    prop_text = "、".join(str(p.get("name") or "") for p in props if p.get("name")) or "室内客厅"
    scene_name = context.get("scene_name") or "客厅"
    duration = shot.get("duration") or context.get("shot_duration") or 5
    shot_type = shot.get("shot_type") or context.get("shot_type") or _infer_shot_type(cam)
    movement = shot.get("camera_movement") or cam.get("motion") or "static"
    emotion = shot.get("emotion") or context.get("emotion") or ""
    visual = shot.get("visual_description") or context.get("shot_description") or extra
    time_of_day = shot.get("time_of_day") or context.get("time_of_day") or ""
    lighting = "夜晚室内暖灯，安静低对比" if "夜" in f"{time_of_day}{visual}{extra}" else "自然室内光"
    composition = "严格按照导演台已发送构图的空间关系、角色站位和机位，不要改站位。" if context.get("composition_url") else ""

    image = (
        f"电影剧照，{shot_type}，{scene_name}，{prop_text}。"
        f"角色：{char_text}。"
        f"{visual + '。' if visual else ''}"
        f"情绪：{emotion or '克制、安静'}。光线：{lighting}。"
        f"构图干净，真实皮肤与布料，电影色彩，不要字幕，不要水印。"
        f"{composition}"
    )
    video = (
        f"电影短镜头，{duration} 秒，{shot_type}，镜头运动 {movement}。"
        f"{scene_name}。{char_text}。{visual}。"
        f"动作连贯，情绪 {emotion or '疲惫安静'}，{lighting}。"
        f"不要跳切，不要字幕，不要变形。"
    )
    negative = "字幕,文字,水印,扭曲五官,多余手指,卡通滤镜过重,低分辨率"
    camera = f"{shot_type}，{movement}，fov={cam.get('fov') or 45}，机位 {cam.get('position')}"
    motion = shot.get("character_action") or (chars[0].get("animation") if chars else "idle") or "idle"

    if kind == "image":
        prompt = image
    elif kind == "video":
        prompt = video
    else:
        prompt = image

    return {
        "image_prompt": image,
        "video_prompt": video,
        "negative_prompt": negative,
        "camera_prompt": camera,
        "motion_prompt": str(motion),
        "prompt": prompt,
    }


def _infer_shot_type(cam: dict) -> str:
    fov = float(cam.get("fov") or 45)
    if fov <= 32:
        return "close-up"
    if fov >= 55:
        return "wide shot"
    return "medium shot"
