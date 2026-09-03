"""Video Assembly:用 MoviePy 2.x 把图片+字幕+旁白+BGM 拼成最终 MP4。

第五阶段升级:
- 9:16 竖屏输出(尺寸从 VideoConfig 读取,不硬编码)
- 中文逐句字幕(msyh.ttc + auto-wrap + 半透明背景条 + 时间对齐)
- 转场(镜头间 fade to black,可配置时长)
- Ken Burns 运镜(resize + pan 组合,7 种镜头运动:push in/out、pan left/right、tilt up/down、crane up)
- BGM 音量从 config 读取

设计取舍:
- 字幕用 Pillow 渲染为透明 RGBA overlay,CompositeVideoClip 叠加,不受 Resize 影响
- 不依赖 MoviePy TextClip(需 ImageMagick,Windows 配置麻烦)
- write_videofile 阻塞操作用 asyncio.to_thread 包裹
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import textwrap
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..core.config import settings
from ..schemas.storyboard import StoryboardShot

logger = logging.getLogger("ai_video_agent")


def _split_sentences(text: str) -> List[str]:
    """按中文标点分割句子,返回非空片段列表。"""
    parts = re.split(r"[。！？，；\n]", text)
    return [p.strip() for p in parts if p.strip()]


def _apply_ken_burns(clip, motion: str, duration: int, W: int, H: int):
    """对 ImageClip 应用 Ken Burns 运镜(resize + pan 组合),让静态图有电影运镜感。

    分类(按关键词优先级,复合动作取首个识别):
    - push in / dolly forward / zoom in / rack focus: 放大 1.0→1.18 突出主体
    - pull out / zoom out / crane back / crane down: 缩小 1.18→1.0 交代环境
    - pan right: 固定 1.15 + 水平向左移(镜头向右扫)
    - pan left: 固定 1.15 + 水平向右移(镜头向左扫)
    - tilt down: 固定 1.15 + 垂直向下移(镜头向下扫)
    - tilt up: 固定 1.15 + 垂直向上移(镜头向上扫)
    - crane up: 固定 1.15 + 缓慢上升
    - pan(无方向)/ 未识别关键词: 默认 pan right
    - static: 固定 1.05 微放大避免黑边

    设计取舍:
    - 动态 scale 运镜(push in/out)用 position center 居中,放大不会黑边
    - 动态 position 运镜(pan/tilt)用固定 scale 1.15,图片始终比画布大 15% 保证不黑边
    """
    from moviepy import vfx

    m = (motion or "").lower()
    d = max(duration, 1)
    extra_w = int(W * 0.15)  # 图片放大 15% 多出的宽
    extra_h = int(H * 0.15)  # 图片放大 15% 多出的高

    # 放大突出主体(push in / dolly forward / zoom in / rack focus)
    if any(k in m for k in ["push in", "dolly forward", "zoom in", "rack focus"]):
        return clip.with_effects([vfx.Resize(new_size=lambda t: 1.0 + 0.18 * (t / d))]).with_position(("center", "center"))
    # 缩小交代环境(pull out / zoom out / crane back / crane down)
    if any(k in m for k in ["pull out", "pull back", "zoom out", "crane back", "crane down"]):
        return clip.with_effects([vfx.Resize(new_size=lambda t: 1.18 - 0.18 * (t / d))]).with_position(("center", "center"))
    # pan right: 镜头向右扫,图片向左移(x: 0 → -extra_w)
    if "pan right" in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-int(extra_w * (t / d)), -extra_h // 2))
    # pan left: 镜头向左扫,图片向右移(x: -extra_w → 0)
    if "pan left" in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-int(extra_w * (1 - t / d)), -extra_h // 2))
    # tilt down: 镜头向下扫,图片向上移(y: 0 → -extra_h)
    if "tilt down" in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-extra_w // 2, -int(extra_h * (t / d))))
    # tilt up: 镜头向上扫,图片向下移(y: -extra_h → 0)
    if "tilt up" in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-extra_w // 2, -int(extra_h * (1 - t / d))))
    # crane up: 摄像机上升,图片向下移(y: 0 → -extra_h*0.5)
    if "crane up" in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-extra_w // 2, -int(extra_h * 0.5 * (t / d))))
    # 默认 pan right(含未指明方向的 pan 关键词)
    if "pan" in m or not m or "static" not in m:
        return clip.with_effects([vfx.Resize(new_size=1.15)]).with_position(lambda t: (-int(extra_w * (t / d)), -extra_h // 2))
    # static: 固定 1.05 微放大避免黑边
    return clip.with_effects([vfx.Resize(new_size=1.05)]).with_position(("center", "center"))


def _make_subtitle_array(text: str, W: int, H: int, font_size: int = 0) -> np.ndarray:
    """渲染单句字幕为 RGBA numpy 数列(透明背景 + 半透明黑条 + 白字)。

    font_size: >0 时覆盖全局默认(逐镜头字幕字号)。
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fs = font_size or settings.subtitle_font_size
    try:
        font = ImageFont.truetype(settings.subtitle_font_path, fs)
    except OSError:
        font = ImageFont.load_default()
    max_chars = max(8, (W - 60) // fs)
    lines = textwrap.wrap(text, width=max_chars) or [text]
    if len(lines) > 2:
        lines = [lines[0], "".join(lines[1:])[:max_chars - 1] + "…"]

    line_h = fs + 8
    block_h = len(lines) * line_h + 16
    y_start = H - block_h - 50  # 底部留 50px margin

    bg = Image.new("RGBA", (W, block_h), (0, 0, 0, 140))
    img.paste(bg, (0, y_start), bg)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = y_start + 8 + i * line_h
        draw.text((x, y), line, fill=(255, 255, 255), font=font)

    return np.array(img)


def _build_video_sync(
    *, shots: List[StoryboardShot], bgm_path: str, output_path: str, title: str
) -> str:
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )

    W = settings.video_width
    H = settings.video_height
    FPS = settings.video_fps
    TRANS = settings.transition_duration

    all_clips: list = []
    for i, shot in enumerate(shots):
        d = max(shot.duration, 1)

        # 1) 加载基础片段:优先 I2V 动态视频(真实连续动作),回退到图片+Ken Burns
        if shot.video_path and os.path.exists(shot.video_path):
            # I2V 模式:用动态视频片段,不再需要 Ken Burns(I2V 本身有连续动作)
            base = VideoFileClip(shot.video_path)
            if base.size != (W, H):
                base = base.with_effects([vfx.Resize(new_size=(W, H))])
            if base.duration > d:
                base = base.subclipped(0, d)
            elif base.duration < d:
                base = base.with_duration(d)
            logger.info("shot%d: 使用 I2V 动态视频片段(%.2fs)", i, base.duration)
        else:
            # 回退:图片 + Ken Burns 运镜(resize + pan 组合)
            pil_img = Image.open(shot.image_path).convert("RGB")
            pil_img = pil_img.resize((W, H), Image.LANCZOS)
            base = ImageClip(np.array(pil_img), duration=d)
            base = _apply_ken_burns(base, shot.camera_movement, d, W, H)

        # 3) 逐句字幕 overlay(优先 subtitle 字段,回退 voiceover;逐镜头开关+字号)
        clips_for_shot = [base]
        subtitle_text = shot.subtitle or shot.voiceover or shot.visual_description or ""
        if subtitle_text and shot.subtitle_enabled:
            sentences = _split_sentences(subtitle_text)
            n = len(sentences)
            if n > 0:
                seg_dur = d / n
                for j, sent in enumerate(sentences):
                    sub_arr = _make_subtitle_array(sent, W, H, font_size=shot.subtitle_font_size or 0)
                    sc = ImageClip(sub_arr, duration=seg_dur).with_start(j * seg_dur)
                    clips_for_shot.append(sc)

        # 4) 合成为目标尺寸的片段
        shot_clip = CompositeVideoClip(clips_for_shot, size=(W, H))

        # 5) 转场:根据 transition 字段选择(cut = 硬切,其余 = fade)
        trans = (shot.transition or "fade").lower()
        effects = []
        if i > 0 and trans != "cut":
            effects.append(vfx.FadeIn(TRANS))
        if i < len(shots) - 1 and trans != "cut":
            effects.append(vfx.FadeOut(TRANS))
        if effects:
            shot_clip = shot_clip.with_effects(effects)

        all_clips.append(shot_clip)

    video = concatenate_videoclips(all_clips, method="compose")

    # 6) 音轨(时间轴语义):旁白按各自镜头的起始时刻对齐放置,不再顺序拼接
    #    (消除"旁白时长≠镜头时长"时的累积漂移;超长旁白自然跨入下一镜头)
    audio_clips: list = []
    t_cursor = 0.0
    for shot in shots:
        if shot.audio_path and os.path.exists(shot.audio_path):
            narr = AudioFileClip(shot.audio_path).with_start(t_cursor)
            audio_clips.append(narr)
        t_cursor += max(shot.duration, 1)

    bgm = None
    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path).with_volume_scaled(settings.bgm_volume)
        if bgm.duration < video.duration:
            bgm = bgm.with_effects([vfx.AudioLoop(duration=video.duration)])
        else:
            bgm = bgm.subclipped(0, video.duration)

    if bgm is not None:
        audio_clips.append(bgm)
    final_audio = CompositeAudioClip(audio_clips) if audio_clips else None

    if final_audio is not None:
        video = video.with_audio(final_audio)

    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    logger.info("视频合成完成: %s (%s)", output_path, f"{W}x{H}")
    return output_path


class VideoAssembler:
    async def assemble(
        self,
        *,
        shots: List[StoryboardShot],
        bgm_path: str,
        output_path: str,
        title: str = "",
    ) -> str:
        return await asyncio.to_thread(
            _build_video_sync,
            shots=shots,
            bgm_path=bgm_path,
            output_path=output_path,
            title=title,
        )


def get_video_assembler() -> VideoAssembler:
    return VideoAssembler()
