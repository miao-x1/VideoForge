"""Phase 4/5 测试:镜头连续性(ShotPlanner)与 Workflow 层成型。

Phase 4 覆盖:
- StoryboardAgent 产出分镜后构建 shot_state 因果链(prev/next 闭合)
- scene_state 按场景聚合
- 角色参考资产(ref_asset_ids)随出场人物自动挂接
- 单镜重生成保持连续性(继承相邻镜头 continuity,链不被破坏)

Phase 5 覆盖:
- ShotRouter 逐镜头模式决策矩阵(t2v/i2v/r2v/first_last/unsupported)
- ImageWorkflow:t2v/r2v 镜头跳过关键帧,资产台账登记
- VideoWorkflow:T2V 路径放开(image_path=None)、first_last、r2v、模式台账
- ModelRequest 放开后 Qwen(I2V-only)对无首帧请求显式拒绝
- TTS/Music Workflow 资产登记与 BGM 情绪贯通
"""
import asyncio
import os

import pytest

from app.agents.character_agent import CharacterAgent
from app.agents.requirement_agent import RequirementAgent
from app.agents.script_agent import ScriptAgent
from app.agents.story_planner_agent import StoryPlannerAgent
from app.agents.storyboard_agent import StoryboardAgent
from app.agents.world_agent import WorldAgent
from app.core.exceptions import ProviderError
from app.director.project_state import AssetEntry
from app.input.base import InputSource
from app.models.state import VideoGenerationState
from app.providers.image.base import ImageProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.music.base import MusicProvider
from app.providers.video.base import ModelRequest, ModelResponse, VideoModelProvider
from app.providers.video.capabilities import ModelCapabilities
from app.providers.voice.base import VoiceProvider
from app.router.shot_router import decide_video_mode
from app.workflows import (
    ImageWorkflow,
    MusicWorkflow,
    TTSWorkflow,
    VideoWorkflow,
)


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "enable_mock_providers", True)


# ---------------------------- 测试基建 ----------------------------

def _state_with_requirement() -> VideoGenerationState:
    state = VideoGenerationState(user_input="我想做一个30秒虐恋短剧", duration=30, style="古风虐恋")
    asyncio.run(RequirementAgent(llm=MockLLMProvider()).run(state))
    assert state.requirement is not None
    return state


def _state_with_storyboard() -> VideoGenerationState:
    """经 requirement → planning → script → storyboard 的完整决策链(mock)。"""
    state = _state_with_requirement()
    llm = MockLLMProvider()
    asyncio.run(StoryPlannerAgent(llm=llm).run(state))
    asyncio.run(CharacterAgent(llm=llm).run(state))
    asyncio.run(WorldAgent(llm=llm).run(state))
    asyncio.run(ScriptAgent(llm=llm).run(state))
    asyncio.run(StoryboardAgent(llm=llm).run(state))
    assert state.storyboard is not None and state.storyboard.shots
    return state


class _FakeImageProvider(ImageProvider):
    name = "fake-image"

    async def generate(self, *, prompt, save_path, width=1280, height=720):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake-png")
        return save_path


class _FakeVoiceProvider(VoiceProvider):
    name = "fake-voice"

    async def generate(self, *, text, save_path, duration):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake-wav")
        return save_path


class _FakeMusicProvider(MusicProvider):
    name = "fake-music"

    def __init__(self):
        self.last_mood = None

    async def generate(self, *, save_path, duration, mood="light"):
        from pathlib import Path
        self.last_mood = mood
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake-music")
        return save_path


class _FakeVideoProvider(VideoModelProvider):
    """记录每次请求的假视频 Provider,能力可配置。"""

    def __init__(self, *, supports_t2v=False, supports_last_frame=False, supports_image=True):
        self._caps = ModelCapabilities(
            supports_text_to_video=supports_t2v,
            supports_last_frame=supports_last_frame,
            supports_image_input=supports_image,
            supports_first_frame=supports_image,
        )
        self.requests: list[ModelRequest] = []

    @property
    def name(self) -> str:
        return "fake-video"

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._caps

    async def generate(self, request: ModelRequest) -> ModelResponse:
        from pathlib import Path
        self.requests.append(request)
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(b"fake-mp4")
        return ModelResponse(video_path=request.save_path, duration=request.duration, model=self.name)


# ============================ Phase 4:连续性 ============================

def test_shot_state_causal_chain_closed():
    state = _state_with_storyboard()
    ps = state.project_state
    n = len(state.storyboard.shots)
    assert len(ps.shot_state.shots) == n
    # 因果链闭合:首镜无前、末镜无后、中间双向连通
    assert ps.shot_state.chain_closed()
    ordered = ps.shot_state.shots
    assert ordered[0].prev_shot is None and ordered[-1].next_shot is None
    assert ordered[0].next_shot == 1 and ordered[-1].prev_shot == n - 2
    # 连续性字段:非首镜必须有继承状态与叙事因果
    for i, entry in enumerate(ordered):
        assert entry.desired_duration == state.storyboard.shots[i].duration
        if i > 0:
            assert entry.continuity_in, f"shot{i} 缺少 continuity_in"
            assert entry.causal_note, f"shot{i} 缺少 causal_note"
        assert entry.continuity_out


def test_scene_state_aggregated_from_shots():
    state = _state_with_storyboard()
    ps = state.project_state
    scene_ids = {s.scene_id for s in state.storyboard.shots}
    assert {s.scene_id for s in ps.scene_state.scenes} == scene_ids
    for scene in ps.scene_state.scenes:
        assert scene.shot_count >= 1
        assert scene.characters  # 聚合出场人物非空
        assert scene.location


def test_character_reference_assets_wired_to_shots(fake_storage):
    state = _state_with_storyboard()
    ps = state.project_state
    # 给主角 Bible 挂参考资产,并在 asset_state 登记一张真实存在的参考图
    ref_path = os.path.join(str(fake_storage), "ref_main.png")
    with open(ref_path, "wb") as f:
        f.write(b"ref")
    bible = ps.character_state.bibles[0]
    bible.reference_asset_ids = ["asset_ref_main"]
    ps.asset_state.add(AssetEntry(
        asset_id="asset_ref_main", type="reference", path=ref_path,
        character_id=bible.character_id, source_provider="user",
    ))
    # 重新同步分镜态(模拟重新规划)
    asyncio.run(StoryboardAgent(llm=MockLLMProvider()).run(state))
    ps = state.project_state
    main_shots = [e for e in ps.shot_state.shots if bible.name in e.characters]
    assert main_shots, "mock 分镜中应有主角出场镜头"
    assert all("asset_ref_main" in e.ref_asset_ids for e in main_shots)


def test_regenerate_shot_preserves_continuity():
    state = _state_with_storyboard()
    agent = StoryboardAgent(llm=MockLLMProvider())
    prev_out_before = state.storyboard.shots[0].continuity_out
    next_in_before = state.storyboard.shots[2].continuity_in

    asyncio.run(agent.regenerate_shot(state, 1))

    shots = state.storyboard.shots
    assert len(shots) == 6  # 30s/5s = 6 镜,数量不变
    # 新镜头必须继承相邻镜头的连续性状态
    assert shots[1].continuity_in == prev_out_before
    assert shots[1].continuity_out == next_in_before
    # 因果链重新闭合
    assert state.project_state.shot_state.chain_closed()
    assert state.project_state.shot_state.get(1).causal_note


# ============================ Phase 5:ShotRouter 决策矩阵 ============================

def test_router_default_i2v_with_keyframe():
    caps = ModelCapabilities()
    d = decide_video_mode(
        desired_mode="", has_first_frame=True, has_last_frame=False,
        has_references=False, caps=caps,
    )
    assert d.mode == "i2v" and d.use_first_frame and not d.use_last_frame


def test_router_first_last_when_both_frames_and_supported():
    caps = ModelCapabilities(supports_last_frame=True)
    d = decide_video_mode(
        desired_mode="", has_first_frame=True, has_last_frame=True,
        has_references=False, caps=caps,
    )
    assert d.mode == "first_last" and d.use_first_frame and d.use_last_frame


def test_router_first_last_falls_back_when_unsupported():
    caps = ModelCapabilities(supports_last_frame=False)
    d = decide_video_mode(
        desired_mode="", has_first_frame=True, has_last_frame=True,
        has_references=False, caps=caps,
    )
    assert d.mode == "i2v" and not d.use_last_frame


def test_router_t2v_for_empty_shot_when_supported():
    caps = ModelCapabilities(supports_text_to_video=True)
    d = decide_video_mode(
        desired_mode="t2v", has_first_frame=False, has_last_frame=False,
        has_references=False, caps=caps,
    )
    assert d.mode == "t2v" and not d.use_first_frame


def test_router_unsupported_when_t2v_needed_but_model_lacks_it():
    caps = ModelCapabilities(supports_text_to_video=False)
    d = decide_video_mode(
        desired_mode="t2v", has_first_frame=False, has_last_frame=False,
        has_references=False, caps=caps,
    )
    assert d.mode == "unsupported" and not d.feasible


def test_router_r2v_with_references_and_no_frame():
    caps = ModelCapabilities(supports_image_input=True)
    d = decide_video_mode(
        desired_mode="r2v", has_first_frame=False, has_last_frame=False,
        has_references=True, caps=caps,
    )
    assert d.mode == "r2v" and d.use_references and not d.use_first_frame


def test_router_desired_t2v_with_existing_frame_upgrades_to_i2v():
    caps = ModelCapabilities(supports_text_to_video=True)
    d = decide_video_mode(
        desired_mode="t2v", has_first_frame=True, has_last_frame=False,
        has_references=False, caps=caps,
    )
    assert d.mode == "i2v"  # 关键帧已就位,I2V 一致性更优


# ============================ Phase 5:Workflow 执行 ============================

def test_image_workflow_skips_t2v_and_r2v_shots(fake_storage):
    state = _state_with_storyboard()
    state.storyboard.shots[0].desired_mode = "t2v"
    state.storyboard.shots[1].desired_mode = "r2v"
    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))

    assert state.storyboard.shots[0].image_path is None
    assert state.storyboard.shots[1].image_path is None
    assert state.storyboard.shots[2].image_path  # 其余镜头正常生成关键帧
    # 资产台账:跳过的镜头无 image 资产
    ps = state.project_state
    assert ps.asset_state.for_shot(0) == []
    assert ps.asset_state.for_shot(2) and ps.asset_state.for_shot(2)[0].type == "image"
    assert ps.generation_state.current_stage == "image"


def test_video_workflow_t2v_path_sends_no_image(fake_storage):
    state = _state_with_storyboard()
    state.storyboard.shots[0].desired_mode = "t2v"
    image_wf = ImageWorkflow(_FakeImageProvider())
    video = _FakeVideoProvider(supports_t2v=True)
    video_wf = VideoWorkflow(video)

    asyncio.run(image_wf.run(state))
    asyncio.run(video_wf.run(state))

    # 首镜 T2V:请求无首帧
    req0 = video.requests[0]
    assert req0.image_path is None
    # 其余镜头 I2V:请求带首帧
    assert all(r.image_path for r in video.requests[1:])
    # 决策台账:首镜 t2v,全部成功
    ps = state.project_state
    assert ps.generation_state.latest_decision(0).mode == "t2v"
    assert ps.generation_state.completed_shots == list(range(len(state.storyboard.shots)))
    assert all(s.video_path for s in state.storyboard.shots)


def test_video_workflow_first_last_mode(fake_storage):
    state = _state_with_storyboard()
    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))
    video = _FakeVideoProvider(supports_last_frame=True)
    asyncio.run(VideoWorkflow(video).run(state))

    modes = [ps_d.mode for ps_d in state.project_state.generation_state.decisions]
    assert modes[0] == "first_last"  # 首镜有下一镜首帧作尾帧
    assert modes[-1] == "i2v"        # 末镜无尾帧
    assert video.requests[0].last_frame_path is not None


def test_video_workflow_r2v_with_user_reference(fake_storage):
    state = _state_with_storyboard()
    state.storyboard.shots[0].desired_mode = "r2v"
    # 用户上传一张参考图
    ref_path = os.path.join(str(fake_storage), "user_ref.png")
    with open(ref_path, "wb") as f:
        f.write(b"ref")
    state.input_sources = [InputSource(type="image", content=ref_path, purpose="subject")]

    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))  # r2v 镜跳过关键帧
    video = _FakeVideoProvider(supports_t2v=True)
    asyncio.run(VideoWorkflow(video).run(state))

    req0 = video.requests[0]
    assert req0.image_path is None
    assert req0.reference_paths and ref_path in req0.reference_paths
    assert state.project_state.generation_state.latest_decision(0).mode == "r2v"


def test_video_workflow_unsupported_mode_raises(fake_storage):
    state = _state_with_storyboard()
    state.storyboard.shots[0].desired_mode = "t2v"
    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))
    video = _FakeVideoProvider(supports_t2v=False)  # 类 Qwen:I2V-only
    with pytest.raises(ProviderError) as exc:
        asyncio.run(VideoWorkflow(video).run(state))
    assert exc.value.error_code == "MODE_UNSUPPORTED"


def test_tts_and_music_workflows_register_assets(fake_storage):
    state = _state_with_storyboard()
    ps = state.project_state
    ps.audio_state.music_mood = "tense"  # 模拟 AudioPlanner 决策(Phase 7)

    music = _FakeMusicProvider()
    asyncio.run(TTSWorkflow(_FakeVoiceProvider()).run(state))
    asyncio.run(MusicWorkflow(music).run(state))

    assert all(s.audio_path for s in state.storyboard.shots)
    assert music.last_mood == "tense"  # 音乐情绪不再写死 light
    assert ps.audio_state.bgm_asset_id == f"{state.task_id}_bgm"
    bgm_assets = [a for a in ps.asset_state.assets if a.type == "music"]
    assert bgm_assets and bgm_assets[0].metadata.get("mood") == "tense"


def test_qwen_provider_rejects_t2v_request(monkeypatch):
    """I2V-only 模型收到无首帧请求必须显式拒绝(而非隐式报错)。"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "qwen_api_key", "fake-key", raising=False)
    from app.providers.video.qwen_video import QwenVideoProvider
    provider = QwenVideoProvider()
    assert provider.capabilities.supports_text_to_video is False
    with pytest.raises(ProviderError) as exc:
        asyncio.run(provider.generate(ModelRequest(
            image_path=None, prompt="empty scene", save_path="x.mp4",
        )))
    assert exc.value.error_code == "MODE_UNSUPPORTED"
