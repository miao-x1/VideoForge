"""Orchestrator:统一编排整个 Agent Pipeline。

职责:
1. 接收用户任务,驱动状态机
2. 顺序调用 RequirementAgent -> ScriptAgent -> StoryboardAgent
3. 调用 Media Provider 为每个分镜生成素材
4. 调用 VideoAssembler 合成最终 MP4
5. 每步通过 task_store 推送状态(SSE)

异常处理:任意阶段抛错即标记 FAILED 并记录,不继续向下执行。
"""
from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from ..agents.requirement_agent import RequirementAgent
from ..agents.script_agent import ScriptAgent
from ..agents.storyboard_agent import StoryboardAgent
from ..core.config import settings, storage_dir
from ..core.logging import logger
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.image import get_image_provider, ImageProvider
from ..providers.llm import get_llm_provider
from ..providers.music import get_music_provider
from ..providers.music.base import MusicProvider
from ..providers.voice import get_voice_provider
from ..providers.voice.base import VoiceProvider
from ..providers.video import get_video_provider
from ..providers.video.base import VideoProvider
from ..services.task_service import task_store
from ..guard import ContentGuard
from ..compliance import TextComplianceAgent, ScriptRevisionAgent, ComplianceAuditLogger
from ..video.assembly import VideoAssembler, get_video_assembler


class Orchestrator:
    def __init__(
        self,
        *,
        llm=None,
        image: Optional[ImageProvider] = None,
        voice: Optional[VoiceProvider] = None,
        music: Optional[MusicProvider] = None,
        video: Optional[VideoProvider] = None,
        assembler: Optional[VideoAssembler] = None,
    ) -> None:
        llm = llm or get_llm_provider()
        self.requirement_agent = RequirementAgent(llm=llm)
        self.script_agent = ScriptAgent(llm=llm)
        self.storyboard_agent = StoryboardAgent(llm=llm)
        # ContentGuard 复用同一 LLM,不增加额外 Provider/Agent
        self.content_guard = ContentGuard(llm=llm)
        # Compliance Agent(脚本级合规预审):规则+LLM 语义,失败不自动放行
        self.compliance_agent = TextComplianceAgent(llm=llm)
        self.revision_agent = ScriptRevisionAgent(llm=llm)
        self.audit_logger = ComplianceAuditLogger()
        self.image = image or get_image_provider()
        self.voice = voice or get_voice_provider()
        self.music = music or get_music_provider()
        self.video = video or get_video_provider()
        self.assembler = assembler or get_video_assembler()

    async def execute(self, state: VideoGenerationState) -> VideoGenerationState:
        """执行完整 Pipeline,产物写入 state 并返回。"""
        try:
            await self._run_requirement(state)
            await self._run_script(state)
            # 合规预审:reject 时触发修订循环,耗尽则 HUMAN_REVIEW(不进入后续阶段)
            # 若该方法将状态置为 HUMAN_REVIEW,则跳过后续视频生成阶段
            await self._run_compliance(state)
            if state.status != TaskStatus.HUMAN_REVIEW:
                await self._run_storyboard(state)
                await self._run_content_guard(state)
                await self._run_media(state)
                await self._run_assembly(state)
        except Exception as e:
            logger.exception("Pipeline 失败 task=%s", state.task_id)
            state.mark_failed(f"{type(e).__name__}: {e}")
            task_store.save(state)
        return state

    # ---- 各阶段 ----
    async def _run_requirement(self, state: VideoGenerationState) -> None:
        state.append_log(TaskStatus.ANALYZING, "正在理解视频需求")
        task_store.save(state)
        await self.requirement_agent.run(state)
        logger.info("需求理解完成: %s", state.requirement.topic if state.requirement else "?")
        state.append_log(TaskStatus.SCRIPTING, "需求理解完成")
        task_store.save(state)

    async def _run_script(self, state: VideoGenerationState) -> None:
        await self.script_agent.run(state)
        logger.info("脚本生成完成: %s", state.script.title if state.script else "?")
        state.append_log(TaskStatus.COMPLIANCE_CHECKING, "脚本生成完成")
        task_store.save(state)

    async def _run_compliance(self, state: VideoGenerationState) -> None:
        """内容合规预审:脚本级规则+LLM 语义检查,不通过则自动修订并复检。

        流程:
          check -> pass: 继续 | review: 打标(可配置阻断) | reject: 修订循环
          reject 修订 max_revisions 次仍不通过 -> HUMAN_REVIEW(人工兜底,不进入视频生成)
        失败保护:Compliance Agent 自身异常 -> review + human_review_required(不自动放行)
        开关:settings.compliance_check_enabled=false 则跳过,回退原 Pipeline。
        """
        if not settings.compliance_check_enabled:
            state.append_log(TaskStatus.STORYBOARDING, "合规预审已关闭,跳过")
            task_store.save(state)
            return
        if state.script is None:
            state.append_log(TaskStatus.STORYBOARDING, "无脚本,跳过合规预审")
            return

        state.append_log(TaskStatus.COMPLIANCE_CHECKING, "正在执行内容合规预审")
        task_store.save(state)

        max_rev = settings.compliance_max_revisions
        revision_count = 0

        while True:
            result = await self.compliance_agent.check({
                "script": state.script,
                "topic": state.user_input,
                "metadata": {"duration": state.duration, "style": state.style},
            })
            result.revision_count = revision_count

            # 审计落盘 + 入 state
            entry = self.audit_logger.log(content_id=state.task_id, result=result)
            state.compliance_audit.append(entry.model_dump())
            state.compliance_report = result.model_dump()
            state.revision_count = revision_count

            logger.info(
                "Compliance 第%d次审核: status=%s risk=%s score=%d violations=%d warnings=%d",
                revision_count + 1, result.status, result.risk_level,
                result.overall_score, len(result.violations), len(result.warnings),
            )

            if result.status == "pass":
                state.append_log(TaskStatus.STORYBOARDING, "合规预审通过")
                task_store.save(state)
                return

            if result.status == "review":
                state.human_review_required = True
                state.compliance_report = result.model_dump()
                if settings.compliance_halt_on_review:
                    state.append_log(TaskStatus.HUMAN_REVIEW, "合规边界,进入人工审核")
                    state.status = TaskStatus.HUMAN_REVIEW
                    task_store.save(state)
                    return
                # 默认:打标后继续生成草稿(供人工复核)
                state.append_log(
                    TaskStatus.STORYBOARDING,
                    f"合规边界(review),已标记人工审核,继续生成草稿: {result.review_reason}",
                )
                task_store.save(state)
                return

            # reject
            if revision_count < max_rev:
                state.append_log(
                    TaskStatus.COMPLIANCE_CHECKING,
                    f"合规不通过(reject),自动修订 {revision_count + 1}/{max_rev}",
                )
                task_store.save(state)
                new_script = await self.revision_agent.revise(state.script, result)
                state.script = new_script
                revision_count += 1
                state.revision_count = revision_count
                continue

            # 修订耗尽仍不通过 -> 人工审核兜底
            state.human_review_required = True
            state.compliance_report = result.model_dump()
            state.append_log(
                TaskStatus.HUMAN_REVIEW,
                f"多次修订({max_rev}次)仍不通过,进入人工审核兜底",
            )
            state.status = TaskStatus.HUMAN_REVIEW
            task_store.save(state)
            return

    async def _run_storyboard(self, state: VideoGenerationState) -> None:
        await self.storyboard_agent.run(state)
        n = len(state.storyboard.shots) if state.storyboard else 0
        logger.info("分镜生成完成: %d 个镜头", n)
        state.append_log(TaskStatus.GENERATING_ASSETS, f"分镜生成完成,共 {n} 个镜头")
        task_store.save(state)

    async def _run_content_guard(self, state: VideoGenerationState) -> None:
        """ContentGuard 预检查:在素材生成前评估三维度风险(安全/平台/文化历史)。

        设计:不阻断 Pipeline(预留接口),仅记录报告到 state.content_guard_report。
        未来可加 content_guard_block_on_high 配置控制 high 风险是否阻断。
        """
        state.append_log(TaskStatus.GENERATING_ASSETS, "正在执行内容风险预检查")
        task_store.save(state)
        report = await self.content_guard.check(state)
        state.content_guard_report = report.model_dump()
        logger.info(
            "ContentGuard 完成: safe=%s overall=%s safety=%s platform=%s cultural=%s warnings=%d",
            report.safe, report.overall_risk, report.safety_risk,
            report.platform_risk, report.cultural_risk, len(report.warnings),
        )
        if report.warnings:
            for w in report.warnings:
                logger.warning("ContentGuard 风险提示: %s", w)
        if report.suggestions:
            state.append_log(TaskStatus.GENERATING_ASSETS, f"内容预检查完成(overall={report.overall_risk})")
        else:
            state.append_log(TaskStatus.GENERATING_ASSETS, "内容预检查完成(无风险)")
        task_store.save(state)

    async def _run_media(self, state: VideoGenerationState) -> None:
        """为每个分镜生成:文生图(关键帧) + TTS 旁白 + I2V 动态视频片段,并生成整片 BGM。

        流程升级(第六阶段 I2V 集成):
        1. 文生图 → image_path(关键帧,也作为 I2V 首帧)
        2. TTS → audio_path(旁白,作为最终音轨)
        3. I2V: image_path + video_prompt → video_path(5s 动态片段,真实连续动作)
           - 成功: shot.duration = 5(I2V 固定)
           - 失败: fallback 到 TTS 时长同步 + Ken Burns(不设 video_path,assembly 自动回退)
        """
        assert state.storyboard is not None
        img_dir = storage_dir("images")
        audio_dir = storage_dir("audio")
        clips_dir = storage_dir("clips")
        total_duration = 0
        assets: List[str] = []

        for i, shot in enumerate(state.storyboard.shots):
            # 1) 文生图(关键帧,也作为 I2V 首帧)
            img_path = os.path.join(img_dir, f"{state.task_id}_shot{i}.png")
            await self.image.generate(
                prompt=shot.image_prompt, save_path=img_path,
                width=settings.video_width, height=settings.video_height,
            )
            shot.image_path = img_path
            assets.append(img_path)

            # 2) TTS 旁白
            audio_path = os.path.join(audio_dir, f"{state.task_id}_shot{i}.wav")
            await self.voice.generate(
                text=shot.voiceover or shot.visual_description,
                save_path=audio_path, duration=shot.duration,
            )
            shot.audio_path = audio_path
            assets.append(audio_path)

            # 3) I2V:用关键帧 + video_prompt 生成 5s 动态视频片段(真实连续动作)
            clip_path = os.path.join(clips_dir, f"{state.task_id}_shot{i}.mp4")
            try:
                await self.video.generate(
                    image_path=img_path,
                    prompt=shot.video_prompt or shot.image_prompt,
                    save_path=clip_path,
                    duration=5,
                )
                shot.video_path = clip_path
                assets.append(clip_path)
                shot.duration = 5  # I2V 固定时长
                logger.info("shot%d: I2V 5s 动态片段生成成功 → duration=5s", i)
            except Exception as e:
                logger.warning("shot%d: I2V 失败,fallback 到 Ken Burns + TTS 时长同步: %s", i, e)
                # fallback:用 TTS 实际时长 + 0.5s 缓冲(原第五阶段逻辑)
                tts_dur = await self._get_audio_duration(audio_path)
                if tts_dur > 0:
                    shot.duration = max(round(tts_dur + 0.5), 2)
                else:
                    shot.duration = max(shot.duration, 2)
                logger.info("shot%d: fallback TTS=%.2fs → duration=%ds", i, tts_dur, shot.duration)
            total_duration += shot.duration

        # 整片 BGM(用 shot.duration 累计总时长)
        bgm_path = os.path.join(audio_dir, f"{state.task_id}_bgm.wav")
        await self.music.generate(save_path=bgm_path, duration=total_duration, mood="light")
        assets.append(bgm_path)
        state.assets = assets
        n_i2v = sum(1 for s in state.storyboard.shots if s.video_path)
        logger.info("素材生成完成: %d 文件, 总时长 %ds, I2V 动态片段 %d/%d",
                    len(assets), total_duration, n_i2v, len(state.storyboard.shots))
        state.append_log(TaskStatus.ASSEMBLING, "素材生成完成,开始合成视频")
        task_store.save(state)

    @staticmethod
    async def _get_audio_duration(audio_path: str) -> float:
        """读取音频文件实际时长(秒),失败返回 0。"""
        def _read() -> float:
            from moviepy import AudioFileClip
            clip = AudioFileClip(audio_path)
            dur = clip.duration
            clip.close()
            return dur
        try:
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.warning("读取音频时长失败 %s: %s", audio_path, e)
            return 0.0

    async def _run_assembly(self, state: VideoGenerationState) -> None:
        assert state.storyboard is not None
        video_dir = storage_dir("videos")
        output_path = os.path.join(video_dir, f"{state.task_id}.mp4")
        title = state.script.title if state.script else state.task_id
        # BGM 路径:约定在 assets 末尾
        bgm_path = state.assets[-1] if state.assets else ""

        await self.assembler.assemble(
            shots=state.storyboard.shots,
            bgm_path=bgm_path,
            output_path=output_path,
            title=title,
        )
        state.video_path = output_path
        logger.info("视频合成完成: %s", output_path)
        state.append_log(TaskStatus.COMPLETED, "视频生成完成")
        task_store.save(state)


# 进程内单例
orchestrator = Orchestrator()
