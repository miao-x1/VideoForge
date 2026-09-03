"""Phase 2 地基测试:ProjectState 十二态 + Bible schemas + 旧任务兼容。

覆盖:
- Bible(Character/World/Style)数据结构
- ProjectState 十二态默认构造与 helper 方法
- 镜头因果链 link_chain / chain_closed
- VideoGenerationState 挂载 project_state:幂等初始化、JSON 往返、旧 state_json 兼容
"""
from app.director.project_state import (
    AssetEntry,
    GenerationDecision,
    ProjectState,
    QualityReport,
    ShotStateEntry,
)
from app.models.state import VideoGenerationState
from app.schemas.bible import CharacterBible, CharacterRelation, StyleBible, WorldBible


# ---------------------------- Bible schemas ----------------------------

def test_character_bible_full_fields():
    bible = CharacterBible(
        character_id="character_001",
        name="林晚",
        age="约二十岁",
        gender="女",
        identity="江南药铺掌柜之女",
        personality="外柔内刚",
        appearance="鹅蛋脸,眉间有一颗小痣",
        hairstyle="黑色长发,半束发髻",
        clothing="素青色襦裙",
        body_type="纤细",
        speech_style="语速平缓,声线温柔",
        emotion_traits="隐忍,情绪不外露",
        relations=[CharacterRelation(target_name="沈砚", relation="恋人", description="因误会分离")],
        background="幼年随父学医",
        visual_keywords=["素青色襦裙", "半束发髻", "眉间小痣"],
        reference_asset_ids=["asset_ref_1"],
    )
    assert bible.character_id == "character_001"
    assert bible.relations[0].target_name == "沈砚"
    assert bible.status == "active"


def test_world_and_style_bible_defaults():
    world = WorldBible(era="古代", region="江南", weather_base="阴雨")
    style = StyleBible(visual_style="电影感", color_palette="冷青灰", saturation="低饱和")
    assert world.scenes == []
    assert style.negative_keywords == []
    assert world.era == "古代" and style.visual_style == "电影感"


# ---------------------------- ProjectState 十二态 ----------------------------

def test_project_state_has_twelve_states():
    ps = ProjectState()
    for attr in [
        "project_info", "story_state", "character_state", "world_state", "style_state",
        "scene_state", "shot_state", "asset_state", "generation_state",
        "audio_state", "editing_state", "quality_state",
    ]:
        assert getattr(ps, attr) is not None
    summary = ps.progress_summary()
    assert summary["total_shots"] == 0 and summary["characters"] == []


def test_character_state_upsert_and_lookup():
    ps = ProjectState()
    bible = CharacterBible(
        character_id="character_001", name="林晚",
        reference_asset_ids=["ref_a", "ref_b"],
    )
    ps.character_state.upsert_bible(bible)
    # 同 ID 更新而非追加
    ps.character_state.upsert_bible(
        bible.model_copy(update={"clothing": "白色孝服"})
    )
    assert len(ps.character_state.bibles) == 1
    assert ps.character_state.get_bible(character_id="character_001").clothing == "白色孝服"
    assert ps.character_state.find_by_name("林晚").character_id == "character_001"
    assert ps.character_state.get_bible(name="不存在") is None

    ps.character_state.set_status("character_001", "情绪:震惊;位置:街口;持有:戒指")
    assert ps.character_state.current_status["character_001"].startswith("情绪:震惊")

    # 出场人物 → 汇总角色参考图(去重)
    ps.character_state.upsert_bible(
        CharacterBible(character_id="character_002", name="沈砚", reference_asset_ids=["ref_c", "ref_a"])
    )
    refs = ps.character_state.reference_assets_for(["林晚", "沈砚"])
    assert refs == ["ref_a", "ref_b", "ref_c"]  # ref_a 去重保序


# ---------------------------- 镜头因果链 ----------------------------

def test_shot_chain_linking():
    ps = ProjectState()
    # 乱序插入,验证 link_chain 排序闭合
    for idx in (2, 0, 1):
        ps.shot_state.upsert(ShotStateEntry(shot_index=idx, scene_id=1))
    assert not ps.shot_state.chain_closed()  # 未链接前不闭合
    ps.shot_state.link_chain()
    assert ps.shot_state.chain_closed()
    shots = sorted(ps.shot_state.shots, key=lambda s: s.shot_index)
    assert shots[0].prev_shot is None and shots[0].next_shot == 1
    assert shots[1].prev_shot == 0 and shots[1].next_shot == 2
    assert shots[2].prev_shot == 1 and shots[2].next_shot is None

    got = ps.shot_state.get(1)
    assert got is not None and got.shot_index == 1


def test_asset_generation_quality_state():
    ps = ProjectState()
    ps.asset_state.add(AssetEntry(asset_id="a1", type="image", path="/x/kf0.png", shot_index=0))
    ps.asset_state.add(AssetEntry(asset_id="a2", type="video", path="/x/v0.mp4", shot_index=0))
    ps.asset_state.add(AssetEntry(asset_id="r1", type="reference", path="/x/ref.png", character_id="character_001"))
    assert len(ps.asset_state.for_shot(0)) == 2
    assert len(ps.asset_state.character_references("character_001")) == 1

    ps.generation_state.record_decision(
        GenerationDecision(shot_index=0, provider="minimax", mode="i2v", reason="人物动作")
    )
    ps.generation_state.mark_shot(0, ok=True)
    assert ps.generation_state.completed_shots == [0]
    assert ps.generation_state.latest_decision(0).provider == "minimax"

    ps.quality_state.add_report(QualityReport(shot_index=0, passed=False, issues=["服装颜色错误"]))
    assert ps.quality_state.failed_shots == [0]
    ps.quality_state.add_report(QualityReport(shot_index=0, passed=True, attempt=2))
    assert ps.quality_state.passed_shots == [0] and ps.quality_state.failed_shots == []
    assert ps.quality_state.latest_for_shot(0).attempt == 2


# ---------------------------- 持久化与旧任务兼容 ----------------------------

def test_state_project_state_lazy_init_and_roundtrip():
    state = VideoGenerationState(user_input="我想做一个30秒虐恋短剧")
    assert state.project_state is None  # 旧行为不变

    ps = state.get_or_create_project_state()
    assert isinstance(ps, ProjectState)
    assert state.get_or_create_project_state() is ps  # 幂等

    ps.project_info.title = "虐恋测试"
    ps.character_state.upsert_bible(CharacterBible(character_id="character_001", name="女主"))
    ps.shot_state.upsert(ShotStateEntry(shot_index=0))
    ps.shot_state.link_chain()

    # JSON 落库往返
    restored = VideoGenerationState.model_validate_json(state.model_dump_json())
    assert restored.project_state is not None
    assert restored.project_state.project_info.title == "虐恋测试"
    assert restored.project_state.character_state.bibles[0].name == "女主"
    assert restored.project_state.shot_state.chain_closed()


def test_legacy_state_json_without_project_state_loads():
    """旧任务 state_json 没有 project_state 字段,反序列化必须正常(向后兼容)。"""
    legacy = VideoGenerationState(user_input="旧任务")
    payload = legacy.model_dump_json()
    assert "project_state" in payload  # 新序列化会带 null
    # 模拟旧版本持久化的 JSON(字段缺失)
    import json
    raw = json.loads(payload)
    del raw["project_state"]
    restored = VideoGenerationState.model_validate_json(json.dumps(raw))
    assert restored.project_state is None
    ps = restored.get_or_create_project_state()
    assert ps.progress_summary()["total_shots"] == 0
