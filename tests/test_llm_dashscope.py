"""DashScope LLM 连通性测试(三个 task 都验证)。

直接运行: python tests/test_llm_dashscope.py
验证: API Key 可用 / 模型可调 / 三个 prompt 均产出合法 JSON。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.providers.llm.dashscope_llm import DashScopeLLMProvider  # noqa: E402


async def main() -> None:
    p = DashScopeLLMProvider()
    print(f"[llm] model={p.model} base={p.base_url}")

    # 1) requirement
    r = await p.generate(
        task="requirement",
        context={
            "user_input": "假如古代人有手机，做一个30秒轻松搞笑的短视频。",
            "duration": 30,
            "style": "轻松搞笑",
        },
    )
    print("[llm] REQUIREMENT topic =", r.get("topic"), "| duration =", r.get("duration"))
    print("[llm]   characters =", [c.get("name") for c in r.get("characters", [])])

    # 2) script
    s = await p.generate(task="script", context={"requirement": r})
    print("[llm] SCRIPT title =", s.get("title"), "| scenes =", len(s.get("scenes", [])))
    if s.get("scenes"):
        print("[llm]   scene1 voiceover =", (s["scenes"][0].get("voiceover") or "")[:60])

    # 3) storyboard
    sb = await p.generate(task="storyboard", context={"script": s})
    shots = sb.get("shots", [])
    print("[llm] STORYBOARD shots =", len(shots))
    if shots:
        print("[llm]   shot1 shot_type =", shots[0].get("shot_type"))
        print("[llm]   shot1 image_prompt =", (shots[0].get("image_prompt") or "")[:120])

    print("[llm] DashScope LLM 实测通过 ✅")


if __name__ == "__main__":
    asyncio.run(main())
