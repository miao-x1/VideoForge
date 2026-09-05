"""通过 Service 层改 DirectorScene.data_json。Agent 不直接写 SQL。"""
from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from ..db.models import DirectorCharacter, DirectorScene
from ..db.ownership import DirectorScope
from .errors import RESOURCE_NOT_FOUND, TOOL_ERROR, AgentError

NEAR_DEFAULTS: dict[str, list[float]] = {
    "window": [1.6, 1.0, 0.2],
    "table": [0.0, 0.0, 0.15],
    "sofa": [0.0, 0.0, 1.15],
    "door": [-1.0, 0.0, 0.6],
}

PROP_NAMES = {"window": "窗", "table": "桌子", "sofa": "沙发", "door": "门", "chair": "椅子"}


def _owned(model, scope: DirectorScope):
    return (model.user_id == scope.user_id) & (model.project_id == scope.project_id)


def _vec(value: Any, fallback: list[float] | None = None) -> list[float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    if isinstance(value, dict):
        return [float(value.get("x") or 0), float(value.get("y") or 0), float(value.get("z") or 0)]
    return list(fallback or [0.0, 0.0, 0.0])


def _beside(pos: list[float], offset: tuple[float, float, float] = (0.55, 0.0, 0.1)) -> list[float]:
    return [pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2]]


def _data(scene: DirectorScene) -> dict[str, Any]:
    return copy.deepcopy(scene.data_json) if isinstance(scene.data_json, dict) else {}


def _save(scene: DirectorScene, data: dict[str, Any]) -> None:
    data["sceneId"] = scene.scene_id
    if scene.scene_name:
        data["sceneName"] = scene.scene_name
    scene.data_json = data
    flag_modified(scene, "data_json")


async def load_scene(
    db: AsyncSession,
    scope: DirectorScope,
    scene_id: str,
    seed: dict[str, Any] | None = None,
) -> DirectorScene:
    row = (
        await db.execute(
            select(DirectorScene).where(DirectorScene.scene_id == scene_id, _owned(DirectorScene, scope))
        )
    ).scalar_one_or_none()
    if row is None and not scene_id:
        raise AgentError(RESOURCE_NOT_FOUND, "场景不存在")
    if row is None:
        row = DirectorScene(
            scene_id=scene_id,
            user_id=scope.user_id,
            project_id=scope.project_id,
            scene_name=str((seed or {}).get("scene_name") or ""),
            is_current=True,
            data_json=_seed_data(scene_id, seed),
        )
        db.add(row)
        await db.flush()
        return row
    data = _data(row)
    if seed and not (data.get("objects") or []):
        seeded = _seed_data(scene_id, seed)
        if seeded.get("objects"):
            _save(row, seeded)
    return row


def _seed_data(scene_id: str, seed: dict[str, Any] | None) -> dict[str, Any]:
    seed = seed or {}
    env = seed.get("environment") if isinstance(seed.get("environment"), dict) else {}
    return {
        "sceneId": scene_id,
        "sceneName": seed.get("scene_name") or "",
        "objects": [o for o in (seed.get("objects") or []) if isinstance(o, dict)],
        "cameras": [c for c in (seed.get("cameras") or []) if isinstance(c, dict)],
        "activeCamera": seed.get("active_camera") or "",
        "environment": env,
        "shotDuration": seed.get("shot_duration") or 4,
        "shotDescription": seed.get("shot_description") or "",
        "aspectRatio": seed.get("aspect_ratio") or "9:16",
    }


def _objects(data: dict[str, Any]) -> list[dict[str, Any]]:
    objs = data.get("objects")
    if not isinstance(objs, list):
        objs = []
        data["objects"] = objs
    return objs


def _cameras(data: dict[str, Any]) -> list[dict[str, Any]]:
    cams = data.get("cameras")
    if not isinstance(cams, list):
        cams = []
        data["cameras"] = cams
    return cams


def _find_object(objects: list[dict[str, Any]], ref: Any) -> dict[str, Any] | None:
    text = str(ref or "").strip()
    if not text:
        chars = [o for o in objects if o.get("characterId")]
        return chars[0] if len(chars) == 1 else None
    for obj in objects:
        if str(obj.get("id") or "") == text or str(obj.get("characterId") or "") == text:
            return obj
    aliases = {
        "女主": ("女",),
        "女主角": ("女",),
        "女生": ("女",),
        "男主": ("男",),
        "男主角": ("男",),
        "男生": ("男",),
    }
    keys = aliases.get(text)
    if keys:
        for obj in objects:
            name = str(obj.get("name") or "")
            if any(k in name for k in keys):
                return obj
    for obj in objects:
        name = str(obj.get("name") or "")
        catalog = str(obj.get("catalogId") or "")
        if text in name or text == catalog:
            return obj
    return None


def _find_camera(cameras: list[dict[str, Any]], ref: Any) -> dict[str, Any] | None:
    text = str(ref or "").strip()
    if not text and cameras:
        return cameras[0]
    for cam in cameras:
        if str(cam.get("id") or "") == text or str(cam.get("name") or "") == text:
            return cam
    return cameras[0] if cameras else None


def _ensure_prop(objects: list[dict[str, Any]], catalog: str) -> dict[str, Any]:
    hit = _find_object(objects, catalog)
    if hit:
        return hit
    pos = list(NEAR_DEFAULTS.get(catalog, [0.0, 0.0, 0.0]))
    obj = {
        "id": f"prop_{catalog}_{uuid.uuid4().hex[:6]}",
        "name": PROP_NAMES.get(catalog, catalog),
        "type": "prop",
        "catalogId": catalog,
        "position": pos,
        "rotation": [0, 0, 0],
        "scale": [1, 1, 1],
    }
    objects.append(obj)
    return obj


def _ok(message: str, **data: Any) -> dict[str, Any]:
    return {"success": True, "message": message, **data}


async def apply_scene_tool(
    db: AsyncSession,
    scope: DirectorScope,
    *,
    scene_id: str,
    name: str,
    arguments: dict[str, Any],
    seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scene = await load_scene(db, scope, scene_id, seed=seed)
    data = _data(scene)
    objects = _objects(data)
    cameras = _cameras(data)
    args = arguments or {}

    if name == "move_character":
        obj = _find_object(objects, args.get("character_id") or args.get("character_ref"))
        if obj is None:
            raise AgentError(TOOL_ERROR, "找不到要移动的角色")
        near = str(args.get("near") or "")
        if near:
            prop = _ensure_prop(objects, near)
            pos = _beside(_vec(prop.get("position")))
        elif args.get("position") in {"__window_beside__", "__table_beside__", "__sofa_beside__"}:
            key = str(args["position"]).replace("__", "").replace("_beside", "")
            prop = _ensure_prop(objects, key)
            pos = _beside(_vec(prop.get("position")))
        else:
            pos = _vec(args.get("position"), obj.get("position") or [0, 0, 0])
        obj["position"] = pos
        if args.get("animate"):
            obj["animation"] = "walk"
        _save(scene, data)
        return _ok("已移动角色", character_id=obj.get("characterId") or obj.get("id"), position=pos)

    if name in {"set_character_pose", "set_character_action", "set_character_expression", "rotate_character", "scale_character"}:
        obj = _find_object(objects, args.get("character_id") or args.get("character_ref"))
        if obj is None:
            raise AgentError(TOOL_ERROR, "找不到角色")
        if name == "set_character_pose":
            obj["pose"] = str(args.get("pose") or "stand")
        if name == "set_character_action":
            obj["animation"] = str(args.get("action") or "idle")
        if name == "set_character_expression":
            obj["expression"] = str(args.get("expression") or "")
        if name == "rotate_character" and args.get("rotation") is not None:
            obj["rotation"] = _vec(args.get("rotation"), obj.get("rotation") or [0, 0, 0])
        if name == "scale_character" and args.get("scale") is not None:
            obj["scale"] = _vec(args.get("scale"), obj.get("scale") or [1, 1, 1])
        _save(scene, data)
        return _ok("已更新角色", character_id=obj.get("characterId") or obj.get("id"), pose=obj.get("pose"), action=obj.get("animation"))

    if name in {"add_prop", "move_prop", "rotate_prop", "scale_prop", "remove_prop"}:
        catalog = str(args.get("catalog_id") or args.get("near") or args.get("prop_ref") or "")
        if name == "add_prop":
            obj = _ensure_prop(objects, catalog or "table")
            if args.get("position") is not None:
                obj["position"] = _vec(args.get("position"), obj["position"])
            _save(scene, data)
            return _ok("已添加道具", object_id=obj["id"], catalog_id=obj.get("catalogId"))
        obj = _find_object(objects, args.get("object_id") or catalog)
        if obj is None:
            raise AgentError(TOOL_ERROR, "找不到物件")
        if name == "remove_prop":
            objects.remove(obj)
        elif name == "move_prop":
            obj["position"] = _vec(args.get("position"), obj.get("position"))
        elif name == "rotate_prop":
            obj["rotation"] = _vec(args.get("rotation"), obj.get("rotation"))
        elif name == "scale_prop":
            obj["scale"] = _vec(args.get("scale"), obj.get("scale"))
        _save(scene, data)
        return _ok("已更新物件", object_id=obj.get("id"))

    if name in {"create_camera", "select_camera", "move_camera", "rotate_camera", "set_camera_fov", "set_camera_target", "set_camera_motion", "set_camera"}:
        cam = _find_camera(cameras, args.get("camera_id"))
        if name == "create_camera" or cam is None:
            cam = {
                "id": f"camera_{uuid.uuid4().hex[:6]}",
                "name": str(args.get("name") or f"机位{len(cameras)+1}"),
                "position": [0, 1.6, 5],
                "rotation": [0, 0, 0],
                "fov": 45,
            }
            cameras.append(cam)
        if args.get("position") is not None:
            cam["position"] = _vec(args.get("position"), cam.get("position"))
        if args.get("rotation") is not None:
            cam["rotation"] = _vec(args.get("rotation"), cam.get("rotation"))
        if args.get("fov") is not None:
            cam["fov"] = float(args.get("fov") or 45)
        if args.get("motion") is not None:
            cam["motion"] = str(args.get("motion"))
        if name == "set_camera_motion" and not args.get("motion"):
            cam["motion"] = "push_in"
        if name in {"set_camera_target", "set_camera"}:
            target_obj = _find_object(objects, args.get("target_ref") or args.get("character_ref") or args.get("character_id"))
            if target_obj:
                pos = _vec(target_obj.get("position"))
                cam["target"] = [pos[0], pos[1] + 1.3, pos[2]]
            elif args.get("target") is not None:
                cam["target"] = _vec(args.get("target"))
        if name == "set_camera" and args.get("shot_type"):
            data["shotType"] = str(args.get("shot_type"))
        data["activeCamera"] = cam["id"]
        _save(scene, data)
        return _ok("已更新机位", camera_id=cam["id"], position=cam.get("position"), fov=cam.get("fov"), motion=cam.get("motion"))

    if name in {"create_shot", "duplicate_shot"}:
        new_id = f"shot_{uuid.uuid4().hex[:8]}"
        clone = copy.deepcopy(data)
        clone["sceneId"] = new_id
        clone["sceneName"] = str(args.get("name") or f"镜头 {len(data.get('scenes') or []) + 1}")
        if args.get("duration") is not None:
            clone["shotDuration"] = float(args["duration"])
        if args.get("description"):
            clone["shotDescription"] = str(args["description"])
        if args.get("shot_type"):
            clone["shotType"] = str(args["shot_type"])
        if args.get("camera_movement"):
            clone["cameraMovement"] = str(args["camera_movement"])
        row = DirectorScene(
            scene_id=new_id,
            user_id=scope.user_id,
            project_id=scope.project_id,
            scene_name=clone["sceneName"],
            is_current=False,
            data_json=clone,
        )
        db.add(row)
        return _ok("已创建镜头", scene_id=new_id, shot_id=new_id, duration=clone.get("shotDuration"))

    if name in {"update_shot", "set_shot_duration", "set_shot_description", "set_shot_type", "update_storyboard", "rename_scene", "update_scene"}:
        if args.get("name"):
            scene.scene_name = str(args["name"])
            data["sceneName"] = scene.scene_name
        if args.get("duration") is not None:
            data["shotDuration"] = float(args["duration"])
        if args.get("description") is not None:
            data["shotDescription"] = str(args["description"])
        if args.get("shot_type"):
            data["shotType"] = str(args["shot_type"])
        if args.get("camera_movement"):
            data["cameraMovement"] = str(args["camera_movement"])
        if args.get("emotion"):
            data["emotion"] = str(args["emotion"])
        if args.get("storyboard") is not None:
            data["storyboard"] = args["storyboard"]
        _save(scene, data)
        return _ok("已更新镜头", scene_id=scene.scene_id)

    if name in {"delete_shot", "delete_scene"}:
        target_id = str(args.get("scene_id") or args.get("shot_id") or scene.scene_id)
        row = await load_scene(db, scope, target_id)
        await db.delete(row)
        return _ok("已删除镜头", scene_id=target_id)

    if name == "create_scene":
        new_id = str(args.get("scene_id") or f"scene_{uuid.uuid4().hex[:8]}")
        row = DirectorScene(
            scene_id=new_id,
            user_id=scope.user_id,
            project_id=scope.project_id,
            scene_name=str(args.get("name") or "新场景"),
            is_current=False,
            data_json={"sceneId": new_id, "sceneName": str(args.get("name") or "新场景"), "objects": [], "cameras": []},
        )
        db.add(row)
        return _ok("已创建场景", scene_id=new_id)

    if name == "place_room_preset":
        data["environment"] = {**(data.get("environment") or {}), "preset": str(args.get("preset") or "room")}
        _ensure_prop(objects, "table")
        _save(scene, data)
        return _ok("已布置房间")

    if name == "change_environment":
        env = dict(data.get("environment") or {})
        env.update({k: v for k, v in args.items() if k != "scene_id"})
        data["environment"] = env
        _save(scene, data)
        return _ok("已更新环境")

    if name in {"create_character", "add_character_to_scene"}:
        cid = str(args.get("character_id") or f"char_{uuid.uuid4().hex[:8]}")
        cname = str(args.get("name") or "角色")
        existing = _find_object(objects, cid) or _find_object(objects, cname)
        if existing is None:
            objects.append({
                "id": f"obj_{cid}",
                "name": cname,
                "type": "character",
                "characterId": cid,
                "position": _vec(args.get("position"), [0, 0, 0]),
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
            })
        char = (
            await db.execute(select(DirectorCharacter).where(DirectorCharacter.id == cid, _owned(DirectorCharacter, scope)))
        ).scalar_one_or_none()
        if char is None and name == "create_character":
            clash = await db.get(DirectorCharacter, cid)
            if clash is None:
                db.add(DirectorCharacter(
                    id=cid,
                    user_id=scope.user_id,
                    project_id=scope.project_id,
                    name=cname,
                    template_id=str(args.get("template_id") or ""),
                    source_type="official",
                    data_json={"id": cid, "name": cname, "templateId": args.get("template_id")},
                ))
        _save(scene, data)
        return _ok("已加入角色", character_id=cid)

    if name == "remove_character_from_scene":
        obj = _find_object(objects, args.get("character_id") or args.get("character_ref"))
        if obj is None:
            raise AgentError(TOOL_ERROR, "找不到要移除的角色")
        objects.remove(obj)
        _save(scene, data)
        return _ok("已移除角色", character_id=obj.get("characterId"))

    if name in {"create_keyframe", "update_keyframe", "delete_keyframe", "set_animation_duration", "update_timeline"}:
        timeline = dict(data.get("timeline") or {"duration": data.get("shotDuration") or 4, "keys": []})
        keys = list(timeline.get("keys") or [])
        if name == "create_keyframe":
            keys.append({"time": args.get("time") or 0, "object_ref": args.get("object_ref"), "animation": args.get("animation"), "pose": args.get("pose")})
        elif name == "delete_keyframe" and keys:
            keys.pop()
        if args.get("duration") is not None:
            timeline["duration"] = float(args["duration"])
        timeline["keys"] = keys
        data["timeline"] = timeline
        _save(scene, data)
        return _ok("已更新时间线", timeline=timeline)

    raise AgentError(TOOL_ERROR, f"服务端未实现 Tool：{name}")
