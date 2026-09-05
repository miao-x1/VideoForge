"""Wave 6: 平台钱包 / 自带 Key。只用临时库，不改 storage/videoforge.db。"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import init_db, reset_engine
from app.main import app

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def isolated_client(fake_storage, monkeypatch):
    url = f"sqlite+aiosqlite:///{(fake_storage / 'wave6.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "minimax_api_key", "platform-minimax-key-xxxx")
    monkeypatch.setattr(settings, "video_model_provider", "minimax")
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


def _project(client, headers, title="Bill Project") -> str:
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


def _status(client, headers):
    return client.get("/api/billing/status", headers=headers)


def test_status_starts_empty_in_test_env(isolated_client):
    headers = _auth(isolated_client, "bill-a@videoforge.dev")
    resp = _status(isolated_client, headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["video_source"] == "platform"
    assert body["wallet"]["balance_fen"] == 0
    assert body["dev_recharge"] is True
    assert body["wallet_kind"] == "platform_ledger"
    assert body["recharge_kind"] == "dev_credit"
    assert "本站账本" in body["wallet_note"]
    assert "MINIMAX_API_KEY" in body["minimax_note"]
    assert "platform-minimax-key" not in str(body)


def test_platform_generate_blocked_without_balance(isolated_client, fake_storage, monkeypatch):
    async def boom(**kwargs):
        raise AssertionError("should not generate without wallet")

    monkeypatch.setattr("app.billing.access.generate_video", boom)
    headers = _auth(isolated_client, "bill-b@videoforge.dev")
    pid = _project(isolated_client, headers)
    assert _put_scene(isolated_client, headers, pid).status_code == 200
    resp = isolated_client.post(
        "/api/director/generate/video",
        headers=headers,
        params={"project_id": pid},
        json={"prompt": "a walk", "scene_id": "scene_v", "shot_id": "scene_v", "duration": 5},
    )
    assert resp.status_code == 402, resp.text
    assert "余额不足" in resp.json()["detail"]


def test_recharge_then_platform_debit(isolated_client, fake_storage, monkeypatch):
    captured: dict = {}

    async def fake_video(**kwargs):
        captured.update(kwargs)
        dest = fake_storage / "billed.mp4"
        dest.write_bytes(b"mp4")
        return {
            "generation_id": "gid_billed",
            "path": str(dest),
            "url": "/storage/billed.mp4",
            "model": "MiniMax-H3",
            "status": "ok",
        }

    monkeypatch.setattr("app.billing.access.generate_video", fake_video)
    headers = _auth(isolated_client, "bill-c@videoforge.dev")
    topup = isolated_client.post("/api/billing/recharge", headers=headers, json={"yuan": 10})
    assert topup.status_code == 200, topup.text
    assert topup.json()["wallet"]["balance_fen"] == 1000

    pid = _project(isolated_client, headers)
    assert _put_scene(isolated_client, headers, pid).status_code == 200
    resp = isolated_client.post(
        "/api/director/generate/video",
        headers=headers,
        params={"project_id": pid},
        json={"prompt": "a walk", "scene_id": "scene_v", "shot_id": "scene_v", "duration": 5},
    )
    assert resp.status_code == 200, resp.text
    after = _status(isolated_client, headers).json()
    assert after["wallet"]["balance_fen"] == 1000 - 5 * 80
    assert captured["api_key"] == "platform-minimax-key-xxxx"
    assert captured["provider_name"] == "minimax"


def test_failed_generate_refunds(isolated_client, fake_storage, monkeypatch):
    async def fail(**kwargs):
        raise RuntimeError("upstream down")

    monkeypatch.setattr("app.billing.access.generate_video", fail)
    headers = _auth(isolated_client, "bill-d@videoforge.dev")
    isolated_client.post("/api/billing/recharge", headers=headers, json={"yuan": 10})
    pid = _project(isolated_client, headers)
    assert _put_scene(isolated_client, headers, pid).status_code == 200
    resp = isolated_client.post(
        "/api/director/generate/video",
        headers=headers,
        params={"project_id": pid},
        json={"prompt": "a walk", "scene_id": "scene_v", "shot_id": "scene_v", "duration": 5},
    )
    assert resp.status_code == 502
    after = _status(isolated_client, headers).json()
    assert after["wallet"]["balance_fen"] == 1000


def test_byok_skips_wallet_and_hides_key(isolated_client, fake_storage, monkeypatch):
    captured: dict = {}

    async def fake_video(**kwargs):
        captured.update(kwargs)
        dest = fake_storage / "own.mp4"
        dest.write_bytes(b"mp4")
        return {
            "generation_id": "gid_own",
            "path": str(dest),
            "url": "/storage/own.mp4",
            "model": "MiniMax-H3",
            "status": "ok",
        }

    monkeypatch.setattr("app.billing.access.generate_video", fake_video)
    headers = _auth(isolated_client, "bill-e@videoforge.dev")
    isolated_client.post("/api/billing/recharge", headers=headers, json={"yuan": 10})
    save = isolated_client.put(
        "/api/billing/credentials",
        headers=headers,
        json={"provider": "minimax", "api_key": "user-secret-key-9876", "base_url": "https://api.minimax.cn"},
    )
    assert save.status_code == 200, save.text
    assert save.json()["credential"]["last4"] == "9876"
    assert "user-secret-key" not in save.text

    prefs = isolated_client.put("/api/billing/prefs", headers=headers, json={"video_source": "own", "video_provider": "minimax"})
    assert prefs.status_code == 200
    assert "user-secret-key" not in prefs.text

    pid = _project(isolated_client, headers)
    assert _put_scene(isolated_client, headers, pid).status_code == 200
    resp = isolated_client.post(
        "/api/director/generate/video",
        headers=headers,
        params={"project_id": pid},
        json={"prompt": "a walk", "scene_id": "scene_v", "shot_id": "scene_v", "duration": 5},
    )
    assert resp.status_code == 200, resp.text
    after = _status(isolated_client, headers).json()
    assert after["wallet"]["balance_fen"] == 1000
    assert captured["api_key"] == "user-secret-key-9876"
    assert captured["base_url"] == "https://api.minimax.cn"


def test_user_cannot_see_other_credentials(isolated_client):
    ha = _auth(isolated_client, "bill-f@videoforge.dev")
    hb = _auth(isolated_client, "bill-g@videoforge.dev")
    isolated_client.put(
        "/api/billing/credentials",
        headers=ha,
        json={"provider": "minimax", "api_key": "only-user-f-key-1111", "base_url": "https://api.minimax.cn"},
    )
    other = _status(isolated_client, hb).json()
    assert other["credentials"] == []
    assert "1111" not in str(other)
