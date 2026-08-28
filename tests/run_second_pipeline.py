"""第三次真实 Pipeline 验收:中文 TTS + ContentGuard + 视频质量。

创意:假如古代人第一次点外卖,做一个30秒轻松搞笑的短视频
真实 Provider:
- LLM:       qwen-plus(OpenAI 兼容,storyboard 按配置生成中文 voiceover)
- 文生图:    wanx2.1-t2i-turbo(通义万相)
- I2V:       wan2.6-i2v-flash(真实连续动作)
- TTS:       qwen-audio-3.0-tts-flash + longanhuan_v3.6(中文女声旁白)
- BGM:       ambient(程序化)
- ContentGuard: 复用 LLM,三维度风险预检查(安全/平台/文化历史)

逐阶段记录耗时,完成后调用 Video Quality Validator 输出报告,
并汇总中文 TTS / ContentGuard / 视频质量 / 总耗时 / 优化建议。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.core.config import settings  # noqa: E402
from app.orchestrator.orchestrator import orchestrator  # noqa: E402
from app.services.task_service import task_store  # noqa: E402
from app.video.quality import validate_video, format_report  # noqa: E402

CREATIVE = "假如古代人第一次点外卖，做一个30秒轻松搞笑的短视频。"
DURATION_TARGET = 30


async def _timed(name: str, coro, timings: list) -> None:
    """包裹一个阶段协程,记录耗时。"""
    t0 = time.perf_counter()
    status = "OK"
    err = None
    try:
        await coro
    except Exception as e:
        status = "FAIL"
        err = f"{type(e).__name__}: {e}"
        raise
    finally:
        elapsed = time.perf_counter() - t0
        timings.append({"stage": name, "status": status, "elapsed_s": round(elapsed, 2), "error": err})
        print(f"  [{name}] {status} {elapsed:.2f}s")


async def run_pipeline_with_timing() -> dict:
    """按阶段执行 Pipeline 并记录耗时,返回结果汇总。"""
    state = task_store.create(
        user_input=CREATIVE,
        duration=DURATION_TARGET,
        style="轻松搞笑",
    )
    print(f"[run] task_id={state.task_id}")
    print(f"[run] 创意: {CREATIVE}")
    print(f"[run] 配置: LLM={orchestrator.requirement_agent.llm.__class__.__name__} "
          f"Image={orchestrator.image.__class__.__name__} "
          f"Voice={orchestrator.voice.__class__.__name__} "
          f"Music={orchestrator.music.__class__.__name__}")

    timings: list = []
    overall_t0 = time.perf_counter()

    try:
        await _timed("requirement", orchestrator._run_requirement(state), timings)
        await _timed("script", orchestrator._run_script(state), timings)
        await _timed("storyboard", orchestrator._run_storyboard(state), timings)
        await _timed("content_guard", orchestrator._run_content_guard(state), timings)
        await _timed("media", orchestrator._run_media(state), timings)
        await _timed("assembly", orchestrator._run_assembly(state), timings)
    except Exception as e:
        print(f"[run] Pipeline 失败: {e}")
        state.mark_failed(f"{type(e).__name__}: {e}")
        task_store.save(state)

    overall = time.perf_counter() - overall_t0
    print(f"[run] 总耗时: {overall:.2f}s")

    # 导出 storyboard 清单(便于复现)
    if state.storyboard:
        prompts_file = os.path.join(os.path.dirname(state.video_path or ""), f"{state.task_id}_prompts.json")
        shots_info = [
            {
                "index": i,
                "image_path": s.image_path,
                "audio_path": s.audio_path,
                "image_prompt": s.image_prompt,
                "duration": s.duration,
                "voiceover": s.voiceover,
                "visual_description": s.visual_description,
                "subtitle": s.subtitle,
                "transition": s.transition,
                "emotion": s.emotion,
                "camera_movement": s.camera_movement,
            }
            for i, s in enumerate(state.storyboard.shots)
        ]
        bgm_path = state.assets[-1] if state.assets else ""
        with open(prompts_file, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": state.task_id,
                "bgm_path": bgm_path,
                "title": state.script.title if state.script else "",
                "shots": shots_info,
            }, f, ensure_ascii=False, indent=2)
        print(f"[run] storyboard 清单已导出: {prompts_file}")

    return {
        "task_id": state.task_id,
        "status": state.status.value,
        "video_path": state.video_path,
        "timings": timings,
        "overall_s": round(overall, 2),
        "state": state,
    }


def _is_mostly_chinese(text: str) -> bool:
    """简单判断文本是否以中文为主(用于校验 voiceover 是否中文)。"""
    if not text:
        return False
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return cn > 0 and cn >= len(text.strip()) * 0.3


def _print_content_guard_report(state) -> None:
    """打印 ContentGuard 风险评估报告。"""
    print("=" * 60)
    print("ContentGuard 风险报告")
    print("=" * 60)
    rep = getattr(state, "content_guard_report", None)
    if not rep:
        print("未生成 ContentGuard 报告")
        return
    print(f"safe          : {rep.get('safe')}")
    print(f"overall_risk  : {rep.get('overall_risk')}")
    print(f"safety_risk   : {rep.get('safety_risk')}")
    print(f"platform_risk : {rep.get('platform_risk')}")
    print(f"cultural_risk : {rep.get('cultural_risk')}")
    warnings = rep.get("warnings") or []
    suggestions = rep.get("suggestions") or []
    print(f"warnings ({len(warnings)}):")
    for w in warnings:
        print(f"  - {w}")
    print(f"suggestions ({len(suggestions)}):")
    for s in suggestions:
        print(f"  - {s}")


def _print_final_summary(*, state, result, quality_report) -> None:
    """按用户要求输出最终汇总报告(6 项)。"""
    print()
    print("=" * 60)
    print("最终汇总报告")
    print("=" * 60)

    # 1. 中文 TTS 是否成功
    cn_ok = False
    cn_samples = []
    if state.storyboard and state.storyboard.shots:
        cn_samples = [s.voiceover for s in state.storyboard.shots if s.voiceover]
        cn_ok = bool(cn_samples) and all(_is_mostly_chinese(v) for v in cn_samples)
    print(f"1. 中文 TTS   : {'成功' if cn_ok else '失败'} (TTS_LANGUAGE={settings.tts_language}, "
          f"voice={settings.tts_voice})")
    if cn_samples:
        print(f"   voiceover 样本: {cn_samples[0][:40]}...")

    # 2. ContentGuard 是否成功
    cg_rep = getattr(state, "content_guard_report", None)
    cg_ok = bool(cg_rep) and "overall_risk" in cg_rep
    print(f"2. ContentGuard: {'成功' if cg_ok else '失败'} "
          f"(overall={cg_rep.get('overall_risk') if cg_rep else 'N/A'}, "
          f"safe={cg_rep.get('safe') if cg_rep else 'N/A'})")

    # 3. 视频是否成功
    vid_ok = state.status.value == "COMPLETED" and bool(state.video_path) and os.path.exists(state.video_path or "")
    print(f"3. 视频生成   : {'成功' if vid_ok else '失败'} "
          f"(status={state.status.value}, path={state.video_path})")

    # 4. 视频质量评级
    grade = "N/A"
    if quality_report:
        grade = quality_report.get("grade", "N/A")
        dur = quality_report.get("duration")
        res = f"{quality_report.get('width')}x{quality_report.get('height')}"
        fps = quality_report.get("fps")
        audio = quality_report.get("has_audio")
        print(f"4. 视频质量   : 评级 {grade} (时长={dur}s, 分辨率={res}, fps={fps}, 音频={audio})")

    # 5. 总耗时
    print(f"5. 总耗时     : {result['overall_s']:.2f}s "
          f"(目标 {DURATION_TARGET}s 视频)")
    total_stage = sum(t["elapsed_s"] for t in result["timings"])
    slow = sorted(result["timings"], key=lambda x: -x["elapsed_s"])[:2]
    slow_str = ", ".join(f"{t['stage']}={t['elapsed_s']:.1f}s" for t in slow)
    print(f"   阶段累计   : {total_stage:.2f}s, 最慢: {slow_str}")

    # 6. 当前最值得优化的问题
    print("6. 当前最值得优化的问题:")
    issues = []
    if not cn_ok:
        issues.append("voiceover 仍含英文/非中文,需加强 STORYBOARD_PROMPT 语言约束或校验重试")
    if quality_report:
        dur = quality_report.get("duration") or 0
        if abs(dur - DURATION_TARGET) > 3:
            issues.append(f"视频时长 {dur}s 偏离目标 {DURATION_TARGET}s,"
                          f"TTS 时长同步逻辑(orchestrator.py shot.duration)需加下限保护")
        if quality_report.get("grade") in ("C", "D"):
            warns = quality_report.get("warnings") or []
            issues.append(f"质量评级 {quality_report.get('grade')} 偏低,"
                          f"主因: {'; '.join(warns[:2]) if warns else 'I2V fallback 比例/分辨率/音频'}")
    n_i2v = sum(1 for s in (state.storyboard.shots if state.storyboard else []) if s.video_path)
    n_total = len(state.storyboard.shots) if state.storyboard else 0
    if n_total and n_i2v < n_total:
        issues.append(f"I2V 成功 {n_i2v}/{n_total},部分镜头 fallback 到 Ken Burns,影响动态连贯性")
    if not issues:
        issues.append("暂无显著问题,可考虑优化:并行生成多镜头素材以降低总耗时")
    for i, msg in enumerate(issues, 1):
        print(f"   {i}. {msg}")


async def main() -> None:
    print("=" * 60)
    print("第三次真实 Pipeline 验收:中文 TTS + ContentGuard")
    print("=" * 60)
    print(f"创意: {CREATIVE}")
    print(f"配置: TTS_LANGUAGE={settings.tts_language} TTS_VOICE={settings.tts_voice} "
          f"I2V_PROVIDER={settings.i2v_provider}")
    result = await run_pipeline_with_timing()

    print()
    print("=" * 60)
    print("Pipeline 性能报告")
    print("=" * 60)
    print(f"task_id      : {result['task_id']}")
    print(f"status       : {result['status']}")
    print(f"overall_s    : {result['overall_s']:.2f}")
    print("阶段耗时:")
    total = 0.0
    for t in result["timings"]:
        flag = "OK" if t["status"] == "OK" else "FAIL"
        print(f"  - {t['stage']:12s} {flag:5s} {t['elapsed_s']:7.2f}s {t['error'] or ''}")
        total += t["elapsed_s"]
    print(f"  - {'sum':12s}       {total:7.2f}s")

    state = result["state"]

    # ContentGuard 报告(无论视频是否成功都打印,证明预检查阶段已运行)
    print()
    _print_content_guard_report(state)

    # 视频质量报告
    quality_report = None
    if state.status.value == "COMPLETED" and state.video_path and state.storyboard:
        print()
        print("=" * 60)
        print("视频质量报告")
        print("=" * 60)
        quality_report = await validate_video(
            video_path=state.video_path,
            storyboard=state.storyboard,
            expected_duration=DURATION_TARGET,
        )
        print(format_report(quality_report))

    # 最终汇总报告(6 项)
    _print_final_summary(state=state, result=result, quality_report=quality_report)

    # 保存完整报告到文件
    if state.video_path:
        report_path = os.path.join(os.path.dirname(state.video_path), f"{state.task_id}_final_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": state.task_id,
                "creative": CREATIVE,
                "status": state.status.value,
                "video_path": state.video_path,
                "timings": result["timings"],
                "overall_s": result["overall_s"],
                "content_guard": state.content_guard_report,
                "quality": quality_report,
                "tts_language": settings.tts_language,
                "tts_voice": settings.tts_voice,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[run] 完整报告已保存: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
