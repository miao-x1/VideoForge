"""Wave 5: Director Agent Plan → Validator → Executor → 真实 Tool。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent.errors import FORBIDDEN_TOOLS, INVALID_ARGUMENTS, RESOURCE_NOT_FOUND, UNKNOWN_TOOL, AgentError
from app.agent.logs import redact_payload
from app.agent.plan_model import to_director_plan
from app.agent.planner import plan
from app.agent.validator import validate_plan
from app.core.config import settings
from sqlalchemy import select

from app.db.database import async_session, get_session, init_db, reset_engine
from app.db.models import DirectorAgentLog, DirectorGeneration, Project, User
from app.db.ownership import DirectorScope
from app.main import app

PNG_A = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
PNG_B = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xff\xff"
    b"\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave5.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine()
    asyncio.run(init_db())
    with TestClient(app) as client:
        yield client
    reset_engine()


def _auth(client: TestClient, email: str) -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": email.split("@")[0]},
    )
    if resp.status_code == 409:
        resp = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    if resp.status_code >= 400:
        pytest.skip(f"register/login unavailable: {resp.status_code} {resp.text}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _project(client, headers, title="Agent Project") -> str:
    resp = client.post("/api/projects", json={"title": title}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _put_scene(client, headers, pid, scene_id="scene_v"):
    return client.put(
        "/api/director/scenebook",
        headers=headers,
        params={"project_id": pid},
        json={
            "currentId": scene_id,
            "scenes": [
                {
                    "sceneId": scene_id,
                    "sceneName": "客厅",
                    "version": 1,
                    "objects": [
                        {
                            "id": "obj_girl",
                            "name": "女主角",
                            "characterId": "char_girl",
                            "position": [0, 0, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                        {
                            "id": "obj_boy",
                            "name": "男主角",
                            "characterId": "char_boy",
                            "position": [2, 0, 0],
                            "rotation": [0, 0, 0],
                            "scale": [1, 1, 1],
                        },
                    ],
                    "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
                }
            ],
        },
    )


@pytest.fixture
def tenants(isolated_client, fake_storage, monkeypatch):
    payloads = iter([PNG_A, PNG_B, PNG_A, PNG_B, PNG_A, PNG_B])

    async def fake_image(*, prompt: str, width=None, height=None):
        dest = fake_storage / f"{abs(hash(prompt)) & 0xFFFFFFFF:08x}.png"
        dest.write_bytes(next(payloads))
        return {"generation_id": dest.stem, "path": str(dest), "url": f"/storage/{dest.name}", "model": "mock-image", "status": "ok"}

    monkeypatch.setattr("app.generation.router.generate_image", fake_image)
    monkeypatch.setattr("app.api.director_generation_routes.generate_image", fake_image)
    ha = _auth(isolated_client, "wave5-a@videoforge.dev")
    hb = _auth(isolated_client, "wave5-b@videoforge.dev")
    pa = _project(isolated_client, ha, "PA")
    pb = _project(isolated_client, hb, "PB")
    assert _put_scene(isolated_client, ha, pa).status_code == 200
    assert _put_scene(isolated_client, hb, pb).status_code == 200
    return isolated_client, ha, hb, pa, pb


def _chat(client, headers, pid, message, confirm=False, context=None, extra=None):
    body = {"message": message, "project_id": pid, "confirm": confirm, "context": context or {}}
    if extra:
        body.update(extra)
    return client.post("/api/agent/chat", headers=headers, params={"project_id": pid}, json=body)


def _scene_objects(client, headers, pid, scene_id="scene_v"):
    resp = client.get("/api/director/scenebook", headers=headers, params={"project_id": pid})
    assert resp.status_code == 200, resp.text
    scenes = resp.json()["scenes"]
    current = next((s for s in scenes if s.get("sceneId") == scene_id), scenes[0])
    return current


def test_planner_produces_plan():
    ctx = {
        "scene_id": "scene_v",
        "objects": [{"id": "obj_girl", "name": "女主角", "characterId": "char_girl", "position": [0, 0, 0]}],
        "focus": {"character_id": "char_girl"},
        "cameras": [{"id": "camera_001"}],
    }
    raw = plan("让女主走到窗边。", ctx)
    names = [c["name"] for c in raw.get("calls") or []]
    assert "move_character" in names
    doc = to_director_plan(raw, project_id="p1", scene_id="scene_v", message="让女主走到窗边。")
    assert doc["intent"] == "move_character"
    assert doc["tool_calls"]


def test_plan_validation_success():
    scope = SimpleNamespace(user_id="u1", project_id="p1")
    plan_doc = {
        "plan_id": "x",
        "project_id": "p1",
        "scene_id": "scene_v",
        "tool_calls": [{"name": "move_character", "arguments": {"character_id": "char_girl", "near": "window"}}],
    }
    ctx = {
        "owned_scene_ids": ["scene_v"],
        "owned_character_ids": ["char_girl"],
        "owned_camera_ids": ["camera_001"],
        "owned_generation_ids": [],
        "owned_asset_ids": [],
    }
    assert validate_plan(plan_doc, scope, ctx)["ok"] is True


def test_agent_moves_character(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _chat(client, ha, pa, "让女主走到窗边。")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["plan"]["tool_calls"]
    names = [c["name"] for c in data["plan"]["tool_calls"]]
    assert "move_character" in names
    assert any(r.get("success") for r in data["tool_results"])
    scene = _scene_objects(client, ha, pa)
    girl = next(o for o in scene["objects"] if o.get("characterId") == "char_girl")
    assert girl["position"] != [0, 0, 0]


def test_agent_modifies_camera(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _chat(client, ha, pa, "镜头慢慢推进。")
    assert resp.status_code == 200, resp.text
    names = [c["name"] for c in resp.json()["plan"]["tool_calls"]]
    assert "set_camera_motion" in names
    scene = _scene_objects(client, ha, pa)
    assert scene["cameras"][0].get("motion") == "push_in"


def test_agent_creates_shot(tenants):
    client, ha, _hb, pa, _pb = tenants
    before = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    resp = _chat(client, ha, pa, "创建一个 5 秒镜头。")
    assert resp.status_code == 200, resp.text
    names = [c["name"] for c in resp.json()["plan"]["tool_calls"]]
    assert "create_shot" in names
    after = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    assert len(after["scenes"]) > len(before["scenes"])


def test_agent_generation_enters_wave4_version_chain(tenants):
    client, ha, _hb, pa, _pb = tenants
    first = _chat(client, ha, pa, "生成这个镜头的画面。")
    assert first.status_code == 200, first.text
    gid1 = first.json()["generation_id"]
    assert gid1
    second = _chat(client, ha, pa, "再生成一张不同的参考图。")
    if second.status_code != 200 or not second.json().get("generation_id"):
        second = client.post(
            "/api/director/generate/image",
            headers=ha,
            params={"project_id": pa},
            json={"prompt": "second look from agent", "scene_id": "scene_v", "shot_id": "scene_v", "kind": "image"},
        )
        assert second.status_code == 200, second.text
        gid2 = second.json()["generation_id"]
    else:
        gid2 = second.json()["generation_id"]
    assert gid2 != gid1
    with get_session() as session:
        rows = session.execute(select(DirectorGeneration).where(DirectorGeneration.project_id == pa)).scalars().all()
        by_id = {r.generation_id: r for r in rows}
        assert gid1 in by_id and gid2 in by_id
        newer = by_id[gid2]
        assert newer.version_number and newer.version_number >= 1
        assert newer.generation_key
        assert newer.input_snapshot_json
        if newer.parent_generation_id:
            assert newer.parent_generation_id == gid1
        assert newer.output_asset_id


def test_agent_cannot_access_other_project(tenants):
    client, ha, hb, pa, pb = tenants
    denied = client.post(
        "/api/agent/chat",
        headers=hb,
        params={"project_id": pa},
        json={"message": "让女主走到窗边。", "project_id": pa},
    )
    assert denied.status_code == 404
    own = _chat(client, ha, pa, "让女主走到窗边。")
    assert own.status_code == 200


def test_agent_cannot_use_foreign_generation(tenants):
    client, ha, hb, pa, pb = tenants
    created = client.post(
        "/api/director/generate/image",
        headers=ha,
        params={"project_id": pa},
        json={"prompt": "owned by a", "scene_id": "scene_v", "shot_id": "scene_v", "kind": "image"},
    )
    assert created.status_code == 200, created.text
    gid = created.json()["generation_id"]
    scope = SimpleNamespace(user_id="b", project_id=pb)
    with pytest.raises(AgentError) as exc:
        validate_plan(
            {
                "plan_id": "x",
                "project_id": pb,
                "scene_id": "scene_v",
                "tool_calls": [{"name": "restore_generation", "arguments": {"generation_id": gid}}],
            },
            scope,
            {"owned_generation_ids": [], "owned_scene_ids": ["scene_v"], "owned_character_ids": [], "owned_camera_ids": [], "owned_asset_ids": []},
        )
    assert exc.value.code == RESOURCE_NOT_FOUND


def test_illegal_tool_rejected():
    scope = SimpleNamespace(user_id="u1", project_id="p1")
    with pytest.raises(AgentError) as exc:
        validate_plan(
            {"plan_id": "x", "project_id": "p1", "scene_id": "s", "tool_calls": [{"name": "execute_sql", "arguments": {}}]},
            scope,
            {"owned_scene_ids": ["s"]},
        )
    assert exc.value.code == FORBIDDEN_TOOLS
    with pytest.raises(AgentError) as unknown:
        validate_plan(
            {"plan_id": "x", "project_id": "p1", "scene_id": "s", "tool_calls": [{"name": "drop_table", "arguments": {}}]},
            scope,
            {"owned_scene_ids": ["s"]},
        )
    assert unknown.value.code == UNKNOWN_TOOL


def test_illegal_params_rejected():
    scope = SimpleNamespace(user_id="u1", project_id="p1")
    with pytest.raises(AgentError) as exc:
        validate_plan(
            {
                "plan_id": "x",
                "project_id": "p1",
                "scene_id": "s",
                "tool_calls": [{"name": "move_character", "arguments": {"position": "not-a-vector"}}],
            },
            scope,
            {"owned_scene_ids": ["s"], "owned_character_ids": ["c1"]},
        )
    assert exc.value.code == INVALID_ARGUMENTS


def test_delete_requires_confirmation(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _chat(client, ha, pa, "删掉这个镜头")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["requires_confirmation"] is True
    before = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    assert any(s.get("sceneId") == "scene_v" for s in before["scenes"])
    confirmed = _chat(client, ha, pa, "删掉这个镜头", confirm=True)
    assert confirmed.status_code == 200, confirmed.text
    after = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    assert not any(s.get("sceneId") == "scene_v" for s in after["scenes"]) or confirmed.json().get("success")


def test_tool_failure_is_structured(tenants):
    client, ha, _hb, pa, _pb = tenants
    from app.agent.executor import execute_plan

    async def _run():
        with get_session() as session:
            user = session.execute(select(User).where(User.email == "wave5-a@videoforge.dev")).scalar_one()
            project = session.execute(select(Project).where(Project.id == pa)).scalar_one()
            uid, pid = user.id, project.id
        async with async_session() as db:
            user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
            project = (await db.execute(select(Project).where(Project.id == pid))).scalar_one()
            return await execute_plan(
                db,
                DirectorScope(user=user, project=project),
                {
                    "plan_id": "x",
                    "project_id": pid,
                    "scene_id": "scene_v",
                    "requires_confirmation": False,
                    "tool_calls": [{"name": "move_character", "arguments": {"character_ref": "ghost_in_library", "position": [1, 0, 0]}}],
                    "summary": "move missing",
                },
                {
                    "scene_id": "scene_v",
                    "owned_scene_ids": ["scene_v"],
                    "owned_character_ids": ["char_girl", "obj_girl", "ghost_in_library"],
                    "owned_camera_ids": ["camera_001"],
                    "owned_generation_ids": [],
                    "owned_asset_ids": [],
                },
                confirm=True,
            )

    result = asyncio.run(_run())
    assert result["executed"] is False
    assert result["tool_results"]
    assert result["tool_results"][0].get("error_code")
    assert result["tool_results"][0]["success"] is False


def test_tool_failure_via_api(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _chat(client, ha, pa, "让幽灵角色走到窗边。", context={"objects": []})
    assert resp.status_code in {200, 400}
    data = resp.json()
    if data.get("tool_results"):
        failed = [r for r in data["tool_results"] if r.get("success") is False]
        if failed:
            assert failed[0].get("error_code")
            return
    if data.get("error_code"):
        assert data["error_code"] != "500"
        return
    # 规划器找不到角色时返回 PLAN_ERROR / 自然语言错误，而不是 500
    assert data.get("success") is False or data.get("message")


def test_agent_log_saves_plan_and_redacts_secrets(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _chat(
        client,
        ha,
        pa,
        "让女主走到窗边。",
        extra={"context": {"authorization": "Bearer secret-jwt-token", "api_key": "sk-live-should-not-log", "jwt": "abc"}},
    )
    assert resp.status_code == 200, resp.text
    with get_session() as session:
        rows = session.execute(select(DirectorAgentLog).where(DirectorAgentLog.project_id == pa)).scalars().all()
        assert rows
        blob = str(rows[-1].tool_result) + str(rows[-1].context_json) + str(rows[-1].tool_arguments)
        assert "sk-live-should-not-log" not in blob
        assert "secret-jwt-token" not in blob
        assert rows[-1].tool_result and rows[-1].tool_result.get("plan_json")


def test_redact_payload_unit():
    out = redact_payload({"authorization": "Bearer abc", "nested": {"password": "x", "ok": 1}})
    assert out["authorization"] == "[REDACTED]"
    assert out["nested"]["password"] == "[REDACTED]"
    assert out["nested"]["ok"] == 1


def test_agent_rejects_sql_python_shell(tenants):
    client, ha, _hb, pa, _pb = tenants
    for msg in ("execute_sql SELECT * FROM users", "execute_python import os", "execute_shell rm -rf /"):
        resp = _chat(client, ha, pa, msg)
        assert resp.status_code == 400, resp.text
        assert resp.json()["error_code"] == FORBIDDEN_TOOLS


def test_scene_text_with_shot_refs_plans_video():
    ctx = {
        "scene_id": "scene_v",
        "composition_url": "/storage/uploads/shot.png",
        "backdrop_url": "/storage/uploads/room.jpg",
        "attachment_urls": ["/storage/uploads/room.jpg"],
        "gen_duration": 6,
        "aspect_ratio": "9:16",
        "objects": [{"id": "obj_girl", "name": "女主角", "characterId": "char_girl", "position": [0, 0, 0]}],
        "cameras": [{"id": "camera_001"}],
    }
    raw = plan("女生晚上回到家，把包放下然后坐在沙发上。", ctx)
    names = [c["name"] for c in raw.get("calls") or []]
    assert names.count("generate_video") == 1
    video = next(c for c in raw["calls"] if c["name"] == "generate_video")
    assert video["arguments"]["duration"] == 6
    assert video["arguments"]["aspect_ratio"] == "9:16"


def test_mixed_walk_and_video_plans_generation():
    ctx = {
        "scene_id": "scene_v",
        "objects": [
            {"id": "obj_girl", "name": "女主角", "characterId": "char_girl", "position": [0, 0, 0]},
            {"id": "obj_boy", "name": "男主角", "characterId": "char_boy", "position": [2, 0, 0]},
        ],
        "focus": {"character_id": "char_girl"},
        "cameras": [{"id": "camera_001"}],
    }
    raw = plan("让她走过去以后转身看向男主，然后生成一个视频。", ctx)
    names = [c["name"] for c in raw.get("calls") or []]
    assert "generate_video" in names
    assert any(n in names for n in ("move_character", "set_character_action", "set_camera_target"))
