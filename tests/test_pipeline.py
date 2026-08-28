"""端到端 Pipeline 测试。

直接运行(无需 pytest):
  python tests/test_pipeline.py
或:
  python -m tests.test_pipeline

验证:输入"假如古代人有手机"创意 -> 最终生成真实 MP4 文件。
"""
from __future__ import annotations

import asyncio
import os
import sys

# 把 backend 加入 import 路径,允许直接 python 运行
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.orchestrator.orchestrator import orchestrator  # noqa: E402
from app.services.task_service import task_store  # noqa: E402


async def run_pipeline() -> None:
    state = task_store.create(
        user_input="假如古代人有手机，做一个30秒轻松搞笑的短视频。",
        duration=30,
        style="轻松搞笑",
    )
    print(f"[test] 创建任务 task_id={state.task_id}")
    await orchestrator.execute(state)

    assert state.status.value == "COMPLETED", f"Pipeline 未完成: status={state.status} error={state.error}"
    assert state.video_path and os.path.exists(state.video_path), f"MP4 不存在: {state.video_path}"

    size = os.path.getsize(state.video_path)
    print(f"[test] 通过 -> {state.video_path} ({size} bytes)")
    print(f"[test] 分镜数: {len(state.storyboard.shots) if state.storyboard else 0}")
    print(f"[test] 素材数: {len(state.assets)}")

    # 导出完整 storyboard 清单,便于用 GenerateImage 工具生成真实 Seedream 图后重装配
    if state.storyboard:
        import json
        prompts_file = os.path.join(os.path.dirname(state.video_path), f"{state.task_id}_prompts.json")
        shots_info = [
            {
                "index": i,
                "image_path": s.image_path,
                "audio_path": s.audio_path,
                "image_prompt": s.image_prompt,
                "duration": s.duration,
                "voiceover": s.voiceover,
                "visual_description": s.visual_description,
            }
            for i, s in enumerate(state.storyboard.shots)
        ]
        bgm_path = state.assets[-1] if state.assets else ""
        with open(prompts_file, "w", encoding="utf-8") as f:
            json.dump({"task_id": state.task_id, "bgm_path": bgm_path, "title": state.script.title if state.script else "", "shots": shots_info}, f, ensure_ascii=False, indent=2)
        print(f"[test] storyboard 清单已导出: {prompts_file}")
        for i, s in enumerate(state.storyboard.shots):
            print(f"  [shot{i}] {s.image_prompt}")

    print("[test] 全部断言通过 ✅")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
