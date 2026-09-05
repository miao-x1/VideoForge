"""Tool 白名单。Agent 只能调用这里注册的名字。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    group: str
    description: str
    confirm: bool = False
    permission: str = "mutate"
    side_effect: str = "mutates_scene"


TOOLS: list[ToolSpec] = [
    ToolSpec("create_character", "character", "从官方模板创建角色资产并加入当前分镜"),
    ToolSpec("add_character_to_scene", "character", "把已有角色加入当前分镜"),
    ToolSpec("remove_character_from_scene", "character", "从当前分镜移除角色实例", confirm=True),
    ToolSpec("move_character", "character", "移动角色到目标位置，可选走路动画"),
    ToolSpec("rotate_character", "character", "旋转角色"),
    ToolSpec("scale_character", "character", "缩放角色"),
    ToolSpec("set_character_action", "character", "设置走路/跑步/挥手等动作"),
    ToolSpec("set_character_pose", "character", "设置站/坐/躺等姿势"),
    ToolSpec("set_character_expression", "character", "设置表情（当前角色系统若不支持会失败）"),
    ToolSpec("create_scene", "scene", "新建空分镜"),
    ToolSpec("rename_scene", "scene", "重命名当前或指定分镜"),
    ToolSpec("delete_scene", "scene", "删除分镜", confirm=True),
    ToolSpec("add_prop", "scene", "从目录添加道具/家具"),
    ToolSpec("remove_prop", "scene", "删除场景物件", confirm=True),
    ToolSpec("move_prop", "scene", "移动物件"),
    ToolSpec("rotate_prop", "scene", "旋转物件"),
    ToolSpec("scale_prop", "scene", "缩放物件"),
    ToolSpec("change_environment", "scene", "修改天空/环境光/网格"),
    ToolSpec("place_room_preset", "scene", "放入房间几何预设"),
    ToolSpec("create_camera", "camera", "添加机位"),
    ToolSpec("select_camera", "camera", "选中机位并切到机位视角"),
    ToolSpec("move_camera", "camera", "移动机位"),
    ToolSpec("rotate_camera", "camera", "旋转机位"),
    ToolSpec("set_camera_fov", "camera", "设置机位焦距"),
    ToolSpec("set_camera_target", "camera", "让机位对准目标"),
    ToolSpec("set_camera_motion", "camera", "推进/拉远/摇移等机位运动"),
    ToolSpec("create_shot", "shot", "新建分镜并可设时长与描述"),
    ToolSpec("delete_shot", "shot", "删除分镜", confirm=True),
    ToolSpec("duplicate_shot", "shot", "复制当前分镜"),
    ToolSpec("update_shot", "shot", "更新分镜名称/时长/描述"),
    ToolSpec("set_shot_duration", "shot", "设置分镜时长"),
    ToolSpec("set_shot_description", "shot", "设置分镜描述"),
    ToolSpec("create_keyframe", "timeline", "在时间线上记录关键帧"),
    ToolSpec("update_keyframe", "timeline", "更新关键帧"),
    ToolSpec("delete_keyframe", "timeline", "删除关键帧"),
    ToolSpec("set_animation_duration", "timeline", "设置时间线时长"),
    ToolSpec("generate_prompt", "prompt", "根据当前导演台状态生成提示词", permission="read", side_effect="none"),
    ToolSpec("set_shot_type", "shot", "设置景别：wide / medium / close-up"),
    ToolSpec("send_composition", "generation", "把当前 3D 机位构图截图发回画布节点，作为生图/生视频空间参考"),
    ToolSpec("generate_image", "generation", "按当前镜头生成参考图（真实图片模型）"),
    ToolSpec("generate_video", "generation", "按当前镜头生成视频（真实视频模型）"),
    ToolSpec("set_camera", "camera", "统一设置机位位置/焦距/运动/对准"),
    ToolSpec("restore_generation", "generation", "恢复历史生成版本到当前分镜", confirm=True, side_effect="mutates_generation"),
    ToolSpec("update_storyboard", "shot", "更新分镜描述与故事板"),
    ToolSpec("update_timeline", "timeline", "更新时间线时长或关键帧"),
    ToolSpec("undo_last", "history", "撤销上一步导演台修改", permission="mutate", side_effect="mutates_scene"),
    ToolSpec("redo_last", "history", "重做上一步导演台修改", permission="mutate", side_effect="mutates_scene"),
]

ALLOWED = {t.name: t for t in TOOLS}


def is_allowed(name: str) -> bool:
    return name in ALLOWED


def needs_confirm(name: str) -> bool:
    spec = ALLOWED.get(name)
    return bool(spec and spec.confirm)
