"""本地检查规则规划器覆盖 12 个验收句。"""
from __future__ import annotations

from .planner import plan

SCENES = [
    ("创建一个女主角。", ["create_character"]),
    ("把女主角加入当前场景。", ["add_character_to_scene"]),
    ("让女主角站在房间中央。", ["move_character"]),
    ("让女主角向桌子走去。", ["move_character", "set_character_action"]),
    ("让女主角坐下。", ["set_character_pose"]),
    ("让摄像机对准女主角。", ["set_camera_target"]),
    ("镜头慢慢推进。", ["set_camera_motion"]),
    ("创建一个 5 秒镜头。", ["create_shot"]),
    ("把这个镜头复制一份。", ["duplicate_shot"]),
    ("生成这个镜头的视频提示词。", ["generate_prompt"]),
    ("撤销刚才的操作。", ["undo_last"]),
    ("恢复刚才的操作。", ["redo_last"]),
    ("然后坐下来。", ["set_character_pose"]),
    ("让她走到沙发旁边。", ["move_character"]),
    ("我要做一个女生在客厅里坐下的镜头。", ["place_room_preset", "create_character", "update_shot"]),
    ("发送构图。", ["send_composition"]),
    ("生成这个镜头的画面。", ["generate_image"]),
    ("把这个画面做成5秒视频。", ["generate_video"]),
    ("最后一个镜头改成脸部特写。", ["set_shot_type"]),
]


def main() -> int:
    ctx = {
        "scene_id": "scene_1",
        "scene_name": "分镜 1",
        "objects": [
            {"id": "char_1", "name": "女主角", "characterId": "c1", "position": [0, 0, 0]},
        ],
        "focus": {"character_id": "c1", "object_id": "char_1"},
        "cameras": [{"id": "camera_001", "name": "机位1", "position": [0, 1.6, 5], "fov": 45}],
        "characters": [{"id": "c1", "name": "女主角"}],
    }
    failed = 0
    for text, expected in SCENES:
        result = plan(text, ctx)
        names = [c["name"] for c in result.get("calls") or []]
        missing = [n for n in expected if n not in names]
        if missing or result.get("error"):
            failed += 1
            print("FAIL", text, "got", names, "err", result.get("error"), "missing", missing)
        else:
            print("OK  ", text, "->", names)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
