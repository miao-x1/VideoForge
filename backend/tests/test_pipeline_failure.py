"""测试 Pipeline 失败时 failure_detail 结构化记录。

覆盖两个失败场景:
1. Assembly 阶段失败 → failure_detail.stage=ASSEMBLING, reason 含镜头数/I2V 片段数/输出路径
2. 素材生成阶段失败 → failure_detail.stage=GENERATING_ASSETS
"""
import asyncio
from pathlib import Path

import pytest

from app.models.state import TaskStatus, VideoGenerationState
from app.orchestrator.orchestrator import Orchestrator
from app.providers.image.base import ImageProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.music.base import MusicProvider
from app.providers.video.base import VideoModelProvider, ModelRequest, ModelResponse
from app.providers.voice.base import VoiceProvider
from app.video.assembly import VideoAssembler


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch):
    """强制 mock 模式:避免 _get_reasoning_llm 注入真实 DashScope LLM(依赖账户余额)。"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "enable_mock_providers", True)


class _FakeImageProvider(ImageProvider):
    async def generate(self, *, prompt, save_path, width=1280, height=720):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


class _FakeVoiceProvider(VoiceProvider):
    async def generate(self, *, text, save_path, duration):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


class _FakeMusicProvider(MusicProvider):
    async def generate(self, *, save_path, duration, mood="light"):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


class _FakeVideoProvider(VideoModelProvider):
    @property
    def name(self) -> str:
        return "fake"

    @property
    def capabilities(self):
        from app.providers.video.capabilities import ModelCapabilities
        return ModelCapabilities()

    async def generate(self, request: ModelRequest) -> ModelResponse:
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(b"fake")
        return ModelResponse(video_path=request.save_path, duration=request.duration, model=self.name)


class _FailingAssembler(VideoAssembler):
    async def assemble(self, **kwargs):
        raise RuntimeError("模拟合成失败")


class _FailingImageProvider(ImageProvider):
    async def generate(self, **kwargs):
        raise RuntimeError("图片生成失败")


def test_assembly_failure_populates_failure_detail(fake_storage):
    state = VideoGenerationState(
        user_id="test-user", user_input="测试创意", duration=10, compliance_enabled=False,
    )
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FakeImageProvider(),
        voice=_FakeVoiceProvider(),
        music=_FakeMusicProvider(),
        video=_FakeVideoProvider(),
        assembler=_FailingAssembler(),
    )
    asyncio.run(orch.execute(state))

    assert state.status == TaskStatus.FAILED
    assert state.failure_detail is not None
    assert state.failure_detail["stage"] == "ASSEMBLING"
    assert "Assembly 失败" in state.failure_detail["reason"]
    assert "shots=" in state.failure_detail["reason"]
    assert len(state.failure_detail["input_files"]) > 0


def test_media_failure_populates_failure_detail(fake_storage):
    state = VideoGenerationState(
        user_id="test-user", user_input="测试创意", duration=10, compliance_enabled=False,
    )
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FailingImageProvider(),
        voice=_FakeVoiceProvider(),
        music=_FakeMusicProvider(),
        video=_FakeVideoProvider(),
    )
    asyncio.run(orch.execute(state))

    assert state.status == TaskStatus.FAILED
    assert state.failure_detail is not None
    assert state.failure_detail["stage"] == "GENERATING_ASSETS"
    assert "RuntimeError" in state.failure_detail["reason"]
