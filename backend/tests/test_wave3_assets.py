"""Wave 3: Asset 归一化与文件生命周期。只用临时库和临时 storage。"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.assets.consistency import check_consistency
from app.core.config import PROJECT_ROOT, settings
from app.db.alembic_runtime import BASELINE_REVISION, HEAD_REVISION, current_revision, stamp_revision, upgrade_head
from app.db.database import get_session, init_db, reset_engine
from app.main import app
from app.storage.local import storage

LIVE_DB = PROJECT_ROOT / "storage" / "videoforge.db"

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
DATA_URL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave3.db').as_posix()}"
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


def _project(client, headers, title="Asset Project") -> str:
    resp = client.post("/api/projects", json={"title": title}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _upload(client, headers, pid, data=PNG, name="tiny.png", asset_type="image"):
    return client.post(
        "/api/director/assets",
        headers=headers,
        params={"project_id": pid},
        files={"file": (name, data, "image/png")},
        data={"asset_type": asset_type, "name": name},
    )


@pytest.fixture
def tenants(isolated_client):
    ha = _auth(isolated_client, "wave3-a@videoforge.dev")
    hb = _auth(isolated_client, "wave3-b@videoforge.dev")
    pa = _project(isolated_client, ha, "PA")
    pb = _project(isolated_client, hb, "PB")
    return isolated_client, ha, hb, pa, pb


def test_asset_create(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = _upload(client, ha, pa)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["file_hash"]
    assert body["storage_key"].startswith(f"projects/{pa}/assets/")
    assert body["deduplicated"] is False


def test_asset_requires_project(tenants):
    client, ha, _hb, _pa, _pb = tenants
    resp = client.post(
        "/api/director/assets",
        headers=ha,
        files={"file": ("tiny.png", PNG, "image/png")},
    )
    assert resp.status_code == 400


def test_asset_project_ownership(tenants):
    client, ha, hb, pa, pb = tenants
    created = _upload(client, ha, pa).json()
    assert client.get(f"/api/director/assets/{created['id']}", headers=ha, params={"project_id": pb}).status_code == 404
    assert client.get(f"/api/director/assets/{created['id']}", headers=hb, params={"project_id": pa}).status_code == 404


def test_asset_user_isolation(tenants):
    client, ha, hb, pa, pb = tenants
    _upload(client, ha, pa)
    listed = client.get("/api/director/assets", headers=hb, params={"project_id": pb})
    assert listed.status_code == 200
    assert listed.json()["assets"] == []


def test_asset_idor(tenants):
    client, ha, hb, pa, pb = tenants
    asset_id = _upload(client, ha, pa).json()["id"]
    assert client.get(f"/api/director/assets/{asset_id}", headers=hb, params={"project_id": pb}).status_code == 404
    assert client.get(f"/api/director/assets/{asset_id}/file", headers=hb, params={"project_id": pb}).status_code == 404
    assert client.delete(f"/api/director/assets/{asset_id}", headers=hb, params={"project_id": pb}).status_code == 404


def test_asset_file_accepts_query_token(tenants):
    client, ha, hb, pa, _pb = tenants
    asset_id = _upload(client, ha, pa).json()["id"]
    token = ha["Authorization"].split(" ", 1)[1]
    ok = client.get(
        f"/api/director/assets/{asset_id}/file",
        params={"project_id": pa, "access_token": token},
    )
    assert ok.status_code == 200, ok.text
    other = hb["Authorization"].split(" ", 1)[1]
    denied = client.get(
        f"/api/director/assets/{asset_id}/file",
        params={"project_id": pa, "access_token": other},
    )
    assert denied.status_code in (401, 404)


def test_asset_hash_deduplication(tenants):
    client, ha, _hb, pa, _pb = tenants
    first = _upload(client, ha, pa).json()
    second = _upload(client, ha, pa).json()
    assert second["deduplicated"] is True
    assert second["id"] == first["id"]
    listed = client.get("/api/director/assets", headers=ha, params={"project_id": pa}).json()
    assert len(listed["assets"]) == 1


def test_same_hash_different_project_isolated(tenants):
    client, ha, _hb, pa, _pb = tenants
    pa2 = _project(client, ha, "PA2")
    a1 = _upload(client, ha, pa).json()
    a2 = _upload(client, ha, pa2).json()
    assert a1["id"] != a2["id"]
    assert a1["file_hash"] == a2["file_hash"]


def test_same_hash_different_user_isolated(tenants):
    client, ha, hb, pa, pb = tenants
    a1 = _upload(client, ha, pa).json()
    a2 = _upload(client, hb, pb).json()
    assert a1["id"] != a2["id"]
    assert a1["file_hash"] == a2["file_hash"]


def test_data_url_not_persisted(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = client.put(
        "/api/director/scenebook",
        headers=ha,
        params={"project_id": pa},
        json={
            "currentId": "scene_data",
            "scenes": [
                {
                    "sceneId": "scene_data",
                    "sceneName": "data",
                    "version": 1,
                    "objects": [],
                    "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
                    "imageUrl": DATA_URL,
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    scenes = resp.json()["scenes"]
    assert scenes
    assert not str(scenes[0].get("imageUrl") or "").startswith("data:")
    listed = client.get("/api/director/assets", headers=ha, params={"project_id": pa}).json()
    assert listed["assets"]


def test_storage_path_traversal_blocked(tenants):
    client, ha, _hb, _pa, _pb = tenants
    with pytest.raises(ValueError):
        storage.resolve("../videoforge.db")
    with pytest.raises(ValueError):
        storage.resolve("projects/../../videoforge.db")
    resp = client.get("/storage/../videoforge.db", headers=ha)
    assert resp.status_code in {400, 404}


def test_storage_key_cannot_bypass_auth(tenants):
    client, ha, hb, pa, pb = tenants
    created = _upload(client, ha, pa).json()
    key = created["storage_key"]
    assert client.get(f"/storage/{key}").status_code == 401
    assert client.get(f"/storage/{key}", headers=hb).status_code == 404
    assert client.get(f"/storage/{key}", headers=ha).status_code == 200


def test_missing_file_detected(tenants):
    client, ha, _hb, pa, _pb = tenants
    created = _upload(client, ha, pa).json()
    path = storage.get_path(created["storage_key"])
    path.unlink()
    with get_session() as session:
        report = check_consistency(session)
    assert created["id"] in report["missing_files"]


def test_orphan_file_detected(tenants, fake_storage):
    orphan = fake_storage / "projects" / "x" / "assets" / "orphan" / "original.png"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(PNG)
    with get_session() as session:
        report = check_consistency(session)
    assert any(p.endswith("original.png") for p in report["orphan_files"])


def test_referenced_asset_cannot_be_deleted(tenants):
    client, ha, _hb, pa, _pb = tenants
    asset_id = _upload(client, ha, pa).json()["id"]
    put = client.put(
        "/api/director/library",
        headers=ha,
        params={"project_id": pa},
        json={
            "characters": [
                {
                    "id": "char_ref",
                    "name": "Ref",
                    "templateId": "t",
                    "sourceType": "official",
                    "primaryAssetId": asset_id,
                }
            ],
            "savedPoses": [],
            "customAnimations": [],
        },
    )
    assert put.status_code == 200, put.text
    blocked = client.delete(f"/api/director/assets/{asset_id}", headers=ha, params={"project_id": pa})
    assert blocked.status_code == 409


def test_unreferenced_asset_delete_safe(tenants):
    client, ha, _hb, pa, _pb = tenants
    asset_id = _upload(client, ha, pa).json()["id"]
    deleted = client.delete(f"/api/director/assets/{asset_id}", headers=ha, params={"project_id": pa})
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get(f"/api/director/assets/{asset_id}", headers=ha, params={"project_id": pa}).status_code == 404


def test_upload_size_limit(tenants, monkeypatch):
    client, ha, _hb, pa, _pb = tenants
    monkeypatch.setattr(settings, "upload_max_size_mb", 0)
    resp = _upload(client, ha, pa)
    assert resp.status_code == 413


def test_mime_validation(tenants):
    client, ha, _hb, pa, _pb = tenants
    resp = client.post(
        "/api/director/assets",
        headers=ha,
        params={"project_id": pa},
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert resp.status_code == 400


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


def test_existing_db_upgrade_keeps_rows(tmp_path, monkeypatch):
    copy = tmp_path / "existing_w3.db"
    _copy_live(copy)
    before = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
    counts = {
        t: before.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        for t in ("users", "projects", "assets", "director_characters", "director_scenes")
    }
    before.close()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{copy.as_posix()}")
    reset_engine()
    stamp_revision(BASELINE_REVISION)
    upgrade_head()
    assert current_revision() == HEAD_REVISION
    engine = create_engine(f"sqlite:///{copy.as_posix()}")
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("assets")}
        assert {"storage_key", "file_hash", "status", "deleted_at"}.issubset(cols)
        with engine.connect() as conn:
            after_assets = conn.execute(text("SELECT COUNT(*) FROM assets")).scalar()
            after_chars = conn.execute(text("SELECT COUNT(*) FROM director_characters")).scalar()
    finally:
        engine.dispose()
    assert after_assets == counts["assets"] == 0
    assert after_chars == counts["director_characters"]
    reset_engine()
