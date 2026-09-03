"""StoryboardAgent(镜头规划 ShotPlanner):将脚本拆解为带因果连续性的分镜。

关键职责:
1. 视觉参数贯通:VideoSpecification 的 lighting / color / style / camera
   真实落到每个 shot 的 image_prompt / video_prompt,不丢失。
2. 连续性规划(Phase 4):消费 StoryPlanner / Character / World Agent 产出的
   Bible 与故事节拍,产出人物/地点/时段/光线/情绪/因果链字段,并把分镜
   同步为 ProjectState 的 shot_state(因果链表)与 scene_state(场景连续性)。

Agent 只做"理解与决策";关键帧/视频片段的实际生成由 Workflow 层执行。
"""
from __future__ import annotations

from ..director.project_state import SceneStateEntry, ShotStateEntry
from ..models.state import VideoGenerationState
from ..schemas.storyboard import Storyboard, StoryboardShot
from .base import BaseAgent


class StoryboardAgent(BaseAgent):
    name = "storyboard"

    async def run(self, state: VideoGenerationState, *, feedback: str | None = None) -> None:
        if state.script is None:
            raise RuntimeError("StoryboardAgent 缺少上游 script")

        context: dict = {"script": state.script.model_dump()}
        self._inject_planning_context(state, context)

        # 从 VideoSpecification 提取视觉参数指令,注入 LLM context
        # 确保 lighting / color / style 贯通到 image_prompt / video_prompt
        if state.spec:
            from .prompt_compiler import PromptCompiler
            visual_directives = PromptCompiler.compile_visual_directives(state.spec)
            if visual_directives:
                context["visual_directives"] = visual_directives

        # Decision Loop:用户重新生成时表达"哪里不满意"(如"第三镜头节奏太慢")
        if feedback:
            context["user_feedback"] = feedback

        data = await self.llm.generate(task="storyboard", context=context)
        storyboard = Storyboard(**data)

        self._post_process_suffix(state, storyboard.shots)
        state.storyboard = storyboard
        # 分镜即镜头规划决策:同步为 shot_state 因果链 + scene_state
        self._sync_project_state(state)

    async def regenerate_shot(
        self, state: VideoGenerationState, shot_index: int, *, feedback: str | None = None,
    ) -> None:
        """重新生成单个镜头:仅以该镜头对应场景为上下文,替换原镜头。

        单镜重生成必须保持连续性:新镜头继承原 scene_id/时长基准,
        替换后重建因果链指针与场景态(相邻镜头的连续性文本不被破坏)。
        """
        if state.script is None or state.storyboard is None:
            raise RuntimeError("regenerate_shot 缺少上游 script/storyboard")
        if not (0 <= shot_index < len(state.storyboard.shots)):
            raise IndexError(f"镜头索引越界: {shot_index}")

        old_shot = state.storyboard.shots[shot_index]
        # 找到该镜头对应场景(新增镜头可能无对应场景,回退到整体场景)
        scene = next(
            (s for s in state.script.scenes if s.scene_id == old_shot.scene_id),
            state.script.scenes[0] if state.script.scenes else None,
        )
        script_dict = state.script.model_dump()
        if scene is not None:
            script_dict["scenes"] = [scene.model_dump()]

        context: dict = {"script": script_dict}
        self._inject_planning_context(state, context)
        if state.spec:
            from .prompt_compiler import PromptCompiler
            visual_directives = PromptCompiler.compile_visual_directives(state.spec)
            if visual_directives:
                context["visual_directives"] = visual_directives
        # 相邻镜头上下文:LLM 只看到单场景,必须显式告知它在叙事链中的位置
        context["shot_position"] = {
            "shot_index": shot_index,
            "total_shots": len(state.storyboard.shots),
            "prev_shot": (
                {
                    "visual_description": state.storyboard.shots[shot_index - 1].visual_description,
                    "continuity_out": state.storyboard.shots[shot_index - 1].continuity_out,
                }
                if shot_index > 0 else None
            ),
            "next_shot": (
                {
                    "visual_description": state.storyboard.shots[shot_index + 1].visual_description,
                    "continuity_in": state.storyboard.shots[shot_index + 1].continuity_in,
                }
                if shot_index + 1 < len(state.storyboard.shots) else None
            ),
        }
        # Decision Loop:用户对单镜头的修改意见
        if feedback:
            context["user_feedback"] = feedback

        data = await self.llm.generate(task="storyboard", context=context)
        single = Storyboard(**data)
        if not single.shots:
            raise RuntimeError("单镜头重新生成未返回结果")
        new_shot = single.shots[0]
        # 保持连续性基准:scene_id/时长/锁定状态不允许 LLM 漂移
        new_shot.scene_id = old_shot.scene_id
        new_shot.duration = old_shot.duration
        new_shot.locked = old_shot.locked
        # 连续性继承:LLM 只看到单场景,上一镜状态必须由系统注入而非让它猜
        if shot_index > 0:
            prev = state.storyboard.shots[shot_index - 1]
            new_shot.continuity_in = prev.continuity_out or new_shot.continuity_in
            if not new_shot.causal_note:
                new_shot.causal_note = (
                    f"承接上一镜事件( {prev.visual_description[:40]} )导致本镜发生"
                )
        if shot_index + 1 < len(state.storyboard.shots):
            nxt = state.storyboard.shots[shot_index + 1]
            new_shot.continuity_out = nxt.continuity_in or new_shot.continuity_out
        # 重生成镜头不应保留旧镜头的生成模式决策之外的空值:人物/地点缺失时继承同场景基准
        if not new_shot.characters:
            new_shot.characters = old_shot.characters
        if not new_shot.location:
            new_shot.location = old_shot.location
        new_shot.desired_mode = old_shot.desired_mode or new_shot.desired_mode

        self._post_process_suffix(state, [new_shot])

        state.storyboard.shots[shot_index] = new_shot
        # 重建镜头因果链与场景态(指针级重建,相邻镜头文本保持不变)
        self._sync_project_state(state)

    # ============================ 内部辅助 ============================

    def _inject_planning_context(self, state: VideoGenerationState, context: dict) -> None:
        """把作品级规划(故事节拍 / Character Bible / World Bible / Style Bible)
        注入分镜上下文,让 LLM 产出跨镜一致的人物与场景。"""
        ps = state.get_or_create_project_state()
        story = ps.story_state
        if story.logline or story.beats:
            context["story"] = {
                "theme": story.theme,
                "logline": story.logline,
                "core_conflict": story.core_conflict,
                "beats": [b.model_dump() for b in story.beats],
            }
        if ps.character_state.bibles:
            context["characters"] = [b.model_dump() for b in ps.character_state.bibles]
        if ps.world_state.bible is not None:
            context["world"] = ps.world_state.bible.model_dump()
        if ps.style_state.bible is not None:
            context["style_bible"] = ps.style_state.bible.model_dump()

    def _post_process_suffix(self, state: VideoGenerationState, shots: list[StoryboardShot]) -> None:
        """确保 prompt_suffix 真实附加到 shot 的 image_prompt / video_prompt。

        这是参数贯通的最终保证 — 不依赖 LLM 自觉遵守指令。
        """
        if not state.spec:
            return
        from .prompt_compiler import PromptCompiler
        visual_directives = PromptCompiler.compile_visual_directives(state.spec)
        suffix = visual_directives.get("prompt_suffix")
        if not suffix:
            return
        for shot in shots:
            if shot.image_prompt and suffix.lower() not in shot.image_prompt.lower():
                shot.image_prompt = f"{shot.image_prompt}, {suffix}"
            if shot.video_prompt and suffix.lower() not in shot.video_prompt.lower():
                shot.video_prompt = f"{shot.video_prompt}, {suffix}"

    def _sync_project_state(self, state: VideoGenerationState) -> None:
        """分镜 → ProjectState 同步:

        - shot_state:每个镜头一条 ShotStateEntry(含连续性字段与参考资产),
          按序链接 prev/next 因果链指针;
        - scene_state:按 scene_id 聚合镜头,合并 World Bible 场景设定
          (天气/时段/光线跨镜一致)。
        """
        if state.storyboard is None:
            return
        ps = state.get_or_create_project_state()

        # ---- shot_state:全量重建(镜头数/顺序以 storyboard 为准) ----
        entries: list[ShotStateEntry] = []
        for i, shot in enumerate(state.storyboard.shots):
            ref_ids = ps.character_state.reference_assets_for(shot.characters)
            entries.append(ShotStateEntry(
                shot_index=i,
                scene_id=shot.scene_id,
                characters=list(shot.characters),
                location=shot.location,
                time_of_day=shot.time_of_day,
                action=shot.character_action,
                emotion_start=shot.emotion,
                emotion_end=shot.emotion_end,
                camera=shot.shot_type,
                camera_motion=shot.camera_movement,
                lighting=shot.lighting,
                dialogue=shot.dialogue,
                sound=(shot.background_music or shot.sound_effect),
                continuity_in=shot.continuity_in,
                continuity_out=shot.continuity_out,
                causal_note=shot.causal_note,
                ref_asset_ids=ref_ids,
                desired_mode=shot.desired_mode,
                desired_duration=shot.duration or 5,
                status="planned",
            ))
        ps.shot_state.shots = entries
        ps.shot_state.link_chain()

        # ---- scene_state:按 scene_id 聚合 + World Bible 场景设定合并 ----
        world_scenes: list = []
        if ps.world_state.bible is not None:
            world_scenes = ps.world_state.bible.scenes
        script_scenes = {s.scene_id: s for s in state.script.scenes} if state.script else {}

        grouped: dict[int, list[StoryboardShot]] = {}
        for shot in state.storyboard.shots:
            grouped.setdefault(shot.scene_id, []).append(shot)

        ps.scene_state.scenes = []
        for scene_id, shots in grouped.items():
            locations = [s.location for s in shots if s.location]
            location = locations[0] if locations else ""
            characters: list[str] = []
            for s in shots:
                for name in s.characters:
                    if name not in characters:
                        characters.append(name)
            ws = self._match_world_scene(world_scenes, location)
            sc = script_scenes.get(scene_id)
            summary = ""
            if sc is not None:
                summary = (sc.visual or sc.voiceover or "")[:120]
            ps.scene_state.upsert(SceneStateEntry(
                scene_id=scene_id,
                name=(ws.name if ws else "") or location,
                location=location or (ws.location if ws else ""),
                time_of_day=next((s.time_of_day for s in shots if s.time_of_day), "")
                or (ws.time_of_day if ws else ""),
                weather=(ws.weather if ws else ""),
                lighting=next((s.lighting for s in shots if s.lighting), "")
                or (ws.lighting if ws else ""),
                characters=characters,
                summary=summary,
                shot_count=len(shots),
                status="planned",
            ))

        ps.touch()

    @staticmethod
    def _match_world_scene(world_scenes: list, location: str):
        """在 World Bible 场景列表中按名称/地点模糊匹配。"""
        if not location:
            return None
        for ws in world_scenes:
            for key in (ws.scene_key, ws.name, ws.location):
                if key and (key in location or location in key):
                    return ws
        return None
