"""ImageWorkflow:为分镜生成关键帧图片(文生图)。

固定步骤:遍历 storyboard.shots → 对需要首帧的镜头调用 ImageModelProvider
→ 写回 shot.image_path / state.assets / asset_state 台账。

哪些镜头不需要关键帧(由 ShotPlanner 的 desired_mode 决策):
- t2v:纯文生视频空镜,不生成首帧
- r2v:参考图驱动,不生成首帧(主体一致性靠参考素材)
其余(i2v / first_last / 自动)都生成关键帧。
"""
from __future__ import annotations

import os

from ..core.config import settings, storage_dir
from ..core.logging import logger
from ..director.project_state import AssetEntry
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.image.base import ImageProvider
from .base import BaseWorkflow

# 不需要关键帧的镜头模式
_NO_KEYFRAME_MODES = ("t2v", "r2v")


class ImageWorkflow(BaseWorkflow):
    name = "image_workflow"

    def __init__(self, image: ImageProvider) -> None:
        self.image = image

    async def run(self, state: VideoGenerationState) -> None:
        if state.storyboard is None:
            raise RuntimeError("ImageWorkflow 缺少上游 storyboard")
        ps = state.get_or_create_project_state()
        ps.generation_state.current_stage = "image"

        n_shots = len(state.storyboard.shots)
        for i, shot in enumerate(state.storyboard.shots):
            if (shot.desired_mode or "").lower() in _NO_KEYFRAME_MODES:
                logger.info("shot%d: 模式=%s 跳过关键帧生成", i, shot.desired_mode)
                state.append_log(
                    TaskStatus.GENERATING_ASSETS,
                    f"镜头 {i+1}/{n_shots} 模式 {shot.desired_mode},无需关键帧",
                )
                continue
            await self.generate_shot(state, i)

    async def generate_shot(self, state: VideoGenerationState, shot_index: int) -> None:
        """生成(或重新生成)单个镜头的关键帧。局部重生成复用此入口。"""
        assert state.storyboard is not None
        shot = state.storyboard.shots[shot_index]
        n_shots = len(state.storyboard.shots)
        ps = state.get_or_create_project_state()

        state.append_log(
            TaskStatus.GENERATING_ASSETS,
            f"正在生成第 {shot_index+1}/{n_shots} 个镜头关键帧(文生图)",
        )
        img_dir = storage_dir("images")
        img_path = os.path.join(str(img_dir), f"{state.task_id}_shot{shot_index}.png")
        await self.image.generate(
            prompt=shot.image_prompt,
            save_path=img_path,
            width=settings.video_width,
            height=settings.video_height,
        )
        shot.image_path = img_path
        if img_path not in state.assets:
            state.assets.append(img_path)
        ps.asset_state.add(AssetEntry(
            asset_id=f"{state.task_id}_img_{shot_index}",
            type="image",
            path=img_path,
            shot_index=shot_index,
            source_provider=getattr(self.image, "name", "image"),
            metadata={"role": "keyframe", "mode": shot.desired_mode or "i2v"},
        ))
        logger.info("shot%d 关键帧生成完成: %s", shot_index, img_path)
