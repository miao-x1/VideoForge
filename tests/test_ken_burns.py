"""单元测试 _apply_ken_burns 所有分支能正确执行(不抛异常)。"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from moviepy import ImageClip, CompositeVideoClip  # noqa: E402
import numpy as np  # noqa: E402

from app.video.assembly import _apply_ken_burns  # noqa: E402

W, H = 720, 1280


def _make_clip():
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[::50, :] = 255  # 横线
    img[:, ::50] = 255  # 竖线
    return ImageClip(img, duration=4)


cases = [
    ("push in on subject", 4),
    ("dolly forward as character rushes in", 5),
    ("zoom in on detail", 4),
    ("rack focus between算盘 and 保温箱", 5),
    ("pull out to reveal environment", 4),
    ("zoom out as character enters", 5),
    ("crane back revealing full street", 6),
    ("slow pan right to reveal character", 5),
    ("pan left across scene", 4),
    ("tilt down to floor", 4),
    ("tilt up to sky", 5),
    ("steady crane up and back", 6),
    ("pan", 4),
    ("", 4),
    ("static shot", 4),
    ("unknown motion keywords", 4),
]

print(f"测试 {len(cases)} 种 camera_movement:")
for i, (motion, dur) in enumerate(cases):
    try:
        clip = _make_clip()
        result = _apply_ken_burns(clip, motion, dur, W, H)
        # 试合成一个 1s 的 CompositeVideoClip 验证 position lambda 能跑
        comp = CompositeVideoClip([result], size=(W, H)).with_duration(0.5)
        # 取一帧(强制 lambda 执行)
        _ = comp.get_frame(0.25)
        print(f"  [{i+1:2d}] OK  '{motion[:50]}'")
    except Exception as e:
        print(f"  [{i+1:2d}] FAIL '{motion[:50]}' -> {type(e).__name__}: {e}")

print("全部测试完成")
