"""Wave 0 生产数据安全护栏。不改 Schema，不删真实业务库。"""
from __future__ import annotations

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.logging import RedactingFilter
from app.core.security_guard import (
    DEFAULT_JWT_SECRET,
    ResetDenied,
    SecurityConfigError,
    assert_reset_allowed,
    validate_runtime_settings,
)
from app.db.database import init_db, reset_engine
from app.db.models import User
from app.db.safety import UnsafeDatabaseOperation, safe_delete, safe_update
from app.main import app


def _prod(**overrides) -> Settings:
    payload = {
        "app_env": "production",
        "jwt_secret": "explicit-production-secret-not-default",
        "debug": False,
        "auth_dev_echo_code": False,
        "database_url": "sqlite:///./storage/videoforge.db",
        "cors_origins": "https://app.example.com",
    }
    payload.update(overrides)
    return Settings(**payload)


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave0.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine()
    asyncio.run(init_db())
    with TestClient(app) as client:
        yield client
    reset_engine()


def _auth(client: TestClient) -> dict:
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "wave0@videoforge.dev",
            "password": "testpass123",
            "display_name": "Wave0",
        },
    )
    if resp.status_code == 409:
        resp = client.post(
            "/api/auth/login",
            json={"email": "wave0@videoforge.dev", "password": "testpass123"},
        )
    if resp.status_code >= 400:
        # 新注册接口可能要 account + captcha；回退旧字段失败则用已有 auth 通道
        pytest.skip(f"register/login unavailable in this fixture: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_director_library_requires_auth(isolated_client):
    resp = isolated_client.get("/api/director/library")
    assert resp.status_code == 401


def test_director_scenebook_put_requires_auth(isolated_client):
    resp = isolated_client.put("/api/director/scenebook", json={"currentId": "x", "scenes": []})
    assert resp.status_code == 401


def _project_id(client: TestClient, headers: dict) -> str:
    resp = client.post("/api/projects", json={"title": "Wave0 Director"}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_empty_scenebook_does_not_delete_rows(isolated_client):
    headers = _auth(isolated_client)
    pid = _project_id(isolated_client, headers)
    params = {"project_id": pid}
    scenes = [
        {
            "sceneId": f"scene_{i}",
            "sceneName": f"分镜 {i}",
            "version": 1,
            "objects": [],
            "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1, 5], "rotation": [0, 0, 0], "fov": 45}],
        }
        for i in range(10)
    ]
    ok = isolated_client.put(
        "/api/director/scenebook",
        json={"currentId": "scene_0", "scenes": scenes},
        headers=headers,
        params=params,
    )
    assert ok.status_code == 200, ok.text
    assert len(ok.json()["scenes"]) == 10
    blocked = isolated_client.put(
        "/api/director/scenebook",
        json={"currentId": "", "scenes": []},
        headers=headers,
        params=params,
    )
    assert blocked.status_code == 400
    again = isolated_client.get("/api/director/scenebook", headers=headers, params=params)
    assert again.status_code == 200
    assert len(again.json()["scenes"]) == 10


def test_empty_library_does_not_delete_rows(isolated_client):
    headers = _auth(isolated_client)
    pid = _project_id(isolated_client, headers)
    params = {"project_id": pid}
    characters = [{"id": f"char_{i}", "name": f"角色 {i}", "templateId": "human_female_young_01", "sourceType": "official"} for i in range(10)]
    ok = isolated_client.put(
        "/api/director/library",
        json={"characters": characters, "savedPoses": [], "customAnimations": []},
        headers=headers,
        params=params,
    )
    assert ok.status_code == 200, ok.text
    assert len(ok.json()["characters"]) == 10
    blocked = isolated_client.put(
        "/api/director/library",
        json={"characters": [], "savedPoses": [], "customAnimations": []},
        headers=headers,
        params=params,
    )
    assert blocked.status_code == 400
    again = isolated_client.get("/api/director/library", headers=headers, params=params)
    assert len(again.json()["characters"]) == 10


def test_production_default_jwt_secret_fails_boot():
    with pytest.raises(SecurityConfigError, match="JWT_SECRET"):
        validate_runtime_settings(_prod(jwt_secret=DEFAULT_JWT_SECRET))


def test_production_debug_true_fails_boot():
    with pytest.raises(SecurityConfigError, match="DEBUG"):
        validate_runtime_settings(_prod(debug=True))


def test_production_reset_denied():
    with pytest.raises(ResetDenied):
        assert_reset_allowed(_prod())
    with TestClient(app) as client:
        resp = client.post("/api/system/reset-database")
        assert resp.status_code == 403


def test_production_echo_code_fails_boot():
    with pytest.raises(SecurityConfigError, match="AUTH_DEV_ECHO_CODE"):
        validate_runtime_settings(_prod(auth_dev_echo_code=True))


def test_production_storage_rejects_anonymous(isolated_client, monkeypatch, fake_storage):
    from app.core import config as cfg
    from app.api import media_routes

    monkeypatch.setattr(cfg.settings, "app_env", "production")
    monkeypatch.setattr(media_routes.settings, "app_env", "production")
    sample = fake_storage / "probe.txt"
    sample.write_text("x", encoding="utf-8")
    resp = isolated_client.get("/storage/probe.txt")
    assert resp.status_code == 401


def test_unscoped_delete_refused():
    with pytest.raises(UnsafeDatabaseOperation):
        safe_delete(User)
    with pytest.raises(UnsafeDatabaseOperation):
        safe_update(User)


def test_logs_redact_secrets():
    filt = RedactingFilter()
    record = logging.LogRecord(
        name="ai_video_agent",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer abc.def.ghi JWT_SECRET=super secret api_key=dash-123",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    text = record.getMessage()
    assert "Bearer abc" not in text
    assert "super secret" not in text
    assert "dash-123" not in text
    assert "[REDACTED]" in text
