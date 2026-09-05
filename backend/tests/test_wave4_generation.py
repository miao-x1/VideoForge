"""Wave 4: Generation 版本链与幂等。只用临时库和临时 storage。"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.core.config import PROJECT_ROOT, settings
from app.db.alembic_runtime import BASELINE_REVISION, HEAD_REVISION, current_revision, stamp_revision, upgrade_head
from app.db.database import get_session, reset_engine, init_db
from app.db.models import DirectorGeneration
from app.main import app
from app.storage.local import storage

LIVE_DB = PROJECT_ROOT / "storage" / "videoforge.db"

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
PNG_C = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xaa\xaa"
    b"\x00\x00\x02\x00\x01k\xca~\x8d\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave4.db').as_posix()}"
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


def _project(client, headers, title="Gen Project") -> str:
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
                    "sceneName": "V",
                    "version": 1,
                    "objects": [],
                    "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
                }
            ],
        },
    )


@pytest.fixture
def tenants(isolated_client, fake_storage, monkeypatch):
    payloads = iter([PNG_A, PNG_B, PNG_C, PNG_A, PNG_B, PNG_C, PNG_A, PNG_B])

    async def fake_image(*, prompt: str, width=None, height=None):
        dest = fake_storage / f"{abs(hash(prompt)) & 0xFFFFFFFF:08x}.png"
        dest.write_bytes(next(payloads))
        return {"generation_id": dest.stem, "path": str(dest), "url": f"/storage/{dest.name}", "model": "mock-image", "status": "ok"}

    monkeypatch.setattr("app.api.director_generation_routes.generate_image", fake_image)
    ha = _auth(isolated_client, "wave4-a@videoforge.dev")
    hb = _auth(isolated_client, "wave4-b@videoforge.dev")
    pa = _project(isolated_client, ha, "PA")
    pb = _project(isolated_client, hb, "PB")
    assert _put_scene(isolated_client, ha, pa).status_code == 200
    return isolated_client, ha, hb, pa, pb


def _gen(client, headers, pid, prompt, scene_id="scene_v", parent=None):
    body = {"prompt": prompt, "scene_id": scene_id, "shot_id": scene_id, "kind": "image"}
    if parent:
        body["parent_generation_id"] = parent
    return client.post(
        "/api/director/generate/image",
        headers=headers,
        params={"project_id": pid},
        json=body,
    )


def test_generation_v1_succeeds(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _gen(client, ha, pa, "first look")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["version"] == 1
    assert body["parent_generation_id"] is None
    assert body["output_asset_id"]
    assert body["idempotent"] is False


def test_generation_v2_has_parent(tenants):
    client, ha, _hb, pa, _pb = tenants
    v1 = _gen(client, ha, pa, "first look").json()
    v2 = _gen(client, ha, pa, "second look", parent=v1["generation_id"]).json()
    assert v2["status"] == "completed"
    assert v2["version"] == 2
    assert v2["parent_generation_id"] == v1["generation_id"]
    assert v2["generation_id"] != v1["generation_id"]


def test_versions_do_not_overwrite_files(tenants):
    client, ha, _hb, pa, _pb = tenants
    v1 = _gen(client, ha, pa, "first look").json()
    v2 = _gen(client, ha, pa, "second look", parent=v1["generation_id"]).json()
    v3 = _gen(client, ha, pa, "third look", parent=v2["generation_id"]).json()
    assert len({v1["output_asset_id"], v2["output_asset_id"], v3["output_asset_id"]}) == 3
    from sqlalchemy import select
    with get_session() as session:
        rows = list(session.scalars(select(DirectorGeneration)))
        keys = []
        for row in rows:
            assert row.output_asset_id
            assert row.result_path
            assert storage.exists(row.result_path)
            keys.append(row.result_path)
        assert len(set(keys)) == 3


def test_double_click_is_idempotent(tenants):
    client, ha, _hb, pa, _pb = tenants
    first = _gen(client, ha, pa, "same prompt")
    second = _gen(client, ha, pa, "same prompt")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    assert first.json()["generation_id"] == second.json()["generation_id"]
    hist = client.get("/api/director/generate/history", headers=ha, params={"project_id": pa, "scene_id": "scene_v"})
    assert len(hist.json()["items"]) == 1


def test_different_prompt_creates_new_version(tenants):
    client, ha, _hb, pa, _pb = tenants
    a = _gen(client, ha, pa, "prompt a").json()
    b = _gen(client, ha, pa, "prompt b", parent=a["generation_id"]).json()
    assert a["generation_id"] != b["generation_id"]
    assert b["version"] == 2


def test_restore_history_version(tenants):
    client, ha, _hb, pa, _pb = tenants
    v1 = _gen(client, ha, pa, "first look").json()
    v2 = _gen(client, ha, pa, "second look", parent=v1["generation_id"]).json()
    restored = client.post(
        f"/api/director/generate/{v1['generation_id']}/restore",
        headers=ha,
        params={"project_id": pa},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["generation_id"] == v1["generation_id"]
    book = client.get("/api/director/scenebook", headers=ha, params={"project_id": pa}).json()
    scene = book["scenes"][0]
    assert scene["generationId"] == v1["generation_id"]
    assert scene["generationId"] != v2["generation_id"]
    detail = client.get(f"/api/director/generate/{v1['generation_id']}", headers=ha, params={"project_id": pa})
    assert detail.status_code == 200
    assert detail.json()["input_snapshot"]["prompt"] == "first look"


def test_user_works_list_rename_and_delete(tenants):
    client, ha, hb, pa, pb = tenants
    mine = _gen(client, ha, pa, "my completed look").json()
    other = _gen(client, hb, pb, "other look").json()
    listed = client.get("/api/director/generate/works", headers=ha)
    assert listed.status_code == 200, listed.text
    ids = {item["generation_id"] for item in listed.json()["items"]}
    assert mine["generation_id"] in ids
    assert other["generation_id"] not in ids
    assert listed.json()["items"][0]["title"]

    renamed = client.patch(
        f"/api/director/generate/{mine['generation_id']}",
        headers=ha,
        json={"title": "夜戏成片"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "夜戏成片"

    stolen = client.patch(
        f"/api/director/generate/{mine['generation_id']}",
        headers=hb,
        json={"title": "偷改"},
    )
    assert stolen.status_code == 404

    deleted = client.delete(f"/api/director/generate/{mine['generation_id']}", headers=ha)
    assert deleted.status_code == 200, deleted.text
    after = client.get("/api/director/generate/works", headers=ha).json()["items"]
    assert mine["generation_id"] not in {item["generation_id"] for item in after}
    assert client.delete(f"/api/director/generate/{mine['generation_id']}", headers=hb).status_code == 404


def test_user_cannot_access_other_versions(tenants):
    client, ha, hb, pa, pb = tenants
    created = _gen(client, ha, pa, "secret look").json()
    gid = created["generation_id"]
    assert client.get(f"/api/director/generate/{gid}", headers=hb, params={"project_id": pb}).status_code == 404
    assert client.post(f"/api/director/generate/{gid}/restore", headers=hb, params={"project_id": pb}).status_code == 404
    assert client.get("/api/director/generate/history", headers=hb, params={"project_id": pb}).json()["items"] == []
    assert client.get("/api/director/generate/history", headers=hb, params={"project_id": pa}).status_code == 404


def test_referenced_generation_asset_cannot_be_deleted(tenants):
    client, ha, _hb, pa, _pb = tenants
    created = _gen(client, ha, pa, "keep me").json()
    asset_id = created["output_asset_id"]
    blocked = client.delete(f"/api/director/assets/{asset_id}", headers=ha, params={"project_id": pa})
    assert blocked.status_code == 409


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


def test_existing_db_upgrade_keeps_generation_rows(tmp_path, monkeypatch):
    copy = tmp_path / "existing_w4.db"
    _copy_live(copy)
    before = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
    counts = {
        t: before.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        for t in ("users", "director_characters", "director_scenes", "director_generations")
    }
    before.close()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{copy.as_posix()}")
    reset_engine()
    stamp_revision(BASELINE_REVISION)
    upgrade_head()
    assert current_revision() == HEAD_REVISION
    engine = create_engine(f"sqlite:///{copy.as_posix()}")
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("director_generations")}
        scene_cols = {c["name"] for c in inspect(engine).get_columns("director_scenes")}
        assert {"parent_generation_id", "version_number", "generation_key", "input_snapshot_json", "title"}.issubset(cols)
        assert "current_generation_id" in scene_cols
        with engine.connect() as conn:
            after = conn.execute(text("SELECT COUNT(*) FROM director_generations")).scalar()
            after_chars = conn.execute(text("SELECT COUNT(*) FROM director_characters")).scalar()
    finally:
        engine.dispose()
    assert after == counts["director_generations"]
    assert after_chars == counts["director_characters"]
    reset_engine()


def test_local_path_from_url_strips_access_token(tmp_path, monkeypatch):
    import app.generation.router as router

    monkeypatch.setattr(router, "STORAGE_ROOT", tmp_path)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    shot = uploads / "17b4ad07a7f6.png"
    shot.write_bytes(PNG_A)
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc"
    dirty = f"/storage/uploads/{shot.name}?access_token={token}"
    assert router.local_path_from_url(dirty) == str(shot)
    glued = f"{shot}access_token={token}"
    assert router.local_path_from_url(glued) == str(shot)
    assert router.local_path_from_url(f"{shot}?access_token={token}") == str(shot)
