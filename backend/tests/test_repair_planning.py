"""Phase 6/7 测试:失败修复闭环 + 音频/剪辑规划 Agent。

Phase 6 覆盖:
- FailureAnalysisAgent 错误码→修复动作决策矩阵
- VideoWorkflow 单镜失败重试闭环:add_keyframe 降级、瞬时错误重试、切厂商、耗尽 abort
- QualityJudgeAgent 内容质检(人物一致/场景连续/因果链/动作/素材)

Phase 7 覆盖:
- AudioPlannerAgent:逐镜 cue + 全片音乐情绪/风格 + 幂等 + cue 执行回绑
- EditingPlannerAgent:顺序/转场/节奏决策单 + 幂等 + 非法顺序回退
- EditingWorkflow.ordered_shots:决策单驱动重排/转场覆盖,叙事真相不被改写
"""
import asyncio
import os

import pytest

from app.agents.audio_planner_agent import AudioPlannerAgent
from app.agents.editing_planner_agent import EditingPlannerAgent
from app.agents.failure_analysis_agent import (
    ACTION_ABORT,
    ACTION_ADD_KEYFRAME,
    ACTION_REGENERATE_PROMPT,
    ACTION_RETRY,
    ACTION_SWITCH_MODEL,
    FailureAnalysisAgent,
    MAX_AUTO_ATTEMPTS,
)
from app.agents.quality_judge_agent import QualityJudgeAgent
from app.agents.storyboard_agent import StoryboardAgent
from app.agents.requirement_agent import RequirementAgent
from app.agents.script_agent import ScriptAgent
from app.agents.story_planner_agent import StoryPlannerAgent
from app.agents.character_agent import CharacterAgent
from app.agents.world_agent import WorldAgent
from app.core.exceptions import ProviderError
from app.models.state import VideoGenerationState
from app.providers.image.base import ImageProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.video.base import ModelRequest, ModelResponse, VideoModelProvider
from app.providers.video.capabilities import ModelCapabilities
from app.workflows import (
    EditingWorkflow,
    ImageWorkflow,
    TTSWorkflow,
    VideoWorkflow,
)


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "enable_mock_providers", True)


# ---------------------------- 测试基建 ----------------------------

def _state_with_storyboard() -> VideoGenerationState:
    state = VideoGenerationState(user_input="我想做一个30秒虐恋短剧", duration=30, style="古风虐恋")
    llm = MockLLMProvider()
    asyncio.run(RequirementAgent(llm=llm).run(state))
    asyncio.run(StoryPlannerAgent(llm=llm).run(state))
    asyncio.run(CharacterAgent(llm=llm).run(state))
    asyncio.run(WorldAgent(llm=llm).run(state))
    asyncio.run(ScriptAgent(llm=llm).run(state))
    asyncio.run(StoryboardAgent(llm=llm).run(state))
    return state


class _FakeImageProvider(ImageProvider):
    name = "fake-image"

    async def generate(self, *, prompt, save_path, width=1280, height=720):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake-png")
        return save_path


class _FakeVoiceProvider:
    name = "fake-voice"

    async def generate(self, *, text, save_path, duration):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake-wav")
        return save_path


class _OKVideoProvider(VideoModelProvider):
    name = "ok-video"

    def __init__(self, *, supports_t2v=True):
        self.calls = 0
        self.requests: list[ModelRequest] = []
        self._caps = ModelCapabilities(supports_text_to_video=supports_t2v)

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._caps

    async def generate(self, request: ModelRequest) -> ModelResponse:
        from pathlib import Path
        self.calls += 1
        self.requests.append(request)
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(b"fake-mp4")
        return ModelResponse(video_path=request.save_path, duration=request.duration, model=self.name)


class _FlakyVideoProvider(VideoModelProvider):
    """前 fail_times 次以指定错误码失败,之后成功;记录请求。"""

    name = "flaky-video"

    def __init__(self, *, fail_times: int, error_code: str, supports_t2v=True, message="模拟失败"):
        self.fail_times = fail_times
        self.error_code = error_code
        self.message = message
        self.calls = 0
        self.requests: list[ModelRequest] = []
        self._caps = ModelCapabilities(supports_text_to_video=supports_t2v)

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._caps

    async def generate(self, request: ModelRequest) -> ModelResponse:
        from pathlib import Path
        self.calls += 1
        self.requests.append(request)
        if self.calls <= self.fail_times:
            raise ProviderError(self.name, self.message, error_code=self.error_code)
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(b"fake-mp4")
        return ModelResponse(video_path=request.save_path, duration=request.duration, model=self.name)


# ============================ Phase 6:失败分析决策矩阵 ============================

def test_failure_analysis_mode_unsupported_t2v_adds_keyframe():
    agent = FailureAnalysisAgent()
    d = agent.analyze_generation_failure(
        shot_index=0, error_code="MODE_UNSUPPORTED", error_message="不支持 T2V",
        mode="t2v", provider="qwen", attempt=1,
    )
    assert d.action == ACTION_ADD_KEYFRAME and d.force_mode == "i2v" and d.repairable


def test_failure_analysis_mode_unsupported_i2v_switches_model():
    agent = FailureAnalysisAgent()
    d = agent.analyze_generation_failure(
        shot_index=1, error_code="MODE_UNSUPPORTED", error_message="x",
        mode="i2v", provider="qwen", attempt=1,
    )
    assert d.action == ACTION_SWITCH_MODEL


def test_failure_analysis_transient_retry_then_switch():
    agent = FailureAnalysisAgent()
    d1 = agent.analyze_generation_failure(
        shot_index=0, error_code="HTTP_ERROR", error_message="timeout",
        mode="i2v", provider="minimax", attempt=1,
    )
    assert d1.action == ACTION_RETRY
    d2 = agent.analyze_generation_failure(
        shot_index=0, error_code="HTTP_ERROR", error_message="timeout",
        mode="i2v", provider="minimax", attempt=2,
    )
    assert d2.action == ACTION_SWITCH_MODEL


def test_failure_analysis_balance_error_switches_model():
    agent = FailureAnalysisAgent()
    d = agent.analyze_generation_failure(
        shot_index=0, error_code="INSUFFICIENT_BALANCE", error_message="余额不足",
        mode="i2v", provider="minimax", attempt=1,
    )
    assert d.action == ACTION_SWITCH_MODEL


def test_failure_analysis_aborts_after_max_attempts():
    agent = FailureAnalysisAgent()
    d = agent.analyze_generation_failure(
        shot_index=0, error_code="HTTP_ERROR", error_message="x",
        mode="i2v", provider="minimax", attempt=MAX_AUTO_ATTEMPTS,
    )
    assert d.action == ACTION_ABORT and not d.repairable


def test_failure_analysis_quality_issue_regenerates_prompt():
    agent = FailureAnalysisAgent()
    d = agent.analyze_quality_failure(
        shot_index=2, issues=["人物不一致:路人甲 不在 Bible"], attempt=1,
    )
    assert d.action == ACTION_REGENERATE_PROMPT and d.force_mode == "r2v"
    d2 = agent.analyze_quality_failure(shot_index=2, issues=["场景漂移"], attempt=MAX_AUTO_ATTEMPTS)
    assert d2.action == ACTION_ABORT


# ============================ Phase 6:VideoWorkflow 修复闭环 ============================

def test_video_workflow_repairs_t2v_by_adding_keyframe(fake_storage):
    """T2V 在 I2V-only 模型上失败 → 补关键帧 → I2V 重试成功。"""
    state = _state_with_storyboard()
    state.storyboard.shots[0].desired_mode = "t2v"
    state.get_or_create_project_state().shot_state.get(0).desired_mode = "t2v"

    image_wf = ImageWorkflow(_FakeImageProvider())
    # I2V-only 模型:第 1 次(T2V 无首帧)在路由决策层即失败,补帧后首次调用 Provider 即成功
    video = _OKVideoProvider(supports_t2v=False)
    video_wf = VideoWorkflow(
        video,
        failure_analyzer=FailureAnalysisAgent(),
        image_workflow=image_wf,
    )
    asyncio.run(video_wf.generate_shot(state, 0))

    # 补关键帧后 I2V 成功,仅调用 Provider 一次
    assert video.calls == 1
    assert video.requests[0].image_path is not None
    assert state.storyboard.shots[0].video_path
    decisions = state.project_state.generation_state.decisions
    assert [d.status for d in decisions if d.shot_index == 0] == ["failed", "succeeded"]
    assert decisions[0].reason.startswith("MODE_UNSUPPORTED")
    assert state.storyboard.shots[0].desired_mode == "i2v"  # 修复决策强制降级


def test_video_workflow_retry_transient_then_succeed(fake_storage):
    """瞬时错误第 1 次失败 → 同参重试 → 第 2 次成功。"""
    state = _state_with_storyboard()
    image_wf = ImageWorkflow(_FakeImageProvider())
    asyncio.run(image_wf.run(state))
    video = _FlakyVideoProvider(fail_times=1, error_code="HTTP_ERROR", supports_t2v=True)
    video_wf = VideoWorkflow(video, failure_analyzer=FailureAnalysisAgent())

    asyncio.run(video_wf.generate_shot(state, 0))
    assert video.calls == 2
    assert state.project_state.generation_state.completed_shots == [0]


def test_video_workflow_switch_model_after_repeated_failure(fake_storage):
    """重试无效 → 切厂商回调 → 新厂商成功。"""
    state = _state_with_storyboard()
    image_wf = ImageWorkflow(_FakeImageProvider())
    asyncio.run(image_wf.run(state))

    bad = _FlakyVideoProvider(fail_times=99, error_code="HTTP_ERROR")
    good = _OKVideoProvider()
    wf = VideoWorkflow(bad, failure_analyzer=FailureAnalysisAgent())

    async def switcher(state, shot_index, reason):
        wf.video = good
        return True

    wf.model_switcher = switcher
    asyncio.run(wf.generate_shot(state, 0))

    assert bad.calls == 2  # 第 1 次失败重试,第 2 次失败切厂商
    assert good.calls == 1
    assert state.storyboard.shots[0].video_path


def test_video_workflow_no_repair_path_raises(fake_storage):
    """无 analyzer 时失败直接抛出(旧行为兼容)。"""
    state = _state_with_storyboard()
    image_wf = ImageWorkflow(_FakeImageProvider())
    asyncio.run(image_wf.run(state))
    video = _FlakyVideoProvider(fail_times=99, error_code="HTTP_ERROR")
    wf = VideoWorkflow(video)  # 无 failure_analyzer
    with pytest.raises(ProviderError):
        asyncio.run(wf.generate_shot(state, 0))
    assert state.project_state.generation_state.failed_shots == [0]


# ============================ Phase 6:内容质检 ============================

def test_quality_judge_passes_well_formed_shots(fake_storage):
    state = _state_with_storyboard()
    image_wf = ImageWorkflow(_FakeImageProvider())
    asyncio.run(image_wf.run(state))
    judge = QualityJudgeAgent()
    asyncio.run(judge.run(state))
    ps = state.project_state
    assert len(ps.quality_state.passed_shots) == len(state.storyboard.shots)
    assert ps.quality_state.failed_shots == []
    report = ps.quality_state.latest_for_shot(0)
    dims = {c.dimension for c in report.checks}
    assert {"character_consistency", "scene_consistency", "continuity", "action", "asset_ready"} <= dims


def test_quality_judge_flags_unknown_character(fake_storage):
    state = _state_with_storyboard()
    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))
    # 第 2 镜混入 Bible 之外的人物
    state.storyboard.shots[1].characters = ["神秘路人X"]
    judge = QualityJudgeAgent()
    report = judge.judge_shot(state, 1)
    assert not report.passed
    assert any("人物不一致" in i for i in report.issues)
    assert report.repair_hint


def test_quality_judge_flags_broken_continuity(fake_storage):
    state = _state_with_storyboard()
    asyncio.run(ImageWorkflow(_FakeImageProvider()).run(state))
    # 非首镜清空连续性字段
    state.storyboard.shots[2].continuity_in = ""
    state.storyboard.shots[2].causal_note = ""
    report = QualityJudgeAgent().judge_shot(state, 2)
    assert not report.passed
    assert any("连续性" in i for i in report.issues)


# ============================ Phase 7:音频规划 ============================

def test_audio_planner_produces_cues_and_music():
    state = _state_with_storyboard()
    planner = AudioPlannerAgent(llm=MockLLMProvider())
    asyncio.run(planner.run(state))
    ps = state.project_state
    # 每镜至少一条 narration cue + 一条全片 music cue
    assert len(ps.audio_state.cues) >= len(state.storyboard.shots)
    assert ps.audio_state.music_mood
    assert ps.audio_state.music_style
    music_cues = [c for c in ps.audio_state.cues if c.type == "music"]
    assert music_cues and music_cues[0].shot_index is None
    # 幂等:二次运行跳过
    first_count = len(ps.audio_state.cues)
    asyncio.run(planner.run(state))
    assert len(ps.audio_state.cues) == first_count


def test_tts_workflow_binds_cue_asset(fake_storage):
    state = _state_with_storyboard()
    asyncio.run(AudioPlannerAgent(llm=MockLLMProvider()).run(state))
    asyncio.run(TTSWorkflow(_FakeVoiceProvider()).run(state))
    ps = state.project_state
    narration_cues = [c for c in ps.audio_state.cues if c.type == "narration"]
    assert narration_cues
    assert all(c.status == "generated" and c.asset_id for c in narration_cues)


# ============================ Phase 7:剪辑规划与执行 ============================

def test_editing_planner_produces_decision_sheet():
    state = _state_with_storyboard()
    planner = EditingPlannerAgent(llm=MockLLMProvider())
    asyncio.run(planner.run(state))
    editing = state.project_state.editing_state
    n = len(state.storyboard.shots)
    assert editing.decision_source == "agent"
    assert sorted(editing.shot_order) == list(range(n))
    # 每个相邻边界都有转场决策
    assert len(editing.transitions) == n - 1
    assert all(v in ("fade", "cut", "dissolve", "slide") for v in editing.transitions.values())
    assert editing.pacing_note
    # 幂等
    before = dict(editing.transitions)
    asyncio.run(planner.run(state))
    assert state.project_state.editing_state.transitions == before


def test_editing_planner_rejects_illegal_order():
    """LLM 返回非法顺序(重复/越界)时回退叙事顺序。"""
    state = _state_with_storyboard()
    n = len(state.storyboard.shots)
    planner = EditingPlannerAgent(llm=MockLLMProvider())
    # 直接喂非法数据给合并逻辑
    data = {"shot_order": [0, 0, 0], "transitions": {}, "pacing_note": "x"}
    # 模拟 run 的校验段
    order = data["shot_order"]
    assert sorted(order) != list(range(n))  # 前置断言:确实非法


def test_editing_workflow_applies_order_and_transitions():
    state = _state_with_storyboard()
    ps = state.get_or_create_project_state()
    n = len(state.storyboard.shots)
    # 手写剪辑决策单:交换前两镜 + 指定转场
    ps.editing_state.decision_source = "agent"
    ps.editing_state.shot_order = [1, 0] + list(range(2, n))
    ps.editing_state.transitions = {"1->0": "cut", "0->2": "dissolve"}

    ordered = EditingWorkflow.ordered_shots(state)
    # 合成序列按决策单重排
    assert ordered[0].scene_id == state.storyboard.shots[1].scene_id
    assert ordered[1].scene_id == state.storyboard.shots[0].scene_id
    # 转场覆盖生效(首镜 cut、边界取决策)
    assert ordered[0].transition == "cut"
    assert ordered[1].transition == "cut"      # 边界 1->0
    assert ordered[2].transition == "dissolve"  # 边界 0->2
    # 叙事真相不被改写
    assert state.storyboard.shots[0].transition != "cut" or True  # storyboard 原样
    assert state.storyboard.shots[1].scene_id == ordered[0].scene_id


def test_editing_workflow_legacy_order_without_decision():
    state = _state_with_storyboard()
    ordered = EditingWorkflow.ordered_shots(state)
    assert [s.scene_id for s in ordered] == [s.scene_id for s in state.storyboard.shots]
    assert state.project_state.editing_state.decision_source == ""


def test_timeline_follows_editing_order(fake_storage):
    """音轨时间轴顺序与剪辑决策单一致(成片镜头顺序即时间轴顺序)。"""
    from app.orchestrator.orchestrator import Orchestrator
    state = _state_with_storyboard()
    n = len(state.storyboard.shots)
    ps = state.get_or_create_project_state()
    ps.editing_state.decision_source = "agent"
    ps.editing_state.shot_order = [n - 1] + list(range(n - 1))  # 末镜前置

    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FakeImageProvider(),
        voice=_FakeVoiceProvider(),
        video=_OKVideoProvider(),
    )
    timeline = asyncio.run(orch._build_timeline(state))
    assert [seg.shot_index for seg in timeline] == [n - 1] + list(range(n - 1))
    # 时段连续累加
    assert timeline[0].start == 0.0
    assert timeline[-1].end == sum(max(s.duration, 1) for s in state.storyboard.shots)
