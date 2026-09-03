"""MusicWorkflow:生成整片背景音乐(BGM)。

固定步骤:按分镜总时长调用 MusicModelProvider 生成一条 BGM
→ 写回 state.assets / asset_state / audio_state.bgm_asset_id。

音乐情绪不再写死 "light":优先读取 AudioPlanner 决策的
audio_state.music_mood(未规划时回退 light)。
文件命名保持 {task_id}_bgm.wav 约定,供合成阶段定位。
"""
from __future__ import annotations

import os

from ..core.config import storage_dir
from ..core.logging import logger
from ..director.project_state import AssetEntry
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.music.base import MusicProvider
from .base import BaseWorkflow


class MusicWorkflow(BaseWorkflow):
    name = "music_workflow"

    def __init__(self, music: MusicProvider) -> None:
        self.music = music

    async def run(self, state: VideoGenerationState) -> None:
        if state.storyboard is None:
            raise RuntimeError("MusicWorkflow 缺少上游 storyboard")
        assert state.storyboard is not None
        ps = state.get_or_create_project_state()
        total_duration = sum(s.duration for s in state.storyboard.shots)
        mood = ps.audio_state.music_mood or "light"

        audio_dir = storage_dir("audio")
        bgm_path = os.path.join(str(audio_dir), f"{state.task_id}_bgm.wav")
        state.append_log(
            TaskStatus.GENERATING_ASSETS,
            f"正在生成整片背景音乐(BGM, mood={mood}, {total_duration}s)",
        )
        await self.music.generate(save_path=bgm_path, duration=total_duration, mood=mood)
        if bgm_path not in state.assets:
            state.assets.append(bgm_path)

        asset_id = f"{state.task_id}_bgm"
        ps.asset_state.add(AssetEntry(
            asset_id=asset_id,
            type="music",
            path=bgm_path,
            source_provider=getattr(self.music, "name", "music"),
            metadata={"mood": mood, "duration": str(total_duration)},
        ))
        ps.audio_state.bgm_asset_id = asset_id
        ps.touch()
        logger.info("BGM 生成完成(mood=%s, %ds): %s", mood, total_duration, bgm_path)
