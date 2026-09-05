"""测试公共 fixtures。"""
import os

os.environ.setdefault("APP_ENV", "test")

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.task_service import task_store


@pytest.fixture(autouse=True)
def _clear_task_store():
    task_store._cache.clear()
    task_store._queues.clear()
    yield
    task_store._cache.clear()
    task_store._queues.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_storage(tmp_path, monkeypatch):
    from app.core.config import STORAGE_ROOT as _orig
    import app.core.config as cfg
    monkeypatch.setattr(cfg, "STORAGE_ROOT", tmp_path)
    from app.db.database import reset_engine, init_db
    reset_engine()
    asyncio.run(init_db())
    yield tmp_path
    reset_engine()
    monkeypatch.setattr(cfg, "STORAGE_ROOT", _orig)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    resp = client.post("/api/auth/register", json={
        "email": "test@videoforge.dev",
        "password": "testpass123",
        "display_name": "TestUser",
    })
    if resp.status_code == 409:
        resp = client.post("/api/auth/login", json={
            "email": "test@videoforge.dev",
            "password": "testpass123",
        })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
