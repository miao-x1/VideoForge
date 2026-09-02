"""测试 API 接口:失败任务的 failure_detail 推送 + 创建任务字段。"""
import pytest

from app.models.state import TaskStatus
from app.services.task_service import task_store


@pytest.fixture(autouse=True)
def _no_background_pipeline(monkeypatch):
    """阻止 POST /tasks 启动后台 Pipeline,只测 API 层。"""

    class _NoOp:
        async def execute(self, state):
            return state

    monkeypatch.setattr("app.api.routes.orchestrator", _NoOp())


def test_create_task_accepts_all_fields(client):
    """POST /tasks 接受 aspect_ratio + compliance_enabled(修复 CreateTaskRequest 缺字段)。"""
    resp = client.post("/api/video/tasks", json={
        "user_input": "测试创意",
        "duration": 15,
        "style": "轻松搞笑",
        "aspect_ratio": "9:16",
        "compliance_enabled": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"

    # 验证任务确实被创建,且字段已传入
    state = task_store.get(data["task_id"])
    assert state is not None
    assert state.compliance_enabled is True
    assert state.aspect_ratio == "9:16"


def test_get_result_includes_failure_detail(client):
    """GET /result 对失败任务返回 failure_detail(stage/reason/input_files)。"""
    state = task_store.create(
        user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    )
    state.status = TaskStatus.FAILED
    state.error = "[阶段:ASSEMBLING] RuntimeError: 模拟合成失败"
    state.failure_detail = {
        "stage": "ASSEMBLING",
        "reason": "RuntimeError: 模拟合成失败",
        "input_files": ["/tmp/img1.png", "/tmp/audio1.wav"],
    }
    task_store.save(state)

    resp = client.get(f"/api/video/tasks/{state.task_id}/result")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["failure_detail"] is not None
    assert data["failure_detail"]["stage"] == "ASSEMBLING"
    assert len(data["failure_detail"]["input_files"]) == 2


def test_get_status_includes_error(client):
    """GET /status 对失败任务返回 error 字段。"""
    state = task_store.create(
        user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    )
    state.status = TaskStatus.FAILED
    state.error = "[阶段:GENERATING_ASSETS] RuntimeError: 图片生成失败"
    task_store.save(state)

    resp = client.get(f"/api/video/tasks/{state.task_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert "图片生成失败" in data["error"]


def test_stream_yields_failure_detail(client):
    """GET /stream 对失败任务推送 failure_detail 并终止。"""
    state = task_store.create(
        user_input="测试", duration=10, style="",
        aspect_ratio="9:16", compliance_enabled=False,
    )
    state.status = TaskStatus.FAILED
    state.failure_detail = {
        "stage": "GENERATING_ASSETS",
        "reason": "RuntimeError: 图片生成失败",
        "input_files": [],
    }
    task_store.save(state)

    resp = client.get(f"/api/video/tasks/{state.task_id}/stream")
    assert resp.status_code == 200
    assert "FAILED" in resp.text
    assert "GENERATING_ASSETS" in resp.text
    assert "failure_detail" in resp.text
