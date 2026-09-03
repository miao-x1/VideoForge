"""Phase 3 测试:作品级规划 Agent(故事/人物/世界观)与 ScriptAgent 上下文注入。

覆盖:
- StoryPlannerAgent:节拍链 + 人物弧光 + project_info,幂等
- CharacterAgent:Character Bible 与 requirement 人物对齐,视觉关键词兜底,幂等
- WorldAgent:World/Style Bible,场景条目兜底
- ScriptAgent:planning 后脚本上下文携带 story/characters/world/style_bible
- Orchestrator._run_planning:阶段集成,project_state 落库持久化
"""
import asyncio

import pytest

from app.agents.character_agent import CharacterAgent
from app.agents.script_agent import ScriptAgent
from app.agents.story_planner_agent import StoryPlannerAgent
from app.agents.world_agent import WorldAgent
from app.models.state import VideoGenerationState
from app.orchestrator.orchestrator import Orchestrator
from app.providers.image.base import ImageProvider
from app.providers.llm.mock_llm import MockLLMProvider
from app.providers.music.base import MusicProvider
from app.providers.video.base import ModelRequest, ModelResponse, VideoModelProvider
from app.providers.voice.base import VoiceProvider


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "enable_mock_providers", True)


def _state_with_requirement() -> VideoGenerationState:
    """经 RequirementAgent(mock)产出 requirement + creative_intent 的状态。"""
    from app.agents.requirement_agent import RequirementAgent

    state = VideoGenerationState(
        user_input="我想做一个30秒虐恋短剧",
        duration=30,
        style="古风虐恋",
    )
    agent = RequirementAgent(llm=MockLLMProvider())
    asyncio.run(agent.run(state))
    assert state.requirement is not None
    return state


# ---------------------------- StoryPlanner ----------------------------

def test_story_planner_produces_beats_and_arcs():
    state = _state_with_requirement()
    agent = StoryPlannerAgent(llm=MockLLMProvider())
    asyncio.run(agent.run(state))

    ps = state.project_state
    assert ps is not None
    assert len(ps.story_state.beats) == 5
    # 节拍因果链:开端 → ... → 结局
    assert ps.story_state.beats[0].name == "开端"
    assert ps.story_state.beats[-1].name == "结局"
    assert ps.story_state.core_conflict
    # 弧光与 requirement 人物顺序对齐(character_001/002)
    req_names = [c.name for c in state.requirement.characters]
    arc_names_ids = [a.character_id for a in ps.story_state.character_arcs]
    assert arc_names_ids == [f"character_{i + 1:03d}" for i in range(len(req_names))]
    # project_info 填充
    assert ps.project_info.genre == state.requirement.genre
    assert ps.project_info.duration_target == 30


def test_story_planner_idempotent():
    state = _state_with_requirement()
    agent = StoryPlannerAgent(llm=MockLLMProvider())
    asyncio.run(agent.run(state))
    beats_after_first = len(state.project_state.story_state.beats)
    # 第二次运行应跳过(幂等),不重复
    asyncio.run(agent.run(state))
    assert len(state.project_state.story_state.beats) == beats_after_first
    # force=True 允许重建
    asyncio.run(agent.run(state, force=True))
    assert len(state.project_state.story_state.beats) == beats_after_first


# ---------------------------- CharacterAgent ----------------------------

def test_character_bible_aligned_with_requirement():
    state = _state_with_requirement()
    asyncio.run(StoryPlannerAgent(llm=MockLLMProvider()).run(state))
    asyncio.run(CharacterAgent(llm=MockLLMProvider()).run(state))

    ps = state.project_state
    req_names = [c.name for c in state.requirement.characters]
    bible_names = [b.name for b in ps.character_state.bibles]
    assert bible_names == req_names  # 人数与姓名严格对齐
    assert [b.character_id for b in ps.character_state.bibles] == [
        f"character_{i + 1:03d}" for i in range(len(req_names))
    ]
    for b in ps.character_state.bibles:
        assert b.visual_keywords  # 视觉一致性关键词不为空(LLM 或兜底)
    # 弧光 ID 与 Bible ID 可互相引用
    arc_ids = {a.character_id for a in ps.story_state.character_arcs}
    bible_ids = {b.character_id for b in ps.character_state.bibles}
    assert arc_ids == bible_ids


def test_character_agent_idempotent():
    state = _state_with_requirement()
    agent = CharacterAgent(llm=MockLLMProvider())
    asyncio.run(StoryPlannerAgent(llm=MockLLMProvider()).run(state))
    asyncio.run(agent.run(state))
    n = len(state.project_state.character_state.bibles)
    asyncio.run(agent.run(state))
    assert len(state.project_state.character_state.bibles) == n


# ---------------------------- WorldAgent ----------------------------

def test_world_and_style_bible():
    state = _state_with_requirement()
    asyncio.run(WorldAgent(llm=MockLLMProvider()).run(state))
    ps = state.project_state
    assert ps.world_state.bible is not None
    assert ps.style_state.bible is not None
    # 场景条目与 requirement.scenes 对齐(LLM 或兜底)
    assert len(ps.world_state.bible.scenes) == len(state.requirement.scenes)
    assert ps.world_state.bible.scenes[0].scene_key == "scene_01"
    assert ps.style_state.bible.visual_style  # 风格非空


# ---------------------------- ScriptAgent 上下文 ----------------------------

class _SpyLLM(MockLLMProvider):
    """记录每次 generate 的 task 与 context。"""

    def __init__(self):
        self.calls = []

    async def generate(self, *, task, context):
        self.calls.append({"task": task, "context": context})
        return await super().generate(task=task, context=context)


def test_script_agent_consumes_project_state():
    state = _state_with_requirement()
    spy = _SpyLLM()
    asyncio.run(StoryPlannerAgent(llm=spy).run(state))
    asyncio.run(CharacterAgent(llm=spy).run(state))
    asyncio.run(WorldAgent(llm=spy).run(state))
    asyncio.run(ScriptAgent(llm=spy).run(state))

    script_call = [c for c in spy.calls if c["task"] == "script"][0]
    ctx = script_call["context"]
    assert "story" in ctx and ctx["story"]["beats"]
    assert "characters" in ctx and ctx["characters"]
    assert "world" in ctx and "scenes" in ctx["world"]
    assert "style_bible" in ctx and ctx["style_bible"]["visual_style"]
    # 人物档案姓名与脚本人物一致
    assert state.script is not None
    assert state.script.scenes  # 脚本正常产出


def test_script_agent_without_planning_still_works():
    """无 project_state 的旧链路:ScriptAgent 不报错(向后兼容)。"""
    state = _state_with_requirement()
    state.project_state = None
    asyncio.run(ScriptAgent(llm=MockLLMProvider()).run(state))
    assert state.script is not None and state.script.scenes


# ---------------------------- Orchestrator 集成 ----------------------------

class _FakeImageProvider(ImageProvider):
    async def generate(self, *, prompt, save_path, width=1280, height=720):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


class _FakeVoiceProvider(VoiceProvider):
    async def generate(self, *, text, save_path, duration):
        from pathlib import Path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(b"fake")
        return save_path


class _FakeMusicProvider(MusicProvider):
    async def generate(self, *, save_path, duration, mood="light"):
        from pathlib import Path
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
        from pathlib import Path
        Path(request.save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(request.save_path).write_bytes(b"fake")
        return ModelResponse(video_path=request.save_path, duration=request.duration, model=self.name)


def test_orchestrator_planning_stage(fake_storage):
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=_FakeImageProvider(),
        voice=_FakeVoiceProvider(),
        music=_FakeMusicProvider(),
        video=_FakeVideoProvider(),
    )
    state = _state_with_requirement()
    asyncio.run(orch._run_planning(state))

    ps = state.project_state
    assert ps is not None
    assert ps.story_state.beats and ps.character_state.bibles
    assert ps.world_state.bible is not None and ps.style_state.bible is not None
    # 阶段日志:故事结构/人物/世界观三条进度
    messages = [log.message for log in state.logs]
    assert any("故事结构" in m for m in messages)
    assert any("人物设定" in m for m in messages)
    assert any("世界观" in m for m in messages)
