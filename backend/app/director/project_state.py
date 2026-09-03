"""ProjectState:作品级状态(AI Director 的记忆)。

回答 Agent 在每个决策点需要知道的问题:
- "我们现在拍到哪了?"            → shot_state / generation_state
- "人物现在是什么状态?"           → character_state(档案 + 跨镜头当前状态)
- "上一镜头发生了什么?"           → shot_state 的 continuity_out / 因果链
- "这个场景现在是什么天气/光线?"  → world_state / scene_state
- "下一镜头需要继承什么?"         → shot_state 的 continuity_in
- "这个镜头生成得合不合格?"       → quality_state
- "素材都在哪、属于谁?"           → asset_state

与 VideoGenerationState 的分工:
- state.script / storyboard / prompt_engineering_result 是"阶段产物"(artifact)
- ProjectState 是"对作品的结构化理解与跨镜头状态",由决策类 Agent 维护,
  Workflow 与 Model Router 读取消费。

持久化:作为 VideoGenerationState.project_state 单字段随 state_json 落库,
所有字段带默认值,旧任务(无此字段)反序列化后为默认空状态。
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..schemas.bible import CharacterBible, StyleBible, WorldBible


# ============================ project_info ============================

class ProjectInfo(BaseModel):
    """作品基础信息。"""

    project_id: Optional[str] = Field(None, description="关联项目 ID(系列作品共用设定)")
    title: str = Field("", description="作品标题")
    genre: str = Field("", description="内容类型/题材:虐恋短剧/古风喜剧/产品广告")
    duration_target: int = Field(30, description="目标成片时长(秒)")
    aspect_ratio: str = Field("9:16", description="画幅比例")
    language: str = Field("zh", description="对白语言")


# ============================ story_state ============================

class StoryBeat(BaseModel):
    """故事节拍:开端/关系建立/误会产生/冲突升级/高潮/结局。"""

    beat_id: str = Field(..., description="节拍 ID,如 beat_01")
    name: str = Field(..., description="节拍名称:开端/冲突升级/高潮/结局")
    summary: str = Field("", description="本节拍发生了什么(因果描述)")
    emotion: str = Field("", description="本节拍情绪基调")
    scene_refs: List[int] = Field(default_factory=list, description="关联脚本场景编号")


class CharacterArc(BaseModel):
    """人物弧光:人物从故事起点到终点的状态变化。"""

    character_id: str = Field(..., description="人物 ID")
    arc_summary: str = Field("", description="弧光概述:这个人经历了什么变化")
    start_state: str = Field("", description="故事开始时的状态(心境/处境/关系)")
    end_state: str = Field("", description="故事结束时的状态")


class StoryState(BaseModel):
    """故事理解与规划状态(StoryPlannerAgent 维护)。"""

    theme: str = Field("", description="故事主题")
    logline: str = Field("", description="一句话故事(logline)")
    core_conflict: str = Field("", description="核心冲突")
    ending_tone: str = Field("", description="结局基调:团圆/遗憾/反转/开放式")
    beats: List[StoryBeat] = Field(default_factory=list, description="故事节拍链(按叙事顺序)")
    character_arcs: List[CharacterArc] = Field(default_factory=list, description="人物弧光")


# ============================ character_state ============================

class CharacterState(BaseModel):
    """人物设定与跨镜头状态(CharacterAgent 维护)。"""

    bibles: List[CharacterBible] = Field(default_factory=list, description="全部人物档案")
    # character_id -> 该人物"当前"状态(随镜头推进演进):服装/情绪/位置/伤势/持有物
    current_status: Dict[str, str] = Field(
        default_factory=dict, description="人物当前状态摘要,key=character_id"
    )

    def upsert_bible(self, bible: CharacterBible) -> None:
        """新增或按 character_id 更新人物档案。"""
        for i, existing in enumerate(self.bibles):
            if existing.character_id == bible.character_id:
                self.bibles[i] = bible
                return
        self.bibles.append(bible)

    def get_bible(self, character_id: str = "", name: str = "") -> Optional[CharacterBible]:
        """按 ID 或姓名查人物档案。"""
        for b in self.bibles:
            if character_id and b.character_id == character_id:
                return b
            if name and b.name == name:
                return b
        return None

    def find_by_name(self, name: str) -> Optional[CharacterBible]:
        return self.get_bible(name=name)

    def set_status(self, character_id: str, status: str) -> None:
        """更新人物当前状态(每镜拍完后由 Agent 写入)。"""
        self.current_status[character_id] = status

    def reference_assets_for(self, names: List[str]) -> List[str]:
        """给定出场人物名,汇总其角色参考图资产 ID(供 R2V/I2V 一致性使用)。"""
        ids: List[str] = []
        for name in names:
            bible = self.get_bible(name=name)
            if bible:
                ids.extend(bible.reference_asset_ids)
        # 去重保序
        seen: set[str] = set()
        return [a for a in ids if not (a in seen or seen.add(a))]


# ============================ world_state / style_state ============================

class WorldState(BaseModel):
    """世界观与场景设定状态(WorldAgent 维护)。"""

    bible: Optional[WorldBible] = Field(None, description="World Bible")


class StyleState(BaseModel):
    """视觉风格设定状态(WorldAgent 维护)。"""

    bible: Optional[StyleBible] = Field(None, description="Style Bible")


# ============================ scene_state ============================

class SceneStateEntry(BaseModel):
    """单个场景的跨镜头连续性状态。"""

    scene_id: int = Field(..., description="脚本场景编号(对齐 ScriptScene.scene_id)")
    name: str = Field("", description="场景名称")
    location: str = Field("", description="地点")
    time_of_day: str = Field("", description="时段")
    weather: str = Field("", description="天气")
    lighting: str = Field("", description="光线")
    characters: List[str] = Field(default_factory=list, description="本场景出场人物")
    summary: str = Field("", description="本场景戏剧内容摘要")
    shot_count: int = Field(0, description="本场景镜头数")
    status: str = Field("planned", description="planned / shooting / done")


class SceneState(BaseModel):
    """场景级状态汇总。"""

    scenes: List[SceneStateEntry] = Field(default_factory=list)

    def upsert(self, entry: SceneStateEntry) -> None:
        for i, existing in enumerate(self.scenes):
            if existing.scene_id == entry.scene_id:
                self.scenes[i] = entry
                return
        self.scenes.append(entry)

    def get(self, scene_id: int) -> Optional[SceneStateEntry]:
        for s in self.scenes:
            if s.scene_id == scene_id:
                return s
        return None


# ============================ shot_state ============================

class ShotStateEntry(BaseModel):
    """单个镜头的规划与连续性状态(ShotPlannerAgent 维护)。

    镜头不是独立 prompt,而是叙事链上的一环:
    - continuity_in / prev_shot:本镜继承上一镜的什么状态
    - continuity_out / next_shot:本镜结束后留给下一镜什么状态
    - causal_note:为什么会发生这个镜头(叙事因果)
    """

    shot_index: int = Field(..., description="镜头序号(对齐 StoryboardShot 下标)")
    scene_id: int = Field(0, description="所属场景编号")
    characters: List[str] = Field(default_factory=list, description="出场人物名")
    location: str = Field("", description="地点")
    time_of_day: str = Field("", description="时段")
    action: str = Field("", description="动作")
    emotion_start: str = Field("", description="镜头开始情绪")
    emotion_end: str = Field("", description="镜头结束情绪")
    camera: str = Field("", description="景别/机位")
    camera_motion: str = Field("", description="运镜")
    lighting: str = Field("", description="光线")
    dialogue: str = Field("", description="对白")
    sound: str = Field("", description="音效/音乐提示")
    continuity_in: str = Field("", description="继承上一镜的状态(人物姿态/情绪/道具/天气)")
    continuity_out: str = Field("", description="本镜结束后传递给下一镜的状态")
    causal_note: str = Field("", description="叙事因果:为什么本镜会发生")
    prev_shot: Optional[int] = Field(None, description="前置镜头序号")
    next_shot: Optional[int] = Field(None, description="后置镜头序号")
    ref_asset_ids: List[str] = Field(default_factory=list, description="本镜参考资产(角色参考图/首尾帧)")
    desired_mode: str = Field("", description="Agent 决策的期望生成模式: t2v/i2v/r2v/first_last")
    desired_duration: int = Field(5, description="期望镜头时长(秒)")
    status: str = Field("planned", description="planned / generating / generated / verified / failed")


class ShotState(BaseModel):
    """镜头级状态:叙事链与生成进度。"""

    shots: List[ShotStateEntry] = Field(default_factory=list)

    def upsert(self, entry: ShotStateEntry) -> None:
        for i, existing in enumerate(self.shots):
            if existing.shot_index == entry.shot_index:
                self.shots[i] = entry
                return
        self.shots.append(entry)

    def get(self, shot_index: int) -> Optional[ShotStateEntry]:
        for s in self.shots:
            if s.shot_index == shot_index:
                return s
        return None

    def link_chain(self) -> None:
        """按 shot_index 排序后补全 prev/next 指针(因果链闭合)。"""
        ordered = sorted(self.shots, key=lambda s: s.shot_index)
        for i, shot in enumerate(ordered):
            shot.prev_shot = ordered[i - 1].shot_index if i > 0 else None
            shot.next_shot = ordered[i + 1].shot_index if i < len(ordered) - 1 else None
        self.shots = ordered

    def chain_closed(self) -> bool:
        """校验因果链:排序后首镜无前置、末镜无后置、中间双向连通。"""
        if not self.shots:
            return True
        ordered = sorted(self.shots, key=lambda s: s.shot_index)
        for i, shot in enumerate(ordered):
            expect_prev = ordered[i - 1].shot_index if i > 0 else None
            expect_next = ordered[i + 1].shot_index if i < len(ordered) - 1 else None
            if shot.prev_shot != expect_prev or shot.next_shot != expect_next:
                return False
        return True


# ============================ asset_state ============================

class AssetEntry(BaseModel):
    """一份生成/上传素材的登记信息。"""

    asset_id: str = Field(..., description="资产稳定 ID")
    type: str = Field(..., description="资产类型: image/video/audio/music/sfx/reference")
    path: str = Field(..., description="文件路径")
    shot_index: Optional[int] = Field(None, description="归属镜头(成片素材)")
    character_id: Optional[str] = Field(None, description="归属人物(角色参考图)")
    source_provider: str = Field("", description="产出该资产的 provider/model")
    metadata: Dict[str, str] = Field(default_factory=dict, description="附加元数据")


class AssetState(BaseModel):
    """素材资产登记(生成产物的台账)。"""

    assets: List[AssetEntry] = Field(default_factory=list)

    def add(self, entry: AssetEntry) -> None:
        for i, existing in enumerate(self.assets):
            if existing.asset_id == entry.asset_id:
                self.assets[i] = entry
                return
        self.assets.append(entry)

    def for_shot(self, shot_index: int) -> List[AssetEntry]:
        return [a for a in self.assets if a.shot_index == shot_index]

    def character_references(self, character_id: str) -> List[AssetEntry]:
        return [a for a in self.assets if a.character_id == character_id and a.type in ("image", "reference")]


# ============================ generation_state ============================

class GenerationDecision(BaseModel):
    """单镜头单次生成的路由决策与执行记录(Model Router 决策,Workflow 执行)。"""

    shot_index: int
    provider: str = Field("", description="选定 provider: minimax/qwen/comfy/...")
    model: str = Field("", description="具体模型名")
    mode: str = Field("", description="生成模式: t2v/i2v/r2v/first_last")
    reference_asset_ids: List[str] = Field(default_factory=list)
    attempt: int = Field(1, description="第几次尝试(质检失败重试递增)")
    reason: str = Field("", description="路由理由(为什么选这个模式/厂商)")
    status: str = Field("pending", description="pending / running / succeeded / failed")


class GenerationState(BaseModel):
    """生成执行状态:路由决策台账与进度。"""

    current_stage: str = Field("", description="当前生成阶段: image/video/audio/editing")
    decisions: List[GenerationDecision] = Field(default_factory=list)
    completed_shots: List[int] = Field(default_factory=list)
    failed_shots: List[int] = Field(default_factory=list)

    def record_decision(self, decision: GenerationDecision) -> None:
        self.decisions.append(decision)

    def latest_decision(self, shot_index: int) -> Optional[GenerationDecision]:
        for d in reversed(self.decisions):
            if d.shot_index == shot_index:
                return d
        return None

    def mark_shot(self, shot_index: int, *, ok: bool) -> None:
        bucket = self.completed_shots if ok else self.failed_shots
        other = self.failed_shots if ok else self.completed_shots
        if shot_index not in bucket:
            bucket.append(shot_index)
        if shot_index in other:
            other.remove(shot_index)


# ============================ audio_state ============================

class AudioCue(BaseModel):
    """单个音频规划点:旁白/对白/音乐/音效(AudioPlannerAgent 规划,音频 Workflow 执行)。"""

    shot_index: Optional[int] = Field(None, description="归属镜头(全片音乐可为空)")
    type: str = Field(..., description="narration(旁白) / dialogue(对白) / music(音乐) / sfx(音效)")
    text: str = Field("", description="旁白/对白文本")
    description: str = Field("", description="音乐/音效描述(风格/情绪/具体音效)")
    emotion: str = Field("", description="演绎情绪")
    asset_id: Optional[str] = Field(None, description="生成后的音频资产 ID")
    status: str = Field("planned", description="planned / generated / skipped")


class AudioState(BaseModel):
    """音频规划与制作状态。"""

    cues: List[AudioCue] = Field(default_factory=list)
    music_mood: str = Field("", description="全片音乐情绪基调(不再写死 light)")
    music_style: str = Field("", description="音乐风格")
    bgm_asset_id: Optional[str] = Field(None, description="背景音乐资产 ID")

    def add_cue(self, cue: AudioCue) -> None:
        self.cues.append(cue)

    def cues_for_shot(self, shot_index: int) -> List[AudioCue]:
        return [c for c in self.cues if c.shot_index == shot_index]


# ============================ editing_state ============================

class EditingState(BaseModel):
    """剪辑决策状态(Agent 决策顺序/时长/转场/节奏,Editing Workflow 执行)。"""

    shot_order: List[int] = Field(default_factory=list, description="镜头顺序(默认叙事顺序)")
    transitions: Dict[str, str] = Field(
        default_factory=dict, description="转场决策: key='{from_shot}->{to_shot}', value=fade/cut/dissolve"
    )
    pacing_note: str = Field("", description="节奏决策:哪里快切/哪里留白")
    subtitle_enabled: bool = Field(True, description="是否烧录字幕")
    decision_source: str = Field("", description="决策来源: agent(Agent 决策单) / legacy(旧默认逻辑)")
    final_video_asset_id: Optional[str] = Field(None, description="成片资产 ID")


# ============================ quality_state ============================

class QualityCheck(BaseModel):
    """单个质检维度的结论。"""

    dimension: str = Field(
        ..., description="质检维度: character_consistency/scene_consistency/action/continuity/story"
    )
    passed: bool = True
    note: str = Field("", description="评判说明")


class QualityReport(BaseModel):
    """单镜头单次质检报告(QualityJudgeAgent 产出)。"""

    shot_index: int
    attempt: int = Field(1, description="对应第几次生成尝试")
    passed: bool = Field(True, description="总体是否通过")
    checks: List[QualityCheck] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list, description="发现的问题清单")
    judge_note: str = Field("", description="评判总结")
    repair_hint: str = Field("", description="给 FailureAnalysisAgent 的修复方向提示")


class QualityState(BaseModel):
    """内容级质检状态(区别于 state.quality_report 的纯技术校验)。"""

    reports: List[QualityReport] = Field(default_factory=list)
    passed_shots: List[int] = Field(default_factory=list)
    failed_shots: List[int] = Field(default_factory=list)

    def add_report(self, report: QualityReport) -> None:
        self.reports.append(report)
        if report.passed:
            if report.shot_index not in self.passed_shots:
                self.passed_shots.append(report.shot_index)
            if report.shot_index in self.failed_shots:
                self.failed_shots.remove(report.shot_index)
        else:
            if report.shot_index not in self.failed_shots:
                self.failed_shots.append(report.shot_index)

    def latest_for_shot(self, shot_index: int) -> Optional[QualityReport]:
        for r in reversed(self.reports):
            if r.shot_index == shot_index:
                return r
        return None


# ============================ ProjectState 根 ============================

class ProjectState(BaseModel):
    """作品级状态根:十二态聚合,AI Director 全程维护。"""

    project_info: ProjectInfo = Field(default_factory=ProjectInfo)
    story_state: StoryState = Field(default_factory=StoryState)
    character_state: CharacterState = Field(default_factory=CharacterState)
    world_state: WorldState = Field(default_factory=WorldState)
    style_state: StyleState = Field(default_factory=StyleState)
    scene_state: SceneState = Field(default_factory=SceneState)
    shot_state: ShotState = Field(default_factory=ShotState)
    asset_state: AssetState = Field(default_factory=AssetState)
    generation_state: GenerationState = Field(default_factory=GenerationState)
    audio_state: AudioState = Field(default_factory=AudioState)
    editing_state: EditingState = Field(default_factory=EditingState)
    quality_state: QualityState = Field(default_factory=QualityState)
    updated_at: float = Field(default_factory=time.time)

    def touch(self) -> None:
        """标记状态更新(由维护它的 Agent 在写入后调用)。"""
        self.updated_at = time.time()

    def progress_summary(self) -> dict:
        """生成进度摘要:回答"我们现在拍到哪了"。"""
        total = len(self.shot_state.shots)
        return {
            "title": self.project_info.title,
            "total_shots": total,
            "generated_shots": len(self.generation_state.completed_shots),
            "verified_shots": len(self.quality_state.passed_shots),
            "failed_shots": list(self.quality_state.failed_shots),
            "characters": [b.name for b in self.character_state.bibles],
            "current_stage": self.generation_state.current_stage,
            "final_video": self.editing_state.final_video_asset_id,
        }


__all__ = [
    "ProjectInfo",
    "StoryBeat", "CharacterArc", "StoryState",
    "CharacterState",
    "WorldState", "StyleState",
    "SceneStateEntry", "SceneState",
    "ShotStateEntry", "ShotState",
    "AssetEntry", "AssetState",
    "GenerationDecision", "GenerationState",
    "AudioCue", "AudioState",
    "EditingState",
    "QualityCheck", "QualityReport", "QualityState",
    "ProjectState",
]
