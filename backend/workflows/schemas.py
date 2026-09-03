"""Workflow 配置模型:描述一个 ComfyUI Workflow 的业务输入与注入点。

每个 Workflow 目录下放置:
  <name>.json         ComfyUI 官方模板(UI Format,含子图定义)
  <name>.config.json  本模块的配置(输入声明 + 注入点)

注入点两种:
  subgraph_input: 打包子图实例上的提升输入(先展开子图后定位内部节点)
  node_widget:    普通节点上的 widget 值
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

WORKFLOWS_ROOT = Path(__file__).resolve().parent


class WorkflowInjection(BaseModel):
    """业务参数注入点。"""

    kind: Literal["subgraph_input", "node_widget"]
    node: int = Field(..., description="节点 ID(UI 图中)")
    input: Optional[str] = Field(None, description="子图输入名(kind=subgraph_input 时)")
    widget: Optional[str] = Field(None, description="widget 名(kind=node_widget 时)")


class WorkflowInputSpec(BaseModel):
    """单个业务输入的声明。"""

    type: Literal["string", "image", "number", "integer", "boolean"] = "string"
    required: bool = False
    inject: WorkflowInjection
    description: str = ""


class WorkflowConfig(BaseModel):
    """Workflow 配置(单文件描述)。"""

    workflow_id: str
    provider: str = "comfy_cloud"
    category: str = Field(..., description="业务类别:text_to_video/image_to_video/reference_to_video/...")
    model: str = Field("", description="底层模型名,如 MiniMax H3")
    version: str = "1.0"
    file: str = Field(..., description="Workflow JSON 文件名(同目录)")
    source: str = Field("", description="模板来源,如官方 workflow_templates 仓库链接")
    description: str = ""
    inputs: dict[str, WorkflowInputSpec] = Field(default_factory=dict)

    def input_names(self) -> list[str]:
        return list(self.inputs.keys())
