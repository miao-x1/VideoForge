"""视频输入处理器:抽取关键帧,调用 LLM 理解画面,输出文本描述。"""
from __future__ import annotations

import os

from ..core.logging import logger
from ..providers.llm.base import LLMProvider
from .base import InputProcessor, InputSource, InputPayload, InputType


class VideoProcessor(InputProcessor):
    name = "video"

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def process(self, source: InputSource) -> InputPayload:
        video_path = source.content
        if not os.path.isfile(video_path):
            return InputPayload(
                type=InputType.VIDEO,
                raw_content=video_path,
                processed_content=f"[视频文件不存在: {os.path.basename(video_path)}]",
            )
        frames = await self._extract_key_frames(video_path)
        if not frames:
            return InputPayload(
                type=InputType.VIDEO,
                raw_content=video_path,
                processed_content=f"[视频已上传: {os.path.basename(video_path)},关键帧提取失败]",
            )
        descriptions: list[str] = []
        for i, frame_path in enumerate(frames):
            try:
                desc = await self.llm.describe_image(
                    frame_path, prompt=f"这是视频的第{i+1}个关键帧,请描述画面内容、主体、风格和色调"
                )
                descriptions.append(f"帧{i+1}: {desc}")
            except NotImplementedError:
                descriptions.append(f"帧{i+1}: [LLM 不支持图片理解]")
            except Exception as e:
                descriptions.append(f"帧{i+1}: [理解失败: {e}]")
            finally:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
        return InputPayload(
            type=InputType.VIDEO,
            raw_content=video_path,
            processed_content="\n".join(descriptions),
        )

    @staticmethod
    async def _extract_key_frames(video_path: str, count: int = 3) -> list[str]:
        import asyncio
        from ..core.config import storage_dir

        frames_dir = storage_dir("frames")

        def _extract() -> list[str]:
            from moviepy import VideoFileClip
            clip = VideoFileClip(video_path)
            duration = clip.duration
            paths = []
            for i in range(count):
                t = duration * (i + 0.5) / count
                frame_path = os.path.join(frames_dir, f"frame_{id(video_path)}_{i}.png")
                clip.save_frame(frame_path, t=t)
                paths.append(frame_path)
            clip.close()
            return paths

        try:
            return await asyncio.to_thread(_extract)
        except Exception as e:
            logger.warning("关键帧提取失败 %s: %s", video_path, e)
            return []
