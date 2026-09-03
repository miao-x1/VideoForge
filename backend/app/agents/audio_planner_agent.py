"""AudioPlannerAgent:音频规划决策 Agent(任务书第 7 节)。

在分镜完成后、音频制作前决策"每个镜头该听到什么":
- 逐镜头 AudioCue:旁白(narration)/对白(dialogue)/音效(sfx)的演绎情绪
- 全片音乐:music_mood(情绪基调)与 music_style(风格),不再写死 "light"
决策写入 audio_state;TTS/Music Workflow 只负责按决策执行合成。

与分镜字段的分工:shot.voiceover/dialogue/sound_effect 是"文本内容",
audio_state.cues 是"制作决策"(情绪/用途/状态跟踪 + 资产绑定)。
"""
from __future__ import annotations

from ..core.logging import logger
from ..director.project_state import AudioCue
from ..models.state import VideoGenerationState
from .base import BaseAgent


class AudioPlannerAgent(BaseAgent):
    name = "audio_planning"

    async def run(self, state: VideoGenerationState, *, force: bool = False) -> None:
        if state.storyboard is None:
            raise RuntimeError("AudioPlannerAgent 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        if ps.audio_state.cues and not force:
            logger.info("音频规划已存在(cues=%d),跳过", len(ps.audio_state.cues))
            return

        context = self._build_context(state)
        data = await self.llm.generate(task="audio_planning", context=context)

        # 全片音乐决策
        ps.audio_state.music_mood = data.get("music_mood", "") or self._infer_music_mood(state)
        ps.audio_state.music_style = data.get("music_style", "")

        # 逐镜头音频 cue(LLM 产出;缺失时从分镜字段确定性补齐)
        cues: list[AudioCue] = []
        raw_cues = {c.get("shot_index"): c for c in (data.get("cues") or []) if c.get("shot_index") is not None}
        for i, shot in enumerate(state.storyboard.shots):
            raw = raw_cues.get(i, {})
            if raw.get("narration") or shot.voiceover:
                cues.append(AudioCue(
                    shot_index=i,
                    type="narration",
                    text=shot.voiceover,
                    emotion=raw.get("narration_emotion") or shot.emotion or "neutral",
                ))
            if raw.get("dialogue") or shot.dialogue:
                cues.append(AudioCue(
                    shot_index=i,
                    type="dialogue",
                    text=shot.dialogue,
                    emotion=raw.get("dialogue_emotion") or shot.emotion or "neutral",
                ))
            sfx_desc = raw.get("sfx") or shot.sound_effect
            if sfx_desc:
                cues.append(AudioCue(
                    shot_index=i,
                    type="sfx",
                    description=sfx_desc,
                    emotion=shot.emotion or "",
                ))
        # 全片音乐 cue
        cues.append(AudioCue(
            shot_index=None,
            type="music",
            description=f"{ps.audio_state.music_style} {ps.audio_state.music_mood}".strip(),
            emotion=ps.audio_state.music_mood,
        ))
        ps.audio_state.cues = cues
        ps.touch()
        logger.info(
            "音频规划完成: cues=%d music_mood=%s music_style=%s",
            len(cues), ps.audio_state.music_mood, ps.audio_state.music_style,
        )

    @staticmethod
    def _build_context(state: VideoGenerationState) -> dict:
        ps = state.get_or_create_project_state()
        return {
            "storyboard": state.storyboard.model_dump() if state.storyboard else None,
            "beats": [b.model_dump() for b in ps.story_state.beats],
            "style": state.style,
            "genre": ps.project_info.genre or (state.requirement.genre if state.requirement else ""),
        }

    @staticmethod
    def _infer_music_mood(state: VideoGenerationState) -> str:
        """无 LLM 产出时从故事节拍情绪推断全片音乐基调(确定性兜底)。"""
        ps = state.get_or_create_project_state()
        emotions = [b.emotion for b in ps.story_state.beats if b.emotion]
        if any(e in emotions for e in ("紧张", "冲突", "高潮", "tension")):
            return "tense"
        if any(e in emotions for e in ("悲伤", "遗憾", "虐心", "sad")):
            return "melancholic"
        if any(e in emotions for e in ("幽默", "轻松", "喜剧", "humor")):
            return "light"
        return "light"
