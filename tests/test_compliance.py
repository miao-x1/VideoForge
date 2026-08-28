"""Compliance Agent 测试套件(10 用例 + 集成)。

直接运行(无需 pytest):
  python tests/test_compliance.py

覆盖:
 1. 正常历史科普脚本 -> PASS
 2. 明显违法内容 -> REJECT
 3. 医疗绝对化承诺 -> REJECT
 4. 危险行为描述但属历史叙述 -> 上下文判断(不靠关键词)
 5. 模糊边界内容 -> REVIEW
 6. 修改后的安全脚本 -> PASS
 7. Compliance JSON 格式异常 -> 正确处理(降级 review,不崩)
 8. LLM 调用失败 -> 降级 review + 人工(不自动放行)
 9. 多次修订仍不通过 -> HUMAN_REVIEW
 10. 不破坏原有视频生成 Pipeline(Mock 全流程仍产出 MP4)
"""
from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.normpath(os.path.join(_HERE, "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.compliance import TextComplianceAgent, ScriptRevisionAgent  # noqa: E402
from app.compliance.rule_engine import RuleEngine  # noqa: E402
from app.models.state import TaskStatus, VideoGenerationState  # noqa: E402
from app.orchestrator.orchestrator import Orchestrator  # noqa: E402
from app.providers.llm.base import LLMProvider  # noqa: E402
from app.providers.llm.mock_llm import MockLLMProvider  # noqa: E402
from app.providers.image.mock_image import MockImageProvider  # noqa: E402
from app.providers.voice.mock_voice import MockVoiceProvider  # noqa: E402
from app.providers.music.mock_music import MockMusicProvider  # noqa: E402
from app.providers.video.mock_i2v import MockI2VProvider  # noqa: E402
from app.schemas.script import ScriptScene, VideoScript  # noqa: E402


# ---------- 辅助 ----------

def _script(title: str, voiceover: str, visual: str = "", dialogue: str = "") -> VideoScript:
    return VideoScript(
        title=title,
        hook="",
        scenes=[ScriptScene(scene_id=1, duration=5, location="场景", characters=[],
                             visual=visual, dialogue=dialogue, voiceover=voiceover)],
        ending=None,
    )


class FakeLLM(LLMProvider):
    """可编程 LLM,用于离线测试 compliance_check / script_revision 的语义路径。"""

    def __init__(self, *, compliance_resp=None, revision_resp=None,
                 raise_on=None, malform=False):
        self.compliance_resp = compliance_resp
        self.revision_resp = revision_resp
        self.raise_on = set(raise_on or [])
        self.malform = malform
        self.model = "fake-qwen"

    async def generate(self, *, task: str, context: dict):
        if task in self.raise_on:
            raise RuntimeError(f"fake failure on {task}")
        if task == "compliance_check":
            if self.malform:
                return {"status": 123, "risk_level": "bogus", "overall_score": "x"}
            return dict(self.compliance_resp) if self.compliance_resp is not None else {
                "status": "pass", "risk_level": "low", "overall_score": 95,
            }
        if task == "script_revision":
            if self.revision_resp is not None:
                return dict(self.revision_resp)
            return dict(context.get("original_script") or {})
        raise ValueError(f"fake: unknown task {task}")


# ---------- 用例 ----------

async def t1_normal_history_pass():
    agent = TextComplianceAgent(llm=FakeLLM(compliance_resp={
        "status": "pass", "risk_level": "low", "overall_score": 96,
        "violations": [], "warnings": [], "matched_rules": [],
        "explanation": "历史科普,无风险", "revision_suggestions": [],
    }))
    r = await agent.check({"script": _script("唐朝历史科普", "唐玄宗开创开元盛世"), "topic": "唐朝历史"})
    assert r.status == "pass", f"应 pass,实际 {r.status}"


async def t2_illegal_reject():
    # 确定性规则 COM-001 命中(关键词教学) + Mock 语义
    agent = TextComplianceAgent(llm=MockLLMProvider())
    r = await agent.check({"script": _script("制毒教程", "教人如何制毒的步骤"), "topic": "制毒"})
    assert r.status == "reject", f"应 reject,实际 {r.status}"
    assert "COM-001" in r.matched_rules


async def t3_medical_absolute_reject():
    agent = TextComplianceAgent(llm=MockLLMProvider())
    r = await agent.check({"script": _script("神药", "我们的药100%治愈癌症,包治百病"), "topic": "医疗"})
    assert r.status == "reject", f"应 reject,实际 {r.status}"
    assert "COM-006" in r.matched_rules


async def t4_danger_historical_context():
    # 文本含"战场"但属历史叙述,无规则模式命中;FakeLLM 做上下文判断 -> pass(不是关键词黑名单)
    agent = TextComplianceAgent(llm=FakeLLM(compliance_resp={
        "status": "pass", "risk_level": "low", "overall_score": 90,
        "explanation": "历史战争叙述,非鼓励现实暴力",
    }))
    r = await agent.check({"script": _script("长平之战", "长平之战是战国时期著名战役"), "topic": "历史"})
    assert r.status == "pass", f"历史叙述不应被判违规,实际 {r.status}"


async def t5_ambiguous_review():
    agent = TextComplianceAgent(llm=FakeLLM(compliance_resp={
        "status": "review", "risk_level": "medium", "overall_score": 55,
        "human_review_required": True, "review_reason": "边界议题",
        "explanation": "边界内容,需人工",
    }))
    r = await agent.check({"script": _script("争议话题", "某个有争议的社会现象讨论"), "topic": "社会"})
    assert r.status == "review", f"应 review,实际 {r.status}"
    assert r.human_review_required


async def t6_revised_safe_pass():
    # 修订后的安全脚本(无规则命中 + Mock 语义 pass)
    agent = TextComplianceAgent(llm=MockLLMProvider())
    r = await agent.check({"script": _script("健康饮食", "均衡饮食有益健康"), "topic": "健康"})
    assert r.status == "pass", f"修订后应 pass,实际 {r.status}"


async def t7_malformed_json():
    agent = TextComplianceAgent(llm=FakeLLM(malform=True))
    r = await agent.check({"script": _script("x", "内容"), "topic": "x"})
    assert r.status == "review", f"格式异常应降级 review,实际 {r.status}"
    assert r.human_review_required, "格式异常必须人工审核(不自动放行)"


async def t8_llm_failure_degrade():
    agent = TextComplianceAgent(llm=FakeLLM(raise_on={"compliance_check"}))
    r = await agent.check({"script": _script("x", "内容"), "topic": "x"})
    assert r.status == "review", f"LLM 失败应降级 review,实际 {r.status}"
    assert r.human_review_required, "LLM 失败必须人工审核(不自动放行)"
    assert r.review_reason == "compliance_check_failed"


async def t9_revision_exhausted_human_review():
    # Fake: compliance 一直 reject;revision 原样返回 -> 复检仍 reject -> 耗尽 -> HUMAN_REVIEW
    reject_resp = {
        "status": "reject", "risk_level": "high", "overall_score": 20,
        "violations": [{"rule_id": "COM-006", "category": "medical_falsehood",
                        "severity": "high", "evidence": "100%治愈", "explanation": "绝对化医疗承诺"}],
        "warnings": [], "matched_rules": ["COM-006"],
        "explanation": "医疗绝对化", "revision_suggestions": ["移除绝对化表述"],
        "human_review_required": True, "review_reason": "medical",
    }
    fake = FakeLLM(compliance_resp=reject_resp)  # revision 默认原样返回
    orch = Orchestrator(llm=fake, image=MockImageProvider(), voice=MockVoiceProvider(),
                        music=MockMusicProvider(), video=MockI2VProvider())
    state = VideoGenerationState(
        user_input="违规医疗", duration=10, style="医疗",
        script=_script("神药", "100%治愈癌症"),
    )
    await orch._run_compliance(state)
    assert state.status == TaskStatus.HUMAN_REVIEW, f"应 HUMAN_REVIEW,实际 {state.status}"
    assert state.human_review_required
    from app.core.config import settings as s
    assert state.revision_count == s.compliance_max_revisions, \
        f"修订次数应={s.compliance_max_revisions},实际 {state.revision_count}"


async def t10_pipeline_not_broken():
    # 全 Mock:合规开启 + 良性主题 -> pass -> 走完原 Pipeline 仍产出 MP4
    orch = Orchestrator(
        llm=MockLLMProvider(),
        image=MockImageProvider(),
        voice=MockVoiceProvider(),
        music=MockMusicProvider(),
        video=MockI2VProvider(),
    )
    state = VideoGenerationState(
        user_input="假如古代人有手机,做一个10秒轻松搞笑的短视频。",
        duration=10, style="轻松搞笑",
    )
    await orch.execute(state)
    assert state.status.value == "COMPLETED", f"原 Pipeline 应完成,实际 {state.status} err={state.error}"
    assert state.video_path and os.path.exists(state.video_path), f"MP4 不存在: {state.video_path}"
    assert state.compliance_report is not None, "应产出 compliance_report"
    assert state.compliance_report.get("status") == "pass", \
        f"良性主题应 pass,实际 {state.compliance_report.get('status')}"
    assert state.content_guard_report is not None, "原 ContentGuard 阶段仍应运行"


# ---------- runner ----------

TESTS = [
    ("1.正常科普->PASS", t1_normal_history_pass),
    ("2.违法内容->REJECT", t2_illegal_reject),
    ("3.医疗绝对化->REJECT", t3_medical_absolute_reject),
    ("4.危险历史叙述->上下文判断", t4_danger_historical_context),
    ("5.模糊边界->REVIEW", t5_ambiguous_review),
    ("6.修订后安全->PASS", t6_revised_safe_pass),
    ("7.JSON格式异常->正确处理", t7_malformed_json),
    ("8.LLM失败->降级", t8_llm_failure_degrade),
    ("9.多次修订不通过->HUMAN_REVIEW", t9_revision_exhausted_human_review),
    ("10.原Pipeline不破坏", t10_pipeline_not_broken),
]


def main() -> None:
    print("=" * 60)
    print("Compliance Agent 测试套件")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            asyncio.run(fn())
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 60)
    print(f"结果: {passed} 通过 / {failed} 失败 / 共 {len(TESTS)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
