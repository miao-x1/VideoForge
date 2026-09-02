"""测试公共 fixtures。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.task_service import task_store


@pytest.fixture(autouse=True)
def _clear_task_store():
    """每个测试前后清空 task_store 单例,避免测试间状态泄漏。"""
    task_store._tasks.clear()
    task_store._queues.clear()
    yield
    task_store._tasks.clear()
    task_store._queues.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_storage(tmp_path, monkeypatch):
    """将 STORAGE_ROOT 重定向到 tmp_path,隔离文件写入。

    storage_dir() 内部引用 app.core.config.STORAGE_ROOT 全局,
    monkeypatch 后所有 storage_dir() 调用都会落到 tmp_path 下。
    """
    monkeypatch.setattr("app.core.config.STORAGE_ROOT", tmp_path)
    return tmp_path
