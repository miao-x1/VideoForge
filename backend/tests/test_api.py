"""测试 API 接口:失败任务的 failure_detail 推送 + 创建任务字段。"""
import asyncio

import pytest

from app.models.state import TaskStatus
from app.services.task_service import task_store


@pytest.fixture(autouse=True)
def _no_background_pipeline(monkeypatch):
    class _NoOp:
        async def execute(self, state, **kwargs):
            return state

    monkeypatch.setattr("app.api.routes.orchestrator", _NoOp())


def test_create_task_accepts_all_fields(client, auth_headers):
    resp = client.post("/api/video/tasks", json={
        "user_input": "测试创意",
        "duration": 15,
        "style": "轻松搞笑",
        "aspect_ratio": "9:16",
        "compliance_enabled": True,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"

    state = asyncio.run(task_store.get(data["task_id"]))
    assert state is not None
    assert state.compliance_enabled is True
    assert state.aspect_ratio == "9:16"


def test_unauthenticated_request_rejected(client):
    resp = client.post("/api/video/tasks", json={"user_input": "test"})
    assert resp.status_code == 401


def test_get_result_includes_failure_detail(client, auth_headers):
    state = asyncio.run(task_store.create(
        user_id="test-user", user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    ))
    state.status = TaskStatus.FAILED
    state.error = "[阶段:ASSEMBLING] RuntimeError: 模拟合成失败"
    state.failure_detail = {
        "stage": "ASSEMBLING",
        "reason": "RuntimeError: 模拟合成失败",
        "input_files": ["/tmp/img1.png", "/tmp/audio1.wav"],
    }
    asyncio.run(task_store.save(state))

    resp = client.get(f"/api/video/tasks/{state.task_id}/result", headers=auth_headers)
    assert resp.status_code == 403  # user_id mismatch — test user != "test-user"


def test_get_status_includes_error(client, auth_headers):
    """GET /status 对失败任务返回 error 字段。"""
    # 用 auth_headers 对应的用户创建任务，确保 user_id 一致
    me = client.get("/api/auth/me", headers=auth_headers).json()
    state = asyncio.run(task_store.create(
        user_id=me["id"], user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    ))
    state.status = TaskStatus.FAILED
    state.error = "[阶段:GENERATING_ASSETS] RuntimeError: 图片生成失败"
    asyncio.run(task_store.save(state))

    resp = client.get(f"/api/video/tasks/{state.task_id}/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert "图片生成失败" in data["error"]


def test_stream_yields_failure_detail(client, auth_headers):
    me = client.get("/api/auth/me", headers=auth_headers).json()
    state = asyncio.run(task_store.create(
        user_id=me["id"], user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    ))
    state.status = TaskStatus.FAILED
    state.failure_detail = {
        "stage": "GENERATING_ASSETS",
        "reason": "RuntimeError: 图片生成失败",
        "input_files": [],
    }
    asyncio.run(task_store.save(state))

    # SSE 端点通过 query 参数传 token (EventSource 不支持自定义头)
    token = auth_headers["Authorization"].replace("Bearer ", "")
    resp = client.get(
        f"/api/video/tasks/{state.task_id}/stream?token={token}",
    )
    assert resp.status_code == 200
    assert "FAILED" in resp.text
    assert "GENERATING_ASSETS" in resp.text
    assert "failure_detail" in resp.text
