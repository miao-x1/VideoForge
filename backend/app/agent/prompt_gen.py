"""根据真实 DirectorContext 生成提示词。不调用视频模型。"""
from __future__ import annotations

from typing import Any


def generate_prompt(kind: str, context: dict[str, Any]) -> dict[str, Any]:
    objects = context.get("objects") or []
    cameras = context.get("cameras") or []
    chars = [o for o in objects if o.get("characterId")]
    props = [o for o in objects if not o.get("characterId")]
    cam = next((c for c in cameras if c.get("id") == context.get("active_camera")), cameras[0] if cameras else {})
    scene_name = context.get("scene_name") or "未命名分镜"
    duration = context.get("shot_duration") or 4
    desc = context.get("shot_description") or ""

    char_bits = []
    for c in chars:
        bit = f"{c.get('name')}"
        if c.get("animation"):
            bit += f"，动作 {c.get('animation')}"
        if c.get("pose"):
            bit += f"，姿势 {c.get('pose')}"
        pos = c.get("position")
        if pos:
            bit += f"，位置 ({pos[0]:.2f},{pos[1]:.2f},{pos[2]:.2f})"
        char_bits.append(bit)
    prop_bits = [f"{p.get('name')}" for p in props]
    motion = cam.get("motion") or "static"
    fov = cam.get("fov") or 45

    body = {
        "scene": scene_name,
        "duration": duration,
        "description": desc,
        "characters": char_bits or ["无角色"],
        "props": prop_bits or ["无道具"],
        "camera": f"fov={fov}, motion={motion}, pos={cam.get('position')}",
    }

    if kind == "image":
        text = (
            f"电影静帧，{scene_name}。"
            f"角色：{'；'.join(char_bits) or '无人'}。"
            f"场景物件：{'、'.join(prop_bits) or '空镜'}。"
            f"机位 fov {fov}，{motion}。"
            f"{desc}"
        )
    elif kind == "motion":
        text = (
            f"动作提示：{'；'.join(char_bits) or '无角色可描述动作'}。"
            f"时长 {duration}s。"
        )
    elif kind == "camera":
        text = (
            f"镜头提示：{scene_name}，时长 {duration}s，"
            f"机位 {cam.get('name') or '主相机'} fov {fov}，运动 {motion}，"
            f"位置 {cam.get('position')}，目标 {cam.get('target')}。"
        )
    elif kind == "scene":
        text = (
            f"场景提示：{scene_name}。"
            f"环境物件：{'、'.join(prop_bits) or '空场景'}。"
            f"在场角色：{'；'.join(char_bits) or '无'}。"
        )
    else:
        text = (
            f"电影视频，{duration} 秒，{scene_name}。"
            f"{desc + '。' if desc else ''}"
            f"角色：{'；'.join(char_bits) or '无人入镜'}。"
            f"场景：{'、'.join(prop_bits) or '空镜'}。"
            f"镜头 {motion}，fov {fov}，机位 {cam.get('position')}。"
            "真实光影，连贯动作，不要字幕。"
        )

    return {"kind": kind, "prompt": text.strip(), "basis": body}
