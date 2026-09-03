"""Workflow Adapter:业务参数 → Workflow 参数注入。

Agent 只产出业务语义参数(task_type/prompt/first_frame/duration/aspect_ratio),
Adapter 负责把它们映射到 Workflow 内部节点:
  prompt      → 子图提升输入 prompt(或 Prompt 节点 widget)
  first_frame → LoadImage 节点的 image widget(云端上传后的文件名)
  duration    → 秒(H3 内部按 24fps 对齐到 17 帧块,公式与官方模板一致)
  aspect_ratio → width/height(对齐到 32 的倍数,与 ResolutionSelector 的 multiple 一致)

Agent 永远不生成节点参数,所有映射规则收敛在本文件。
"""
from __future__ import annotations

from workflows.registry import WorkflowRegistry, workflow_registry
from workflows.converter import ui_to_api

# 分辨率对齐步长(官方模板 ResolutionSelector.multiple=32)
_RESOLUTION_STEP = 32
# H3 帧长度对齐(官方模板 ComfyMathExpression 的对齐公式)
_FRAME_CHUNK = 17


class WorkflowValidationError(Exception):
    """业务参数校验失败(必填缺失/类型非法)。"""


def align_resolution(value: int) -> int:
    """分辨率对齐到 32 的倍数。"""
    return max(_RESOLUTION_STEP, round(value / _RESOLUTION_STEP) * _RESOLUTION_STEP)


def duration_to_length(duration: float) -> int:
    """秒 → H3 帧数(与官方模板表达式一致)。

    max(5, round(a*24)) + (5 - max(5, round(a*24)) % 17) % 17
    """
    frames = max(5, round(duration * 24))
    return frames + (5 - frames % _FRAME_CHUNK) % _FRAME_CHUNK


ASPECT_RATIOS = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (960, 960),
}


def resolve_aspect_ratio(
    aspect_ratio: str | None, width: int | None = None, height: int | None = None
) -> tuple[int, int]:
    """业务比例(可选)→ 具体 width/height,显式值优先。"""
    if width and height:
        return align_resolution(width), align_resolution(height)
    w, h = ASPECT_RATIOS.get(aspect_ratio or "9:16", (720, 1280))
    return align_resolution(w), align_resolution(h)


class WorkflowAdapter:
    def __init__(self, registry: WorkflowRegistry = workflow_registry) -> None:
        self.registry = registry

    def build_prompt(self, workflow_id: str, params: dict) -> dict:
        """业务参数 → API Format Workflow(可直接提交云端执行)。

        Args:
            workflow_id: Registry 中的 Workflow ID
            params: 业务语义参数(prompt/first_frame/duration/aspect_ratio/...)

        Returns:
            API Format prompt dict
        """
        config = self.registry.get(workflow_id)
        workflow_ui = self.registry.load_workflow(workflow_id)
        api_prompt, subgraph_inputs = ui_to_api(workflow_ui)

        # 参数校验
        for name, spec in config.inputs.items():
            if spec.required and params.get(name) in (None, ""):
                raise WorkflowValidationError(f"缺少必填参数: {name}")

        for name, spec in config.inputs.items():
            value = params.get(name)
            if value is None:
                continue
            # 依据注入点写入
            inject = spec.inject
            if inject.kind == "subgraph_input":
                targets = subgraph_inputs.get((inject.node, inject.input), [])
                if not targets:
                    raise WorkflowValidationError(
                        f"注入点不存在: node={inject.node} input={inject.input} (workflow={workflow_id})"
                    )
                for key, field in targets:
                    api_prompt[key]["inputs"][field] = value
            else:  # node_widget
                key = str(inject.node)
                if key not in api_prompt:
                    raise WorkflowValidationError(
                        f"注入节点不存在: node={inject.node} (workflow={workflow_id})"
                    )
                api_prompt[key]["inputs"][inject.widget] = value

        return api_prompt


workflow_adapter = WorkflowAdapter()
