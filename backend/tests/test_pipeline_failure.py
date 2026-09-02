"""测试 Pipeline 失败时 failure_detail 结构化记录。

覆盖两个失败场景:
1. Assembly 阶段失败 → failure_detail.stage=ASSEMBLING, reason 含镜头数/I2V 片段数/输出路径
2. 素材生成阶段失败 → failure_detail.stage=GENERATING_ASSETS
"""
import asyncio
from pathlib import Path

from app.models.state import TaskStatus, VideoGenerationState
from app.orchestrator.orchestrator import Orchestrator
from app.providers.image.base import ImageProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.music.base import MusicProvider
from app.providers.video.base import VideoProvider
from app.providers.voice.base import VoiceProvider
from app.video.assembly import VideoAssembler


# ---- 轻量 Fake Provider:创建空占位文件,不触发真实媒体处理 ----

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


class _FakeI2VProvider(VideoProvider):
    async def generate(self, *, image_path, prompt, save_path, duration=5):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


# ---- 失败注入 Provider ----

class _FailingAssembler(VideoAssembler):
    async def assemble(self, **kwargs):
        raise RuntimeError("模拟合成失败")


class _FailingImageProvider(ImageProvider):
    async def generate(self, **kwargs):
        raise RuntimeError("图片生成失败")


# ---- 测试用例 ----

def test_assembly_failure_populates_failure_detail(fake_storage):
    """Assembly 失败 → failure_detail 记录 stage=ASSEMBLING + reason + input_files。"""
    state = VideoGenerationState(
        user_input="测试创意", duration=10, compliance_enabled=False,
    )
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FakeImageProvider(),
        voice=_FakeVoiceProvider(),
        music=_FakeMusicProvider(),
        video=_FakeI2VProvider(),
        assembler=_FailingAssembler(),
    )
    asyncio.run(orch.execute(state))

    assert state.status == TaskStatus.FAILED
    assert state.failure_detail is not None
    assert state.failure_detail["stage"] == "ASSEMBLING"
    # reason 包含 Assembly 专属上下文(镜头数 / I2V 片段数 / 输出路径)
    assert "Assembly 失败" in state.failure_detail["reason"]
    assert "shots=" in state.failure_detail["reason"]
    # Assembly 失败前素材已全部生成,input_files 非空
    assert len(state.failure_detail["input_files"]) > 0


def test_media_failure_populates_failure_detail(fake_storage):
    """素材生成失败 → failure_detail 记录 stage=GENERATING_ASSETS。"""
    state = VideoGenerationState(
        user_input="测试创意", duration=10, compliance_enabled=False,
    )
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FailingImageProvider(),
        voice=_FakeVoiceProvider(),
        music=_FakeMusicProvider(),
        video=_FakeI2VProvider(),
    )
    asyncio.run(orch.execute(state))

    assert state.status == TaskStatus.FAILED
    assert state.failure_detail is not None
    assert state.failure_detail["stage"] == "GENERATING_ASSETS"
    assert "RuntimeError" in state.failure_detail["reason"]
