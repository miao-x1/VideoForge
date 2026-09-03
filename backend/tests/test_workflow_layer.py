"""Workflow 层针对性测试:converter / registry / adapter / capability_router。

不发起真实 API 调用;comfy_service 用 monkeypatch 模拟 HTTP 层。
覆盖任务书第二十条:最小输入/正常输入/多参数/异常输入(参数缺失、注入点不存在、
Workflow 不存在、API Key 缺失、云端不可达、生成失败、超时)/重试。
"""
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.exceptions import InsufficientBalanceError, ProviderError
from workflows.adapter import (
    duration_to_length,
    resolve_aspect_ratio,
    workflow_adapter,
    WorkflowValidationError,
)
from workflows.converter import ui_to_api
from workflows.registry import workflow_registry, WorkflowNotFoundError
from app.services.capability_router import select_workflow, WorkflowNotAvailableError


# ---------------------------------------------------------------- converter
def test_converter_t2v():
    """T2V 子图展开:prompt 注入点应解析到内部 MiniMaxH3ImageToVideo 节点。"""
    wf = workflow_registry.load_workflow("minimax_h3_t2v_v1")
    api, subgraph_inputs = ui_to_api(wf)

    # 展开后的子图内部节点均以 "140:" 前缀存在
    assert "140:131" in api and api["140:131"]["class_type"] == "MiniMaxH3ImageToVideo"
    # prompt 提升输入 → 内部节点 131 的 prompt 字段
    targets = subgraph_inputs[(140, "prompt")]
    assert ("140:131", "prompt") in targets
    # 默认 widget 值已填充(长 prompt 模板文本)
    assert isinstance(api["140:131"]["inputs"]["prompt"], str)
    # width 由 ResolutionSelector 外部连线接入
    assert api["140:131"]["inputs"]["width"] == ["115", 0]
    # 子图输出 → SaveVideo
    assert api["92"]["inputs"]["video"] == ["140:130", 0]
    # 输出视频节点存在
    assert api["92"]["class_type"] == "SaveVideo"
    print("PASS converter_t2v")


def test_converter_i2v():
    """I2V:LoadImage → 子图 first_frame;分辨率连线。"""
    wf = workflow_registry.load_workflow("minimax_h3_i2v_v1")
    api, subgraph_inputs = ui_to_api(wf)
    assert api["114"]["class_type"] == "LoadImage"
    # first_frame 输入映射到内部节点
    assert (105, "first_frame") in subgraph_inputs
    key, field = subgraph_inputs[(105, "first_frame")][0]
    assert api[key]["inputs"][field] == ["114", 0]  # LoadImage 接入
    # width/height 来自 ResolutionSelector
    assert api["105:104"]["class_type"] == "MiniMaxH3ImageToVideo"
    assert api["105:104"]["inputs"]["width"] == ["115", 0]
    print("PASS converter_i2v")


def test_converter_r2v():
    """R2V 全展开图:参考图/提示词/分辨率连线保持。"""
    wf = workflow_registry.load_workflow("minimax_h3_r2v_v1")
    api, _ = ui_to_api(wf)
    h3 = api["136"]
    assert h3["class_type"] == "MiniMaxH3ReferenceToVideo"
    assert h3["inputs"]["prompt"] == ["138", 0]          # PrimitiveStringMultiline
    assert h3["inputs"]["ref_images.ref_image_0"] == ["137", 0]  # LoadImage 1
    assert h3["inputs"]["ref_images.ref_image_1"] == ["139", 0]  # LoadImage 2
    assert h3["inputs"]["width"] == ["115", 0]
    print("PASS converter_r2v")


# ---------------------------------------------------------------- adapter
def test_adapter_i2v_params():
    """正常输入 + 多参数:业务参数注入到正确节点。"""
    api = workflow_adapter.build_prompt("minimax_h3_i2v_v1", {
        "prompt": "霓虹雨巷中的机械少女",
        "first_frame": "upload_abc.png",
        "width": 704, "height": 1280,
        "duration": 5.0,
        "seed": 42,
    })
    h3 = api["105:104"]
    assert h3["inputs"]["prompt"] == "霓虹雨巷中的机械少女"
    assert api["114"]["inputs"]["image"] == "upload_abc.png"
    assert h3["inputs"]["width"] == 704  # 覆盖 ResolutionSelector 连线
    assert h3["inputs"]["height"] == 1280
    # duration(value_1)注入到内部 PrimitiveFloat,再经表达式换算 length
    assert api["105:111"]["inputs"]["value"] == 5.0
    assert api["105:15"]["inputs"]["noise_seed"] == 42  # RandomNoise
    print("PASS adapter_i2v_params")


def test_adapter_t2v_minimal():
    """最小输入:仅 prompt(T2V 无图)。"""
    api = workflow_adapter.build_prompt("minimax_h3_t2v_v1", {"prompt": "一只猫"})
    assert api["140:131"]["inputs"]["prompt"] == "一只猫"
    print("PASS adapter_t2v_minimal")


def test_adapter_r2v_with_length():
    """R2V:duration 换算 length 注入。"""
    length = duration_to_length(5.0)
    api = workflow_adapter.build_prompt("minimax_h3_r2v_v1", {
        "prompt": "参考风格生成", "ref_image_0": "ref.png", "length": length,
    })
    assert api["136"]["inputs"]["length"] == length
    assert api["138"]["inputs"]["value"] == "参考风格生成"  # Prompt 经 PrimitiveStringMultiline 输入
    assert api["137"]["inputs"]["image"] == "ref.png"
    print("PASS adapter_r2v_with_length")


def test_adapter_missing_required():
    """异常输入:必填缺失 → WorkflowValidationError。"""
    try:
        workflow_adapter.build_prompt("minimax_h3_i2v_v1", {"prompt": "x"})  # 缺 first_frame
        raise AssertionError("应当抛出 WorkflowValidationError")
    except WorkflowValidationError as e:
        assert "first_frame" in str(e)
    print("PASS adapter_missing_required")


def test_adapter_workflow_not_found():
    """异常输入:Workflow 不存在。"""
    try:
        workflow_adapter.build_prompt("no_such_workflow", {"prompt": "x"})
        raise AssertionError("应当抛出 WorkflowNotFoundError")
    except WorkflowNotFoundError:
        pass
    print("PASS adapter_workflow_not_found")


# ---------------------------------------------------------------- 数值规则
def test_resolution_alignment():
    assert resolve_aspect_ratio("9:16") == (704, 1280)
    assert resolve_aspect_ratio("16:9") == (1280, 704)
    assert resolve_aspect_ratio(None) == (704, 1280)
    print("PASS resolution_alignment")


def test_duration_to_length():
    # 官方表达式: max(5, round(a*24)) + (5 - 帧数%17)%17
    assert duration_to_length(5) == 120 + (5 - 120 % 17) % 17
    assert duration_to_length(0.1) == 5 + (5 - 5 % 17) % 17
    print("PASS duration_to_length")


# ---------------------------------------------------------------- capability router
def test_capability_router():
    assert select_workflow("image_to_video").workflow_id == "minimax_h3_i2v_v1"
    assert select_workflow("text_to_video").workflow_id == "minimax_h3_t2v_v1"
    assert select_workflow("reference_to_video").workflow_id == "minimax_h3_r2v_v1"
    assert select_workflow("image_to_video", preferred_workflow="minimax_h3_t2v_v1").workflow_id == "minimax_h3_t2v_v1"
    try:
        select_workflow("video_upscale")
        raise AssertionError("应当抛出 WorkflowNotAvailableError")
    except WorkflowNotAvailableError:
        pass
    try:
        select_workflow("image_to_video", preferred_workflow="nope")
        raise AssertionError("应当抛出 WorkflowNotAvailableError")
    except WorkflowNotAvailableError:
        pass
    print("PASS capability_router")


# ---------------------------------------------------------------- comfy_service (mock HTTP)
class _FakeResponse:
    def __init__(self, payload, code=200):
        self.payload = payload
        self.code = code

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeClient:
    """替换 ComfyCloudClient 的 _request,模拟云端行为(含错误转换语义)。"""

    def __init__(self):
        self.jobs = {}
        self.outputs = {}
        self.error_code = None  # 注入错误:ProviderError.error_code
        self.calls = 0
        self.submit_attempts = 0
        self.fail_first_submit = False
        self.video_bytes = b"FAKE_MP4" * 100

    def request(self, method, path, **kw):
        self.calls += 1
        if self.error_code:
            code, self.error_code = self.error_code, None
            if code == "INSUFFICIENT_BALANCE":
                raise InsufficientBalanceError("video/comfy", "额度不足")
            raise ProviderError("video/comfy", f"注入错误 {code}", error_code=code)
        if path == "/api/upload/image":
            return json.dumps({"name": "cloud_img.png", "subfolder": ""}).encode()
        if path == "/api/prompt":
            self.submit_attempts += 1
            if self.fail_first_submit and self.submit_attempts == 1:
                self.fail_first_submit = False
                raise ProviderError("video/comfy", "瞬态错误", error_code="HTTP_ERROR")
            pid = f"job-{self.submit_attempts}"
            self.jobs[pid] = "executing"
            return json.dumps({"prompt_id": pid}).encode()
        if path.startswith("/api/job/"):
            pid = path.split("/")[3]
            self.jobs[pid] = "success"
            return json.dumps({"status": self.jobs[pid]}).encode()
        if path.startswith("/api/history/"):
            pid = path.split("/")[3]
            return json.dumps({pid: {"outputs": {"92": {"videos": [
                {"filename": "out.mp4", "subfolder": "", "type": "output"}
            ]}}}}).encode()
        if path.startswith("/api/view"):
            return self.video_bytes
        raise AssertionError(f"未预期的请求: {path}")


def _make_provider(fake):
    from app.services.comfy_service import ComfyCloudClient
    client = ComfyCloudClient.__new__(ComfyCloudClient)
    client.base_url = "https://cloud.comfy.org"
    client.api_key = "test-key"
    client._request = lambda method, path, **kw: fake.request(method, path, **kw)

    from app.providers.video.comfy_video import ComfyVideoProvider
    provider = ComfyVideoProvider.__new__(ComfyVideoProvider)
    provider.workflow_id = None
    provider._client = client
    return provider


def test_provider_happy_path():
    """正常链路:上传 → 提交 → 轮询 → 取回 → 保存。"""
    fake = _FakeClient()
    provider = _make_provider(fake)
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "first.png"
        img.write_bytes(b"PNG")
        out = Path(tmp) / "video.mp4"
        resp = asyncio.run(provider.generate(__import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest(
            image_path=str(img), prompt="雨夜长安", save_path=str(out), duration=5, aspect_ratio="9:16",
        )))
        assert resp.model == "MiniMax-H3" and resp.task_id.startswith("job-")
        assert out.read_bytes() == fake.video_bytes
    print("PASS provider_happy_path")


def test_provider_retry_transient():
    """重试:首次提交瞬态失败 → 第二次成功。"""
    fake = _FakeClient()
    fake.fail_first_submit = True
    provider = _make_provider(fake)
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "first.png"; img.write_bytes(b"PNG")
        out = Path(tmp) / "v.mp4"
        resp = asyncio.run(provider.generate(__import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest(
            image_path=str(img), prompt="p", save_path=str(out), duration=5,
        )))
        assert fake.submit_attempts == 2 and out.exists()
    print("PASS provider_retry_transient")


def test_provider_invalid_key_no_retry():
    """API Key 错误:立即失败不重试。"""
    fake = _FakeClient()
    fake.error_code = "INVALID_API_KEY"
    provider = _make_provider(fake)
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "first.png"; img.write_bytes(b"PNG")
        out = Path(tmp) / "v.mp4"
        try:
            asyncio.run(provider.generate(__import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest(
                image_path=str(img), prompt="p", save_path=str(out), duration=5,
            )))
            raise AssertionError("应当抛出 INVALID_API_KEY")
        except ProviderError as e:
            assert e.error_code == "INVALID_API_KEY" and fake.submit_attempts <= 1
    print("PASS provider_invalid_key_no_retry")


def test_provider_generation_failed():
    """生成失败:终态 error → GENERATION_FAILED。"""
    fake = _FakeClient()

    def _fail_status(method, path, **kw):
        if path.startswith("/api/job/"):
            return json.dumps({"status": "error"}).encode()
        return fake.request(method, path, **kw)

    provider = _make_provider(fake)
    provider._client._request = _fail_status
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "first.png"; img.write_bytes(b"PNG")
        out = Path(tmp) / "v.mp4"
        try:
            asyncio.run(provider.generate(__import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest(
                image_path=str(img), prompt="p", save_path=str(out), duration=5,
            )))
            raise AssertionError("应当抛出 GENERATION_FAILED")
        except ProviderError as e:
            assert e.error_code == "GENERATION_FAILED"
    print("PASS provider_generation_failed")


def test_provider_image_not_found():
    """异常输入:图片不存在。"""
    fake = _FakeClient()
    provider = _make_provider(fake)
    try:
        asyncio.run(provider.generate(__import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest(
            image_path="Z:/no/such.png", prompt="p", save_path="Z:/out.mp4", duration=5,
        )))
        raise AssertionError("应当抛出 INPUT_NOT_FOUND")
    except ProviderError as e:
        assert e.error_code == "INPUT_NOT_FOUND"
    print("PASS provider_image_not_found")


def test_provider_not_configured():
    """API Key 未配置:NOT_CONFIGURED。"""
    from app.services.comfy_service import ComfyCloudClient
    import app.core.config as cfg
    old = cfg.settings.comfy_api_key
    try:
        cfg.settings.comfy_api_key = ""
        try:
            ComfyCloudClient()
            raise AssertionError("应当抛出 NOT_CONFIGURED")
        except ProviderError as e:
            assert e.error_code == "NOT_CONFIGURED"
    finally:
        cfg.settings.comfy_api_key = old
    print("PASS provider_not_configured")


def test_provider_balance():
    """额度不足:InsufficientBalanceError(HTTP 402 转换)。"""
    from app.services.comfy_service import ComfyCloudClient
    try:
        ComfyCloudClient._raise_http_error(402, "credits")
        raise AssertionError("应当抛出 InsufficientBalanceError")
    except InsufficientBalanceError:
        pass
    # 401/403 → INVALID_API_KEY;404 → NOT_FOUND;429 → RATE_LIMITED
    for code, expect in [(401, "INVALID_API_KEY"), (403, "INVALID_API_KEY"), (404, "NOT_FOUND"), (429, "RATE_LIMITED")]:
        try:
            ComfyCloudClient._raise_http_error(code, "")
            raise AssertionError(f"HTTP {code} 应当抛出 ProviderError")
        except ProviderError as e:
            assert e.error_code == expect, f"HTTP {code} → {e.error_code}"
    print("PASS provider_balance")


def test_concurrent_generation():
    """并发:同时生成多个视频。"""
    fake = _FakeClient()
    provider = _make_provider(fake)
    base = __import__("app.providers.video.base", fromlist=["ModelRequest"]).ModelRequest

    async def run(i):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "f.png"; img.write_bytes(b"PNG")
            out = Path(tmp) / "v.mp4"
            return await provider.generate(base(
                image_path=str(img), prompt=f"并发任务{i}", save_path=str(out), duration=5,
            ))

    async def main():
        return await asyncio.gather(*[run(i) for i in range(3)])

    results = asyncio.run(main())
    assert all(r.model == "MiniMax-H3" for r in results)
    print("PASS concurrent_generation")


if __name__ == "__main__":
    test_converter_t2v()
    test_converter_i2v()
    test_converter_r2v()
    test_adapter_i2v_params()
    test_adapter_t2v_minimal()
    test_adapter_r2v_with_length()
    test_adapter_missing_required()
    test_adapter_workflow_not_found()
    test_resolution_alignment()
    test_duration_to_length()
    test_capability_router()
    test_provider_happy_path()
    test_provider_retry_transient()
    test_provider_invalid_key_no_retry()
    test_provider_generation_failed()
    test_provider_image_not_found()
    test_provider_not_configured()
    test_provider_balance()
    test_concurrent_generation()
    print("ALL PASS")
