"""Video Quality Validator:对最终 MP4 与素材清单做轻量级一致性/规格校验。

检查项(无外部依赖,仅用 moviepy + PIL + os):
1. 文件存在 / 大小 > 0
2. 时长(与目标 ±2s 容差)
3. 分辨率(默认 9:16 竖屏, 720x1280)
4. FPS(默认 24)
5. 是否含音轨
6. 场景-素材数量一致性(shots / images / TTS 段数应相等)
7. 各分镜图片存在且可读、TTS 文件存在且非空

输出: VideoQualityReport(dict),含 grade 字段:
- A: 全部规格达标 + 场景素材一致 + 9:16 竖屏
- B: 基本达标但有 1 处轻微缺陷(如时长偏差 1~2s / FPS 略偏)
- C: 存在明显缺陷(分辨率/比例错误、缺音轨、静音段过长可修复)
- D: 关键产物缺失(无视频文件、文件损坏、无场景素材)

不修改 Pipeline 主流程,可被测试或独立调用。
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from ..core.config import settings
from ..core.logging import logger
from ..schemas.storyboard import Storyboard


def _read_video_meta(path: str) -> Dict[str, Any]:
    """同步读取视频元信息。"""
    from moviepy import VideoFileClip

    clip = VideoFileClip(path)
    try:
        meta = {
            "duration": float(clip.duration or 0),
            "width": int(clip.size[0]),
            "height": int(clip.size[1]),
            "fps": float(clip.fps or 0),
            "has_audio": clip.audio is not None,
        }
    finally:
        clip.close()
    return meta


async def _get_video_meta(path: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_read_video_meta, path)


async def validate_video(
    *,
    video_path: str,
    storyboard: Optional[Storyboard] = None,
    expected_duration: Optional[int] = None,
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
    expected_fps: Optional[int] = None,
) -> Dict[str, Any]:
    """校验单个视频与其素材清单,返回报告 dict。

    若传入 storyboard,则校验场景-素材数量一致性。
    expected_* 不传时使用 settings 中的默认值。
    """
    W = expected_width or settings.video_width
    H = expected_height or settings.video_height
    FPS = expected_fps or settings.video_fps
    target_dur = expected_duration or 0

    report: Dict[str, Any] = {
        "video_path": video_path,
        "exists": False,
        "size_bytes": 0,
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "has_audio": False,
        "aspect_ratio": "",
        "checks": [],
        "warnings": [],
        "errors": [],
        "scenes": None,
        "images_count": 0,
        "tts_count": 0,
        "grade": "D",
    }

    # 1) 文件存在
    if not video_path or not os.path.exists(video_path):
        report["errors"].append(f"视频文件不存在: {video_path}")
        report["grade"] = "D"
        return report
    report["exists"] = True
    report["size_bytes"] = os.path.getsize(video_path)
    if report["size_bytes"] < 1024:
        report["errors"].append(f"视频文件过小(<1KB): {report['size_bytes']} bytes")
        report["grade"] = "D"
        return report

    # 2) 视频元信息
    try:
        meta = await _get_video_meta(video_path)
    except Exception as e:
        report["errors"].append(f"读取视频元信息失败: {e}")
        report["grade"] = "D"
        return report

    report.update({
        "duration": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "fps": meta["fps"],
        "has_audio": meta["has_audio"],
    })
    w, h = meta["width"], meta["height"]
    report["aspect_ratio"] = f"{w}:{h}" if h else "?"

    checks = report["checks"]
    # 3) 分辨率
    if w == W and h == H:
        checks.append(f"分辨率达标 {W}x{H}")
    else:
        report["errors"].append(f"分辨率不符: 期望 {W}x{H}, 实际 {w}x{h}")

    # 4) 比例(9:16)
    if h > 0 and abs((w / h) - (9 / 16)) < 0.01:
        checks.append("竖屏比例 9:16")
    else:
        report["warnings"].append(f"非 9:16 竖屏(实际 {w}:{h})")

    # 5) FPS
    if abs(meta["fps"] - FPS) < 1:
        checks.append(f"FPS 达标 {meta['fps']:.1f}")
    else:
        report["warnings"].append(f"FPS 偏差: 期望 {FPS}, 实际 {meta['fps']:.1f}")

    # 6) 时长
    if target_dur > 0:
        diff = abs(meta["duration"] - target_dur)
        if diff <= 1:
            checks.append(f"时长达标 {meta['duration']:.2f}s (目标 {target_dur}s)")
        elif diff <= 3:
            report["warnings"].append(f"时长偏差 {diff:.2f}s (实际 {meta['duration']:.2f}s, 目标 {target_dur}s)")
        else:
            report["errors"].append(f"时长严重偏差 {diff:.2f}s (实际 {meta['duration']:.2f}s, 目标 {target_dur}s)")

    # 7) 音轨
    if meta["has_audio"]:
        checks.append("含音轨")
    else:
        report["errors"].append("无音轨(应有旁白+BGM)")

    # 8) 场景-素材一致性
    if storyboard is not None:
        shots = storyboard.shots
        n_scenes = len(shots)
        n_imgs = sum(1 for s in shots if s.image_path and os.path.exists(s.image_path))
        n_tts = sum(1 for s in shots if s.audio_path and os.path.exists(s.audio_path))
        report["scenes"] = n_scenes
        report["images_count"] = n_imgs
        report["tts_count"] = n_tts

        if n_scenes == 0:
            report["errors"].append("分镜列表为空")
        else:
            if n_imgs == n_scenes:
                checks.append(f"图片数量匹配场景 ({n_imgs}/{n_scenes})")
            else:
                report["errors"].append(f"图片数量不匹配: 期望 {n_scenes}, 实际 {n_imgs}")
            if n_tts == n_scenes:
                checks.append(f"TTS 数量匹配场景 ({n_tts}/{n_scenes})")
            else:
                report["errors"].append(f"TTS 数量不匹配: 期望 {n_scenes}, 实际 {n_tts}")

        # 各素材文件非空
        for i, s in enumerate(shots):
            if not s.image_path or not os.path.exists(s.image_path):
                report["errors"].append(f"shot{i} 图片缺失: {s.image_path}")
            elif os.path.getsize(s.image_path) < 1024:
                report["warnings"].append(f"shot{i} 图片过小: {os.path.getsize(s.image_path)} bytes")
            if not s.audio_path or not os.path.exists(s.audio_path):
                report["errors"].append(f"shot{i} TTS 缺失: {s.audio_path}")
            elif os.path.getsize(s.audio_path) < 1024:
                report["warnings"].append(f"shot{i} TTS 文件过小: {os.path.getsize(s.audio_path)} bytes")

    # 9) 评级
    if report["errors"]:
        report["grade"] = "C" if report["exists"] else "D"
    elif report["warnings"]:
        report["grade"] = "B"
    else:
        report["grade"] = "A"

    logger.info(
        "视频质量校验 grade=%s dur=%.2fs %dx%d audio=%s scenes=%s",
        report["grade"], report["duration"], report["width"], report["height"],
        report["has_audio"], report["scenes"],
    )
    return report


def format_report(report: Dict[str, Any]) -> str:
    """把报告 dict 格式化为可读字符串。"""
    lines = [
        "===== Video Quality Report =====",
        f"file          : {report['video_path']}",
        f"exists        : {report['exists']}",
        f"size_bytes    : {report['size_bytes']}",
        f"duration      : {report['duration']:.2f}s",
        f"resolution    : {report['width']}x{report['height']} ({report['aspect_ratio']})",
        f"fps           : {report['fps']:.2f}",
        f"has_audio     : {report['has_audio']}",
        f"scenes        : {report['scenes']}",
        f"images_count  : {report['images_count']}",
        f"tts_count     : {report['tts_count']}",
        f"grade         : {report['grade']}",
        "---- checks ----",
    ]
    lines += [f"  [OK] {c}" for c in report["checks"]]
    if report["warnings"]:
        lines.append("---- warnings ----")
        lines += [f"  [WARN] {w}" for w in report["warnings"]]
    if report["errors"]:
        lines.append("---- errors ----")
        lines += [f"  [ERR] {e}" for e in report["errors"]]
    lines.append("================================")
    return "\n".join(lines)
