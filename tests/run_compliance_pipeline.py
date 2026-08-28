"""真实 Pipeline 验收:Compliance Agent + 完整视频生成。

创意:假如古代人第一次点外卖(良性主题,合规应 pass)
流程:requirement -> script -> [compliance check -> 必要时 revision -> 复检] -> storyboard -> media -> assembly
真实 Provider:DashScope LLM(qwen-plus)/ 文生图 / I2V / TTS / ambient BGM / Compliance 复用 LLM

打印:合规报告(每次审核) + 视频质量 + 最终汇总。
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


async def _timed(name, coro, timings):
    t0 = time.perf_counter()
    try:
        await coro
    except Exception as e:
        timings.append({"stage": name, "status": "FAIL", "elapsed_s": round(time.perf_counter() - t0, 2),
                        "error": f"{type(e).__name__}: {e}"})
        raise
    timings.append({"stage": name, "status": "OK", "elapsed_s": round(time.perf_counter() - t0, 2), "error": None})
    print(f"  [{name}] OK {timings[-1]['elapsed_s']:.2f}s")


def _print_compliance(state):
    rep = state.compliance_report
    print("\n" + "=" * 60)
    print("Compliance 合规报告(脚本级)")
    print("=" * 60)
    if not rep:
        print("未生成合规报告")
        return
    print(f"status              : {rep.get('status')}")
    print(f"risk_level          : {rep.get('risk_level')}")
    print(f"overall_score       : {rep.get('overall_score')}")
    print(f"human_review_required: {rep.get('human_review_required')}")
    print(f"revision_count      : {state.revision_count} (max={settings.compliance_max_revisions})")
    vs = rep.get("violations") or []
    ws = rep.get("warnings") or []
    print(f"violations ({len(vs)}):")
    for v in vs:
        print(f"  - [{v.get('rule_id')}] {v.get('category')} sev={v.get('severity')} 证据={v.get('evidence')}")
    print(f"warnings ({len(ws)}):")
    for w in ws:
        print(f"  - [{w.get('rule_id')}] {w.get('category')} 证据={w.get('evidence')}")
    print(f"matched_rules       : {rep.get('matched_rules')}")
    print(f"explanation         : {rep.get('explanation')}")
    sug = rep.get("revision_suggestions") or []
    if sug:
        print("revision_suggestions:")
        for s in sug:
            print(f"  - {s}")
    print(f"audit 记录数        : {len(state.compliance_audit)} (落盘 storage/audit/compliance_audit.jsonl)")


async def main():
    print("=" * 60)
    print("Compliance Agent 真实 Pipeline 验收")
    print("=" * 60)
    print(f"创意: {CREATIVE}")
    print(f"配置: COMPLIANCE_CHECK_ENABLED={settings.compliance_check_enabled} "
          f"MAX_REVISIONS={settings.compliance_max_revisions} LLM={settings.llm_model}")

    state = task_store.create(user_input=CREATIVE, duration=DURATION_TARGET, style="轻松搞笑")
    print(f"[run] task_id={state.task_id}")
    timings = []
    t0 = time.perf_counter()

    try:
        await _timed("requirement", orchestrator._run_requirement(state), timings)
        await _timed("script", orchestrator._run_script(state), timings)
        await _timed("compliance", orchestrator._run_compliance(state), timings)
        # 合规阶段一结束立即打印报告(不等视频生成)
        _print_compliance(state)
        if state.status.value == "HUMAN_REVIEW":
            print("\n[run] 合规未通过且修订耗尽,进入人工审核,停止视频生成")
        else:
            await _timed("storyboard", orchestrator._run_storyboard(state), timings)
            await _timed("content_guard", orchestrator._run_content_guard(state), timings)
            await _timed("media", orchestrator._run_media(state), timings)
            await _timed("assembly", orchestrator._run_assembly(state), timings)
    except Exception as e:
        print(f"[run] Pipeline 失败: {e}")
        state.mark_failed(f"{type(e).__name__}: {e}")
        task_store.save(state)

    overall = time.perf_counter() - t0
    print(f"\n[run] 总耗时: {overall:.2f}s")

    # 性能
    print("\n" + "=" * 60)
    print("阶段耗时")
    print("=" * 60)
    for t in timings:
        flag = "OK" if t["status"] == "OK" else "FAIL"
        print(f"  - {t['stage']:12s} {flag:5s} {t['elapsed_s']:7.2f}s {t['error'] or ''}")

    # 视频质量
    quality = None
    if state.status.value == "COMPLETED" and state.video_path and os.path.exists(state.video_path):
        print("\n" + "=" * 60)
        print("视频质量报告")
        print("=" * 60)
        quality = await validate_video(video_path=state.video_path, storyboard=state.storyboard, expected_duration=DURATION_TARGET)
        print(format_report(quality))

    # 最终汇总
    print("\n" + "=" * 60)
    print("最终汇总")
    print("=" * 60)
    rep = state.compliance_report or {}
    print(f"1. Compliance   : status={rep.get('status')} risk={rep.get('risk_level')} "
          f"score={rep.get('overall_score')} 修订={state.revision_count}")
    print(f"2. ContentGuard : {state.content_guard_report.get('overall_risk') if state.content_guard_report else 'N/A'}")
    print(f"3. 视频生成     : {state.status.value} {state.video_path or ''}")
    if quality:
        print(f"4. 视频质量     : 评级 {quality.get('grade')} {quality.get('duration')}s "
              f"{quality.get('width')}x{quality.get('height')} {quality.get('fps')}fps 音频={quality.get('has_audio')}")
    print(f"5. 总耗时       : {overall:.2f}s")

    # 落盘
    if state.video_path or rep:
        out = os.path.join(os.path.dirname(state.video_path or __file__),
                           f"{state.task_id}_compliance_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": state.task_id, "creative": CREATIVE, "status": state.status.value,
                "video_path": state.video_path, "timings": timings, "overall_s": round(overall, 2),
                "compliance": rep, "compliance_audit_count": len(state.compliance_audit),
                "revision_count": state.revision_count, "content_guard": state.content_guard_report,
                "quality": quality,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[run] 报告已保存: {out}")


if __name__ == "__main__":
    asyncio.run(main())
