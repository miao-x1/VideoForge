"""DirectorContext：Agent 运行时上下文。不是数据库表，不把整库塞给 LLM。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DirectorCharacter, DirectorGeneration, DirectorLibraryMeta, DirectorScene
from ..db.ownership import DirectorScope
from .registry import TOOLS


def _owned(model, scope: DirectorScope):
    return (model.user_id == scope.user_id) & (model.project_id == scope.project_id)


def _slim_object(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": obj.get("id"),
        "name": obj.get("name"),
        "type": obj.get("type"),
        "catalogId": obj.get("catalogId"),
        "characterId": obj.get("characterId"),
        "position": obj.get("position"),
        "rotation": obj.get("rotation"),
        "scale": obj.get("scale"),
        "animation": obj.get("animation"),
        "pose": obj.get("pose"),
    }


def _slim_camera(cam: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": cam.get("id"),
        "name": cam.get("name"),
        "position": cam.get("position"),
        "rotation": cam.get("rotation"),
        "fov": cam.get("fov"),
        "target": cam.get("target"),
        "motion": cam.get("motion"),
    }


async def build_director_context(
    db: AsyncSession,
    scope: DirectorScope,
    client: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = dict(client or {})
    scenes = (await db.execute(select(DirectorScene).where(_owned(DirectorScene, scope)))).scalars().all()
    characters = (await db.execute(select(DirectorCharacter).where(_owned(DirectorCharacter, scope)))).scalars().all()
    meta = (await db.execute(select(DirectorLibraryMeta).where(_owned(DirectorLibraryMeta, scope)))).scalar_one_or_none()
    gens = (
        await db.execute(
            select(DirectorGeneration)
            .where(_owned(DirectorGeneration, scope))
            .order_by(DirectorGeneration.id.desc())
            .limit(20)
        )
    ).scalars().all()

    scene_id = str(client.get("scene_id") or (meta.current_scene_id if meta else "") or "")
    current = next((s for s in scenes if s.scene_id == scene_id), None)
    if current is None:
        current = next((s for s in scenes if s.is_current), None) or (scenes[0] if scenes else None)
    if current is not None:
        scene_id = current.scene_id

    data = dict(current.data_json) if current and isinstance(current.data_json, dict) else {}
    client_objects = client.get("objects") if isinstance(client.get("objects"), list) else None
    client_cameras = client.get("cameras") if isinstance(client.get("cameras"), list) else None
    source_objects = client_objects if client_objects is not None else data.get("objects") or []
    if not source_objects:
        for row in scenes:
            blob = row.data_json if isinstance(row.data_json, dict) else {}
            source_objects = blob.get("objects") or []
            if source_objects:
                if not scene_id:
                    scene_id = row.scene_id
                break
    objects = [_slim_object(o) for o in source_objects if isinstance(o, dict)]
    cameras = [_slim_camera(c) for c in (client_cameras if client_cameras is not None else data.get("cameras") or []) if isinstance(c, dict)]

    char_assets = []
    for row in characters:
        blob = dict(row.data_json) if isinstance(row.data_json, dict) else {}
        char_assets.append({
            "id": row.id,
            "name": row.name or blob.get("name"),
            "templateId": row.template_id or blob.get("templateId"),
            "sourceType": row.source_type or blob.get("sourceType"),
            "primary_asset_id": row.primary_asset_id,
            "reference_asset_id": row.reference_asset_id,
        })

    current_gen = None
    history = []
    for row in gens:
        item = {
            "generation_id": row.generation_id,
            "kind": row.kind,
            "status": row.status,
            "version_number": row.version_number,
            "parent_generation_id": row.parent_generation_id,
            "output_asset_id": row.output_asset_id,
            "scene_id": row.scene_id,
        }
        history.append(item)
        if current and row.generation_id == current.current_generation_id:
            current_gen = item
    if current_gen is None and history:
        current_gen = next((h for h in history if h.get("scene_id") == scene_id), history[0])

    focus = client.get("focus") if isinstance(client.get("focus"), dict) else {}
    props = [o for o in objects if not o.get("characterId")]
    env = data.get("environment") if isinstance(data.get("environment"), dict) else client.get("environment") or {}

    return {
        "user_id": scope.user_id,
        "project_id": scope.project_id,
        "scene_id": scene_id,
        "scene_name": (current.scene_name if current else "") or client.get("scene_name") or data.get("sceneName") or "",
        "scene": {
            "scene_id": scene_id,
            "scene_name": (current.scene_name if current else "") or "",
            "current_generation_id": current.current_generation_id if current else None,
        },
        "characters": char_assets,
        "character_assets": [c["primary_asset_id"] for c in char_assets if c.get("primary_asset_id")],
        "props": props,
        "environment": env,
        "background_assets": [current.background_asset_id] if current and current.background_asset_id else [],
        "reference_assets": [current.reference_asset_id] if current and current.reference_asset_id else [],
        "camera": cameras[0] if cameras else {},
        "cameras": cameras,
        "shots": [
            {"id": s.scene_id, "name": s.scene_name, "duration": (s.data_json or {}).get("shotDuration") if isinstance(s.data_json, dict) else None}
            for s in scenes
        ],
        "storyboard": {
            "shot_description": data.get("shotDescription") or client.get("shot_description") or "",
            "shot_type": data.get("shotType") or client.get("shot_type"),
        },
        "timeline": data.get("timeline") or client.get("timeline") or {"duration": data.get("shotDuration") or 4, "keys": []},
        "objects": objects,
        "selected_character": focus.get("character_id") or client.get("selected_character"),
        "selected_object": focus.get("object_id") or client.get("selected_object"),
        "selected_camera": focus.get("camera_id") or client.get("selected_camera") or client.get("active_camera"),
        "selected_shot": focus.get("shot_id") or scene_id,
        "current_generation": current_gen,
        "generation_history": history[:12],
        "owned_generation_ids": [g.generation_id for g in gens],
        "owned_object_ids": [str(o.get("id") or "") for o in objects if o.get("id")],
        "owned_character_ids": [c.id for c in characters] + [str(o.get("characterId") or o.get("id") or "") for o in objects if o.get("characterId") or o.get("id")],
        "owned_camera_ids": [str(c.get("id") or "") for c in cameras if c.get("id")],
        "owned_scene_ids": [s.scene_id for s in scenes],
        "owned_asset_ids": [
            *[c["primary_asset_id"] for c in char_assets if c.get("primary_asset_id")],
            *[c["reference_asset_id"] for c in char_assets if c.get("reference_asset_id")],
            *([current.background_asset_id] if current and current.background_asset_id else []),
            *([current.reference_asset_id] if current and current.reference_asset_id else []),
            *[str(g.output_asset_id) for g in gens if g.output_asset_id],
        ],
        "available_tools": [t.name for t in TOOLS],
        "focus": focus,
        "active_camera": client.get("active_camera") or (cameras[0]["id"] if cameras else ""),
        "shot_duration": data.get("shotDuration") or client.get("shot_duration") or client.get("gen_duration") or 4,
        "shot_description": data.get("shotDescription") or client.get("shot_description") or "",
        "user_message": str(client.get("user_message") or ""),
        "image_url": client.get("image_url") or data.get("imageUrl"),
        "composition_url": client.get("composition_url") or data.get("compositionUrl"),
        "backdrop_url": client.get("backdrop_url") or (env.get("backdropUrl") if isinstance(env, dict) else None),
        "attachment_urls": [u for u in (client.get("attachment_urls") or []) if isinstance(u, str) and u.strip()],
        "aspect_ratio": client.get("aspect_ratio") or data.get("aspectRatio") or "9:16",
        "gen_duration": client.get("gen_duration") or data.get("shotDuration") or 5,
        "video_url": client.get("video_url") or data.get("videoUrl"),
    }
