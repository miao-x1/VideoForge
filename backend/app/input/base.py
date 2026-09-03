"""多模态输入抽象基类。

InputSource:统一封装用户提供的文本/图片/视频/URL 输入。
InputProcessor:将不同类型的输入解析为文本描述,注入 RequirementAgent context。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    URL = "url"


class InputSource(BaseModel):
    type: InputType
    content: str = Field(..., description="文本内容/文件路径/URL")
    purpose: str = Field("overall", description="参考用途: subject/scene/style/camera/action/overall 等")


class InputPayload(BaseModel):
    type: InputType
    raw_content: str
    processed_content: str = Field("", description="解析/理解后的文本描述")
    purpose: str = Field("overall", description="用户标注的参考用途")


class InputProcessor(ABC):
    name: str = ""

    @abstractmethod
    async def process(self, source: InputSource) -> InputPayload:
        ...


PURPOSE_LABELS = {
    "subject": "主体参考",
    "scene": "场景参考",
    "style": "风格参考",
    "camera": "镜头参考",
    "action": "动作参考",
    "composition": "构图参考",
    "color": "色彩参考",
    "movement": "运动参考",
    "rhythm": "节奏参考",
    "overall": "整体参考",
}


def build_multimodal_context(payloads: list[InputPayload]) -> str:
    """将多个 InputPayload 的理解结果拼接为 RequirementAgent 可用的上下文文本。"""
    parts: list[str] = []
    for p in payloads:
        type_label = {
            InputType.TEXT: "文本输入",
            InputType.IMAGE: "图片输入",
            InputType.VIDEO: "视频输入",
            InputType.URL: "URL输入",
        }.get(p.type, "输入")
        purpose_label = PURPOSE_LABELS.get(p.purpose or "overall", "整体参考")
        if purpose_label != "整体参考":
            parts.append(f"[{type_label}·{purpose_label}] {p.processed_content}")
        else:
            parts.append(f"[{type_label}] {p.processed_content}")
    return "\n".join(parts) if parts else ""
