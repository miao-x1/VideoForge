"""Workflow 层:把 Agent 已决策的任务按固定步骤执行(无 LLM 创作决策)。

- ImageWorkflow:关键帧图片生成
- VideoWorkflow:逐镜头模式决策(t2v/i2v/r2v/first_last) + 视频片段生成
- TTSWorkflow:旁白语音合成
- MusicWorkflow:整片背景音乐
- EditingWorkflow:镜头片段合成成片
"""
from .base import BaseWorkflow
from .editing_workflow import EditingWorkflow
from .image_workflow import ImageWorkflow
from .music_workflow import MusicWorkflow
from .tts_workflow import TTSWorkflow
from .video_workflow import VideoWorkflow

__all__ = [
    "BaseWorkflow",
    "ImageWorkflow",
    "VideoWorkflow",
    "TTSWorkflow",
    "MusicWorkflow",
    "EditingWorkflow",
]
