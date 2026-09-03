"""TTSWorkflow:为分镜生成旁白音频(文本转语音)。

固定步骤:遍历 storyboard.shots → 调用 VoiceModelProvider 合成旁白
→ 写回 shot.audio_path / state.assets / asset_state 台账。
音频的"创作决策"(旁白文案/情绪/音乐音效规划)由 Agent 层完成,
本 Workflow 只执行确定的 TTS 合成。
"""
from __future__ import annotations

import os

from ..core.config import storage_dir
from ..core.logging import logger
from ..director.project_state import AssetEntry
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.voice.base import VoiceProvider
from .base import BaseWorkflow


class TTSWorkflow(BaseWorkflow):
    name = "tts_workflow"

    def __init__(self, voice: VoiceProvider) -> None:
        self.voice = voice

    async def run(self, state: VideoGenerationState) -> None:
        if state.storyboard is None:
            raise RuntimeError("TTSWorkflow 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        ps.generation_state.current_stage = "audio"
        n_shots = len(state.storyboard.shots)
        for i in range(n_shots):
            state.append_log(
                TaskStatus.GENERATING_ASSETS,
                f"正在生成第 {i+1}/{n_shots} 个镜头旁白(TTS)",
            )
            await self.generate_shot(state, i)

    async def generate_shot(self, state: VideoGenerationState, shot_index: int) -> None:
        """合成(或重新合成)单个镜头旁白。局部重生成复用此入口。"""
        assert state.storyboard is not None
        shot = state.storyboard.shots[shot_index]
        ps = state.get_or_create_project_state()

        audio_dir = storage_dir("audio")
        audio_path = os.path.join(str(audio_dir), f"{state.task_id}_shot{shot_index}.wav")
        await self.voice.generate(
            text=shot.voiceover or shot.visual_description,
            save_path=audio_path,
            duration=shot.duration,
        )
        shot.audio_path = audio_path
        if audio_path not in state.assets:
            state.assets.append(audio_path)
        asset_id = f"{state.task_id}_tts_{shot_index}"
        ps.asset_state.add(AssetEntry(
            asset_id=asset_id,
            type="audio",
            path=audio_path,
            shot_index=shot_index,
            source_provider=getattr(self.voice, "name", "voice"),
            metadata={"role": "narration"},
        ))
        # 回绑音频规划 cue:规划(Agent)→ 执行(Workflow)状态闭环
        for cue in ps.audio_state.cues_for_shot(shot_index):
            if cue.type in ("narration", "dialogue") and cue.status == "planned":
                cue.asset_id = asset_id
                cue.status = "generated"
        ps.touch()
        logger.info("shot%d 旁白生成完成: %s", shot_index, audio_path)
