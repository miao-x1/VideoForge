"""Wave 2: Director User + Project 隔离与 IDOR。只使用临时库。"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from app.core.config import PROJECT_ROOT, settings
from app.db.alembic_runtime import (
    BASELINE_REVISION,
    HEAD_REVISION,
    current_revision,
    stamp_revision,
    upgrade_head,
)
from app.db.database import get_session, init_db, reset_engine
from app.db.models import DirectorAgentLog, DirectorCharacter, DirectorGeneration, DirectorScene, User
from app.main import app

LIVE_DB = PROJECT_ROOT / "storage" / "videoforge.db"

COUNT_TABLES = (
    "users",
    "projects",
    "director_characters",
    "director_scenes",
    "director_agent_logs",
    "director_character_tasks",
)


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave2.db').as_posix()}"
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


def _project(client: TestClient, headers: dict, title: str) -> str:
    resp = client.post("/api/projects", json={"title": title}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _put_char(client, headers, pid, cid, name="角色"):
    return client.put(
        "/api/director/library",
        params={"project_id": pid},
        headers=headers,
        json={
            "characters": [{"id": cid, "name": name, "templateId": "t", "sourceType": "official"}],
            "savedPoses": [],
            "customAnimations": [],
        },
    )


def _put_scene(client, headers, pid, sid, name="分镜"):
    return client.put(
        "/api/director/scenebook",
        params={"project_id": pid},
        headers=headers,
        json={
            "currentId": sid,
            "scenes": [
                {
                    "sceneId": sid,
                    "sceneName": name,
                    "version": 1,
                    "objects": [],
                    "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
                }
            ],
        },
    )


@pytest.fixture
def tenants(isolated_client):
    headers_a = _auth(isolated_client, "wave2-a@videoforge.dev")
    headers_b = _auth(isolated_client, "wave2-b@videoforge.dev")
    project_a = _project(isolated_client, headers_a, "Project A")
    project_b = _project(isolated_client, headers_b, "Project B")
    return isolated_client, headers_a, headers_b, project_a, project_b


def test_user_cannot_read_other_users_character(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_char(client, ha, pa, "char_a", "AliceChar").status_code == 200
    mine = client.get("/api/director/library", headers=ha, params={"project_id": pa})
    other = client.get("/api/director/library", headers=hb, params={"project_id": pb})
    assert [c["id"] for c in mine.json()["characters"]] == ["char_a"]
    assert other.json()["characters"] == []


def test_user_cannot_update_other_users_character(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_char(client, ha, pa, "char_a", "Original").status_code == 200
    sneaky = _put_char(client, hb, pb, "char_a", "Hijacked")
    assert sneaky.status_code == 200
    a_lib = client.get("/api/director/library", headers=ha, params={"project_id": pa}).json()
    b_lib = client.get("/api/director/library", headers=hb, params={"project_id": pb}).json()
    assert a_lib["characters"][0]["name"] == "Original"
    assert b_lib["characters"] == []


def test_user_cannot_delete_other_users_character(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_char(client, ha, pa, "char_a").status_code == 200
    blocked = client.put(
        "/api/director/library",
        params={"project_id": pa},
        headers=hb,
        json={"characters": [{"id": "x", "name": "x", "templateId": "t", "sourceType": "official"}], "savedPoses": [], "customAnimations": []},
    )
    assert blocked.status_code == 404
    empty = client.put(
        "/api/director/library",
        params={"project_id": pb},
        headers=hb,
        json={"characters": [], "savedPoses": [], "customAnimations": []},
    )
    assert empty.status_code == 400
    again = client.get("/api/director/library", headers=ha, params={"project_id": pa})
    assert len(again.json()["characters"]) == 1


def test_user_cannot_read_other_users_scene(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_scene(client, ha, pa, "scene_a", "A1").status_code == 200
    mine = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa})
    other = client.get("/api/director/scenebook", headers=hb, params={"project_id": pb})
    assert [s["sceneId"] for s in mine.json()["scenes"]] == ["scene_a"]
    assert other.json()["scenes"] == []


def test_user_cannot_update_other_users_scene(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_scene(client, ha, pa, "scene_a", "Original").status_code == 200
    sneaky = _put_scene(client, hb, pb, "scene_a", "Hijacked")
    assert sneaky.status_code == 200
    a_book = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    assert a_book["scenes"][0]["sceneName"] == "Original"


def test_user_cannot_delete_other_users_scene(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_scene(client, ha, pa, "scene_a").status_code == 200
    blocked = client.put(
        "/api/director/scenebook",
        params={"project_id": pa},
        headers=hb,
        json={"currentId": "", "scenes": []},
    )
    assert blocked.status_code == 404
    again = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa})
    assert len(again.json()["scenes"]) == 1


def test_user_cannot_access_other_project(tenants):
    client, ha, hb, pa, pb = tenants
    assert client.get("/api/director/library", headers=ha, params={"project_id": pb}).status_code == 404
    assert client.get("/api/director/scenebook", headers=hb, params={"project_id": pa}).status_code == 404
    assert client.get("/api/director/generate/history", headers=ha, params={"project_id": pb}).status_code == 404


def test_project_must_belong_to_current_user(tenants):
    client, ha, _hb, pa, pb = tenants
    assert client.get("/api/director/library", headers=ha, params={"project_id": pb}).status_code == 404
    assert client.get("/api/director/library", headers=ha).status_code == 400
    assert client.get("/api/director/library", headers=ha, params={"project_id": pa}).status_code == 200


def test_create_character_uses_authenticated_user(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = client.put(
        "/api/director/library",
        params={"project_id": pa},
        headers=ha,
        json={
            "user_id": "forged-user",
            "project_id": "forged-project",
            "characters": [{"id": "char_owned", "name": "Mine", "templateId": "t", "sourceType": "official"}],
            "savedPoses": [],
            "customAnimations": [],
        },
    )
    assert resp.status_code == 200
    with get_session() as session:
        row = session.execute(select(DirectorCharacter).where(DirectorCharacter.id == "char_owned")).scalar_one()
        assert row.user_id != "forged-user"
        assert row.project_id == pa
        assert row.project_id != "forged-project"


def test_create_scene_uses_authenticated_user(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = client.put(
        "/api/director/scenebook",
        params={"project_id": pa},
        headers=ha,
        json={
            "user_id": "forged-user",
            "project_id": "forged-project",
            "currentId": "scene_owned",
            "scenes": [
                {
                    "sceneId": "scene_owned",
                    "sceneName": "Mine",
                    "version": 1,
                    "objects": [],
                    "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
                }
            ],
        },
    )
    assert resp.status_code == 200
    with get_session() as session:
        row = session.execute(select(DirectorScene).where(DirectorScene.scene_id == "scene_owned")).scalar_one()
        assert row.user_id != "forged-user"
        assert row.project_id == pa


def test_client_cannot_override_user_id(tenants):
    test_create_character_uses_authenticated_user(tenants)


def test_client_cannot_override_project_ownership(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_char(client, ha, pa, "char_a").status_code == 200
    forged = _put_char(client, hb, pa, "char_b", "Nope")
    assert forged.status_code == 404
    a_lib = client.get("/api/director/library", headers=ha, params={"project_id": pa}).json()
    assert [c["id"] for c in a_lib["characters"]] == ["char_a"]


def test_library_is_project_scoped(tenants):
    client, ha, _hb, pa, _pb = tenants
    pa2 = _project(client, ha, "Project A2")
    assert _put_char(client, ha, pa, "char_p1").status_code == 200
    a1 = client.get("/api/director/library", headers=ha, params={"project_id": pa}).json()
    a2 = client.get("/api/director/library", headers=ha, params={"project_id": pa2}).json()
    assert [c["id"] for c in a1["characters"]] == ["char_p1"]
    assert a2["characters"] == []


def test_generation_is_project_scoped(tenants):
    client, ha, hb, pa, pb = tenants
    with get_session() as session:
        user_a = session.execute(select(User).where(User.email == "wave2-a@videoforge.dev")).scalar_one()
        session.add(
            DirectorGeneration(
                generation_id="gen_a_only",
                user_id=user_a.id,
                project_id=pa,
                scene_id="scene_a",
                shot_id="scene_a",
                kind="image",
                prompt="scoped-only",
                status="error",
                error="provider not invoked in this test",
            )
        )
        session.commit()
    a_hist = client.get("/api/director/generate/history", headers=ha, params={"project_id": pa})
    b_hist = client.get("/api/director/generate/history", headers=hb, params={"project_id": pb})
    cross = client.get("/api/director/generate/history", headers=hb, params={"project_id": pa})
    assert a_hist.status_code == 200
    assert [i["generation_id"] for i in a_hist.json()["items"]] == ["gen_a_only"]
    assert b_hist.status_code == 200
    assert b_hist.json()["items"] == []
    assert cross.status_code == 404


def test_agent_only_reads_current_project(tenants):
    client, ha, hb, pa, pb = tenants
    assert _put_char(client, ha, pa, "char_a", "SecretA").status_code == 200
    log_a = client.post(
        "/api/agent/log",
        headers=ha,
        params={"project_id": pa},
        json={
            "conversation_id": "conv-a",
            "message_id": "msg-a",
            "agent_run_id": "run-a",
            "user_input": "hello",
            "tool_name": "plan",
            "context": {"user_id": "forged", "project_id": "forged"},
        },
    )
    assert log_a.status_code == 200
    chat_b = client.post(
        "/api/agent/chat",
        headers=hb,
        params={"project_id": pb},
        json={"message": "列出所有角色", "context": {"characters": [{"id": "char_a", "name": "SecretA"}]}},
    )
    assert chat_b.status_code == 200
    with get_session() as session:
        logs = session.execute(select(DirectorAgentLog)).scalars().all()
        assert logs
        for row in logs:
            if row.conversation_id.startswith("conv-a"):
                assert row.user_id != "forged"
                assert row.project_id == pa
            if row.user_input == "列出所有角色":
                assert row.project_id == pb
                assert row.context_json and row.context_json.get("project_id") == pb
                assert row.context_json.get("user_id") != "forged"


def test_character_task_is_project_scoped(tenants):
    client, ha, hb, pa, pb = tenants
    created = client.post(
        "/api/director/characters/tasks",
        headers=ha,
        params={"project_id": pa},
        data={"kind": "ai_generate", "prompt": "a hero"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    assert client.get(
        f"/api/director/characters/tasks/{task_id}",
        headers=ha,
        params={"project_id": pa},
    ).status_code == 200
    assert client.get(
        f"/api/director/characters/tasks/{task_id}",
        headers=hb,
        params={"project_id": pb},
    ).status_code == 404


def _row_counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {t: con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] for t in COUNT_TABLES}
    finally:
        con.close()


def _copy_live(dest: Path) -> None:
    if not LIVE_DB.exists():
        pytest.skip(f"live database missing: {LIVE_DB}")
    src = sqlite3.connect(f"file:{LIVE_DB.as_posix()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def test_existing_data_survives_ownership_upgrade(tmp_path, monkeypatch):
    copy = tmp_path / "existing_w2.db"
    _copy_live(copy)
    before = _row_counts(copy)
    live_before = _row_counts(LIVE_DB)
    url = f"sqlite:///{copy.as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine()
    stamp_revision(BASELINE_REVISION)
    upgrade_head()
    assert current_revision() == HEAD_REVISION
    after = _row_counts(copy)
    assert after == before
    engine = create_engine(url)
    try:
        insp = inspect(engine)
        for table in (
            "director_characters",
            "director_scenes",
            "director_library_meta",
            "director_agent_logs",
            "director_character_tasks",
        ):
            cols = {c["name"] for c in insp.get_columns(table)}
            assert {"user_id", "project_id"}.issubset(cols)
        with engine.connect() as conn:
            mapped = conn.execute(
                text("SELECT COUNT(*) FROM director_characters WHERE user_id IS NOT NULL")
            ).scalar()
            orphan = conn.execute(
                text("SELECT COUNT(*) FROM director_characters WHERE user_id IS NULL")
            ).scalar()
            scenes_orphan = conn.execute(
                text("SELECT COUNT(*) FROM director_scenes WHERE user_id IS NULL")
            ).scalar()
            logs_orphan = conn.execute(
                text("SELECT COUNT(*) FROM director_agent_logs WHERE user_id IS NULL")
            ).scalar()
            tasks_orphan = conn.execute(
                text("SELECT COUNT(*) FROM director_character_tasks WHERE user_id IS NULL")
            ).scalar()
            meta_orphan = conn.execute(
                text("SELECT COUNT(*) FROM director_library_meta WHERE user_id IS NULL")
            ).scalar()
    finally:
        engine.dispose()
    assert mapped == 0
    assert orphan == before["director_characters"]
    assert scenes_orphan == before["director_scenes"]
    assert logs_orphan == before["director_agent_logs"]
    assert tasks_orphan == before["director_character_tasks"]
    assert meta_orphan in (0, 1)
    assert _row_counts(LIVE_DB) == live_before
    reset_engine()
