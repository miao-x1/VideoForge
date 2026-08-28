"""单元测试 DashScope I2V Provider:用一张已有图片生成 5s 动态视频。

验证:
1. POST 提交任务能拿到 task_id
2. 轮询能在 5 分钟内拿到 video_url
3. 下载的 mp4 文件合法(可读、时长≈5s、含视频流)
"""
from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.providers.video.dashscope_i2v import DashScopeI2VProvider  # noqa: E402
from app.core.logging import logger  # noqa: E402

# 用上一次外卖古装 Pipeline 的 shot1 图片作为首帧输入
INPUT_IMG = os.path.normpath(os.path.join(_HERE, "..", "storage", "images", "c5e00785ba56_shot1.png"))
# 输出 mp4 到 storage/videos/test_i2v.mp4
OUTPUT_MP4 = os.path.normpath(os.path.join(_HERE, "..", "storage", "videos", "test_i2v_shot1.mp4"))
# I2V 动作提示词(描述期望人物动作/运镜)
PROMPT = "A young man in a white robe slowly turns his head and reaches out, ancient Chinese street with lanterns, slight wind, slow camera push in"


async def main() -> None:
    if not os.path.exists(INPUT_IMG):
        print(f"FAIL: 输入图片不存在: {INPUT_IMG}")
        return
    print(f"输入图片: {INPUT_IMG}")
    print(f"输出路径: {OUTPUT_MP4}")
    print(f"提示词: {PROMPT}")
    print(f"图片大小: {os.path.getsize(INPUT_IMG)} bytes\n")

    provider = DashScopeI2VProvider()
    print(f"Provider: model={provider.model}, endpoint={provider.submit_url}")
    print(f"API Key: {provider.api_key[:10]}...\n")

    print("开始 I2V 生成(可能需要 1-5 分钟,请耐心等待)...")
    t0 = asyncio.get_event_loop().time()
    try:
        result = await provider.generate(
            image_path=INPUT_IMG,
            prompt=PROMPT,
            save_path=OUTPUT_MP4,
            duration=5,
        )
        elapsed = asyncio.get_event_loop().time() - t0
        print(f"\n✅ I2V 生成成功(耗时 {elapsed:.1f}s)")
        print(f"输出文件: {result}")
        print(f"文件大小: {os.path.getsize(result)} bytes")

        # 验证 mp4 可读 + 时长
        from moviepy import VideoFileClip
        clip = VideoFileClip(result)
        print(f"视频时长: {clip.duration:.2f}s")
        print(f"视频尺寸: {clip.size[0]}x{clip.size[1]}")
        print(f"视频 FPS: {clip.fps}")
        clip.close()

        # 提取首帧和末帧对比,验证是否真有连续动作
        import numpy as np
        from PIL import Image
        clip = VideoFileClip(result)
        f_start = clip.get_frame(0.5)
        f_end = clip.get_frame(min(clip.duration - 0.5, 4.5))
        clip.close()
        diff = np.abs(f_start.astype(np.int16) - f_end.astype(np.int16))
        mad = float(diff.mean())
        diff_ratio = float((diff > 10).mean())
        print(f"\n首帧 vs 末帧差异: MAD={mad:.2f}  diff%={diff_ratio*100:.2f}%")
        if mad > 10:
            print("✅ 视频含真实连续动作(MAD > 10)")
        else:
            print("⚠ MAD 偏低,可能仍是静态图(请肉眼确认)")

        # 保存首末帧供肉眼对比
        Image.fromarray(f_start).save(os.path.join(os.path.dirname(OUTPUT_MP4), "test_i2v_start.png"))
        Image.fromarray(f_end).save(os.path.join(os.path.dirname(OUTPUT_MP4), "test_i2v_end.png"))
        print(f"首/末帧已保存: {os.path.dirname(OUTPUT_MP4)}/test_i2v_start.png / test_i2v_end.png")
    except Exception as e:
        elapsed = asyncio.get_event_loop().time() - t0
        print(f"\n❌ I2V 生成失败(耗时 {elapsed:.1f}s): {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
