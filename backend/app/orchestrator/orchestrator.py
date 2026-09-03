"""Orchestrator:统一编排整个 Agent Pipeline。

职责:
1. 接收用户任务,驱动状态机
2. 阶段级模型路由:每个阶段通过 ModelRouter 选择最适合的模型
3. 顺序调用 RequirementAgent -> ScriptAgent -> StoryboardAgent
4. 调用 Media Provider 为每个分镜生成素材
5. 调用 VideoAssembler 合成最终 MP4
6. 每步通过 task_store 推送状态(SSE)
7. 阶段级错误隔离:单阶段失败不影响其他阶段的状态记录

异常处理:阶段级 try/except,记录结构化 failure_detail,标记 FAILED。
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import List, Optional

from ..agents.requirement_agent import RequirementAgent
from ..agents.story_planner_agent import StoryPlannerAgent
from ..agents.character_agent import CharacterAgent
from ..agents.world_agent import WorldAgent
from ..agents.script_agent import ScriptAgent
from ..agents.storyboard_agent import StoryboardAgent
from ..agents.prompt_engineering_agent import PromptEngineeringAgent
from ..agents.failure_analysis_agent import FailureAnalysisAgent
from ..agents.quality_judge_agent import QualityJudgeAgent
from ..agents.audio_planner_agent import AudioPlannerAgent
from ..agents.editing_planner_agent import EditingPlannerAgent
from ..workflows import (
    EditingWorkflow,
    ImageWorkflow,
    MusicWorkflow,
    TTSWorkflow,
    VideoWorkflow,
)
from ..core.config import settings
from ..core.exceptions import ProviderError
from ..core.logging import logger
from ..input.base import InputSource, build_multimodal_context
from ..input.registry import init_processors, process_all
from ..knowledge.video_indexer import VideoIndexer
from ..models.state import TaskStatus, VideoGenerationState
from ..providers.image import get_image_provider, ImageProvider
from ..providers.llm import get_llm_provider
from ..providers.music import get_music_provider
from ..providers.music.base import MusicProvider
from ..providers.voice import get_voice_provider
from ..providers.voice.base import VoiceProvider
from ..providers.video import get_video_provider
from ..providers.video.base import VideoModelProvider
from ..router import model_router, registry
from ..services.task_service import task_store
from ..services.asset_service import register_generated_assets
from ..graph import dependency_graph  # noqa: F401  # 依赖图(展示/影响分析)
from ..services.project_memory import update_project_memory
from ..guard import ContentGuard
from ..compliance import TextComplianceAgent, ScriptRevisionAgent, ComplianceAuditLogger
from ..video.assembly import VideoAssembler, get_video_assembler
from ..video.quality import validate_video


class Orchestrator:
    def __init__(
        self,
        *,
        llm=None,
        image: Optional[ImageProvider] = None,
        voice: Optional[VoiceProvider] = None,
        music: Optional[MusicProvider] = None,
        video: Optional[VideoModelProvider] = None,
        assembler: Optional[VideoAssembler] = None,
    ) -> None:
        llm = llm or get_llm_provider()
        self.llm = llm
        # 需求理解阶段使用最强推理模型(如 qwen-max)
        reasoning_llm = self._get_reasoning_llm(llm)
        self.requirement_agent = RequirementAgent(llm=reasoning_llm)
        # 作品级规划 Agent(决策层):故事结构 / 人物 Bible / 世界观与风格 Bible
        self.story_planner_agent = StoryPlannerAgent(llm=reasoning_llm)
        self.character_agent = CharacterAgent(llm=llm)
        self.world_agent = WorldAgent(llm=llm)
        self.script_agent = ScriptAgent(llm=llm)
        self.storyboard_agent = StoryboardAgent(llm=llm)
        self.prompt_engineering_agent = PromptEngineeringAgent(llm=llm)
        self.content_guard = ContentGuard(llm=llm)
        self.compliance_agent = TextComplianceAgent(llm=llm)
        self.revision_agent = ScriptRevisionAgent(llm=llm)
        self.audit_logger = ComplianceAuditLogger()
        # 失败分析与内容质检 Agent(决策层):失败根因→修复动作,镜头内容→质检报告
        self.failure_analysis_agent = FailureAnalysisAgent(llm=llm)
        self.quality_judge_agent = QualityJudgeAgent(llm=llm)
        # 音频/剪辑规划 Agent(决策层):音频 cue+音乐情绪、镜头顺序+转场+节奏
        self.audio_planner_agent = AudioPlannerAgent(llm=llm)
        self.editing_planner_agent = EditingPlannerAgent(llm=llm)
        self.image = image or get_image_provider()
        self.voice = voice or get_voice_provider()
        self.music = music or get_music_provider()
        self.video = video or get_video_provider()
        self.assembler = assembler or get_video_assembler()
        # Workflow 层:固定执行步骤,不做创作决策(Agent 已决策完毕)
        self.image_workflow = ImageWorkflow(image=self.image)
        self.video_workflow = VideoWorkflow(
            video=self.video,
            failure_analyzer=self.failure_analysis_agent,
            image_workflow=self.image_workflow,
            model_switcher=self._switch_video_model,
        )
        self.tts_workflow = TTSWorkflow(voice=self.voice)
        self.music_workflow = MusicWorkflow(music=self.music)
        self.editing_workflow = EditingWorkflow(assembler=self.assembler)
        init_processors(llm)
        self.video_indexer = VideoIndexer(llm=llm)

    @staticmethod
    def _get_reasoning_llm(default_llm):
        """尝试创建使用最强推理模型的 LLM 实例,失败则回退到默认 LLM。

        Mock 模式下不覆盖,保持测试环境零真实 API 调用。
        """
        if settings.llm_provider == "mock" or settings.enable_mock_providers:
            return default_llm
        try:
            from ..router import registry
            reasoning_models = registry.list_by_type("reasoning")
            if reasoning_models:
                best = max(reasoning_models, key=lambda m: m.priority)
                from ..providers.llm.dashscope_llm import DashScopeLLMProvider
                reasoning_llm = DashScopeLLMProvider(model=best.model_name)
                logger.info("需求理解阶段使用推理模型: %s", best.model_name)
                return reasoning_llm
        except Exception as e:
            logger.warning("创建推理 LLM 失败,回退到默认: %s", e)
        return default_llm

    async def execute(self, state: VideoGenerationState, *, preferred_model: str | None = None) -> VideoGenerationState:
        """执行完整 Pipeline,产物写入 state 并返回。

        Human-in-the-loop Gate:state.review_gates 中的节点(如 script)执行完毕后
        Pipeline 暂停,等待用户通过 confirm_* 接口确认后继续。

        Args:
            state: 视频生成状态
            preferred_model: 偏好模型(qwen/minimax),None 则自动路由
        """
        try:
            await self._route_models(state, preferred_model)
            await self._run_stage(state, "input_processing", self._run_input_processing)
            await self._run_stage(state, "requirement", self._run_requirement)
            await self._run_stage(state, "planning", self._run_planning)
            await self._run_stage(state, "script", self._run_script)
            await self._run_stage(state, "compliance", self._run_compliance)
            if state.status == TaskStatus.HUMAN_REVIEW:
                return state
            if await self._gate_pause(state, "script"):
                return state
            await self._run_tail(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def _run_tail(self, state: VideoGenerationState) -> None:
        """执行脚本确认后的后半段 Pipeline(分镜 → [Gate 3] → Prompt → 风控 → 素材 → 合成 → 索引)。"""
        await self._run_stage(state, "storyboard", self._run_storyboard)
        if await self._gate_pause(state, "storyboard"):
            return
        await self._run_after_storyboard(state)

    async def _run_after_storyboard(self, state: VideoGenerationState) -> None:
        """执行分镜确认后的 Pipeline(Prompt → [Gate 4] → 风控 → 素材 → 合成 → 索引)。"""
        await self._run_stage(state, "prompt_engineering", self._run_prompt_engineering)
        if await self._gate_pause(state, "prompt"):
            return
        await self._run_after_prompt(state)

    async def _run_after_prompt(self, state: VideoGenerationState) -> None:
        """执行 Prompt 确认后的 Pipeline(风控 → 素材 → 合成 → 质检闭环 → 索引)。"""
        await self._run_stage(state, "content_guard", self._run_content_guard)
        await self._run_stage(state, "media", self._run_media)
        await self._run_stage(state, "assembly", self._run_assembly)
        # QA 自动闭环:质检发现可修复缺陷(素材缺失/规格错误)时,限次自动修复并重新合成
        await self._quality_repair_loop(state)
        await self._run_stage(state, "indexing", self._run_indexing)
        # 任务完成:沉淀 Project Memory(创作设定/主体/场景/风格/Prompt/视频/修改记录)
        update_project_memory(state)

    async def _gate_pause(self, state: VideoGenerationState, gate: str) -> bool:
        """检查 gate 是否在 review_gates 中,是则暂停 Pipeline 等待用户确认。"""
        if gate not in (state.review_gates or []):
            return False
        gate_status = {
            "script": TaskStatus.SCRIPT_REVIEW,
            "storyboard": TaskStatus.STORYBOARD_REVIEW,
            "prompt": TaskStatus.PROMPT_REVIEW,
        }.get(gate)
        if gate_status is None:
            return False
        gate_labels = {"script": "脚本", "storyboard": "分镜", "prompt": "Prompt"}
        state.append_log(gate_status, f"{gate_labels.get(gate, gate)}已生成,等待你确认后继续")
        await task_store.save(state)
        logger.info("Gate 暂停 task=%s gate=%s,等待用户确认", state.task_id, gate)
        return True

    def _dismiss_gate(self, state: VideoGenerationState, gate: str) -> None:
        """Gate 确认后从 review_gates 移除,避免后续重入时重复暂停。"""
        if gate in (state.review_gates or []):
            state.review_gates = [g for g in state.review_gates if g != gate]

    # 失败阶段 → 恢复点映射(重试从失败阶段重新执行,已完成的更早阶段产物直接复用)
    _RETRY_RESUME: dict[str, str] = {
        "ANALYZING": "requirement",
        "SCRIPTING": "script",
        "COMPLIANCE_CHECKING": "compliance",
        "HUMAN_REVIEW": "compliance",
        "STORYBOARDING": "storyboard",
        "STORYBOARD_REVIEW": "storyboard",
        "PROMPT_REVIEW": "prompt_engineering",
        "GENERATING_ASSETS": "media",
        "ASSEMBLING": "assembly",
    }

    async def retry(self, state: VideoGenerationState) -> VideoGenerationState:
        """失败重试:从失败阶段恢复执行,保留已完成阶段的产物。

        只有 FAILED 状态可重试;无 failure_detail 时从头执行。
        """
        if state.status != TaskStatus.FAILED:
            raise ValueError(f"仅失败任务可重试,当前状态: {state.status.value}")
        stage_detail = (state.failure_detail or {}).get("stage", "")
        resume = self._RETRY_RESUME.get(stage_detail)
        state.failure_detail = None
        state.error = None
        state.append_log(
            TaskStatus.PENDING, f"开始重试(从 {stage_detail or '头'} 恢复,已完成阶段产物保留)"
        )
        await task_store.save(state)
        try:
            await self._route_models(state, None)
            if resume is None or resume == "requirement":
                await self._run_stage(state, "input_processing", self._run_input_processing)
                await self._run_stage(state, "requirement", self._run_requirement)
                resume = "script"
            if resume == "script":
                # 故事/人物/世界观规划(幂等:已存在则跳过),重试时自动补齐缺失设定
                await self._run_stage(state, "planning", self._run_planning)
                await self._run_stage(state, "script", self._run_script)
                resume = "compliance"
            if resume == "compliance":
                await self._run_stage(state, "compliance", self._run_compliance)
                if state.status == TaskStatus.HUMAN_REVIEW:
                    await task_store.save(state)
                    return state
                resume = "storyboard"
            if resume == "storyboard":
                # 分镜已存在且失败点在其后 → 跳过重生成,直接进入后续;否则重新生成分镜
                if state.storyboard is not None and stage_detail in ("PROMPT_REVIEW", "GENERATING_ASSETS", "ASSEMBLING"):
                    pass
                else:
                    await self._run_stage(state, "storyboard", self._run_storyboard)
                self._dismiss_gate(state, "storyboard")
                resume = "prompt_engineering"
            if resume == "prompt_engineering":
                if state.prompt_engineering_result is not None and stage_detail in ("GENERATING_ASSETS", "ASSEMBLING"):
                    pass
                else:
                    await self._run_stage(state, "prompt_engineering", self._run_prompt_engineering)
                self._dismiss_gate(state, "prompt")
            await self._run_after_prompt(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def confirm_script(
        self, state: VideoGenerationState, *, edited_script: dict | None = None,
    ) -> VideoGenerationState:
        """Gate 2 确认脚本:应用用户编辑并继续执行后续 Pipeline。

        Args:
            state: 处于 SCRIPT_REVIEW 状态的任务
            edited_script: 用户编辑后的脚本(VideoScript dict),None 表示确认当前脚本
        """
        if edited_script is not None:
            from ..schemas.script import VideoScript
            state.script = VideoScript(**edited_script)
            if state.script:
                state.save_version("script", state.script.model_dump(), label=state.script.title, reason="用户编辑")
            state.append_log(TaskStatus.COMPLIANCE_CHECKING, "脚本已确认(含用户修改)")
        else:
            state.append_log(TaskStatus.COMPLIANCE_CHECKING, "脚本已确认")
        self._dismiss_gate(state, "script")
        await task_store.save(state)
        try:
            # 编辑过的脚本重新过合规预审(用户修改可能引入新内容)
            if edited_script is not None:
                await self._run_stage(state, "compliance", self._run_compliance)
                if state.status == TaskStatus.HUMAN_REVIEW:
                    await task_store.save(state)
                    return state
            await self._run_tail(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def regenerate_script(
        self, state: VideoGenerationState, *, feedback: str | None = None,
    ) -> VideoGenerationState:
        """Gate 2 重新生成脚本草稿(保持 SCRIPT_REVIEW 状态,替换当前草稿)。"""
        log = "正在重新生成脚本" + (f"(用户反馈: {feedback})" if feedback else "")
        state.append_log(TaskStatus.SCRIPTING, log)
        await task_store.save(state)
        try:
            await self._run_stage(
                state, "script",
                lambda s: self._run_script(s, reason="重新生成", feedback=feedback),
            )
            state.append_log(TaskStatus.SCRIPT_REVIEW, "脚本已重新生成,等待确认")
            await task_store.save(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def confirm_storyboard(
        self, state: VideoGenerationState, *, edited_storyboard: dict | None = None,
    ) -> VideoGenerationState:
        """Gate 3 确认分镜:应用用户编辑并继续执行后续 Pipeline(Prompt → 生成)。"""
        if edited_storyboard is not None:
            from ..schemas.storyboard import Storyboard
            state.storyboard = Storyboard(**edited_storyboard)
            n = len(state.storyboard.shots)
            state.save_version("storyboard", state.storyboard.model_dump(), label=f"{n} 个镜头", reason="用户编辑")
            state.append_log(TaskStatus.STORYBOARDING, f"分镜已确认(含用户修改,{n} 个镜头)")
        else:
            state.append_log(TaskStatus.STORYBOARDING, "分镜已确认")
        self._dismiss_gate(state, "storyboard")
        await task_store.save(state)
        try:
            await self._run_after_storyboard(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def regenerate_storyboard(
        self, state: VideoGenerationState, *, feedback: str | None = None,
    ) -> VideoGenerationState:
        """Gate 3 重新生成全部分镜草稿(保持 STORYBOARD_REVIEW 状态)。"""
        log = "正在重新生成分镜" + (f"(用户反馈: {feedback})" if feedback else "")
        state.append_log(TaskStatus.STORYBOARDING, log)
        await task_store.save(state)
        try:
            await self._run_stage(
                state, "storyboard",
                lambda s: self._run_storyboard(s, reason="重新生成", feedback=feedback),
            )
            state.append_log(TaskStatus.STORYBOARD_REVIEW, "分镜已重新生成,等待确认")
            await task_store.save(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def regenerate_shot(
        self, state: VideoGenerationState, shot_index: int, *, feedback: str | None = None,
    ) -> VideoGenerationState:
        """Gate 3 重新生成单个镜头(保持 STORYBOARD_REVIEW 状态,替换该镜头)。"""
        log = f"正在重新生成镜头 {shot_index + 1}" + (f"(用户反馈: {feedback})" if feedback else "")
        state.append_log(TaskStatus.STORYBOARDING, log)
        await task_store.save(state)
        try:
            await self.storyboard_agent.regenerate_shot(state, shot_index, feedback=feedback)
            n = len(state.storyboard.shots) if state.storyboard else 0
            state.save_version("storyboard", state.storyboard.model_dump(), label=f"{n} 个镜头", reason=f"重新生成镜头 {shot_index + 1}")
            state.append_log(TaskStatus.STORYBOARD_REVIEW, f"镜头 {shot_index + 1} 已重新生成,等待确认")
            await task_store.save(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def confirm_prompt(
        self, state: VideoGenerationState, *, edited_result: dict | None = None,
    ) -> VideoGenerationState:
        """Gate 4 确认 Prompt:应用用户编辑并继续执行后续 Pipeline(生成)。"""
        if edited_result is not None:
            from ..schemas.structured_prompt import PromptEngineeringResult
            result = PromptEngineeringResult(**edited_result)
            # 用户编辑的 raw prompt 覆盖 storyboard,确保真实生效
            self.prompt_engineering_agent._apply_enhanced_prompts(state, result)
            state.prompt_engineering_result = result.model_dump()
            n = len(result.prompts)
            state.save_version("prompt", result.model_dump(), label=f"{n} 个镜头, 模型={result.model_id}", reason="用户编辑")
            state.append_log(TaskStatus.GENERATING_ASSETS, f"Prompt 已确认(含用户修改,{n} 个镜头)")
        else:
            state.append_log(TaskStatus.GENERATING_ASSETS, "Prompt 已确认")
        self._dismiss_gate(state, "prompt")
        await task_store.save(state)
        try:
            await self._run_after_prompt(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def regenerate_prompt(
        self, state: VideoGenerationState, *, feedback: str | None = None,
    ) -> VideoGenerationState:
        """Gate 4 重新编译 Prompt 草稿(保持 PROMPT_REVIEW 状态)。"""
        log = "正在重新编译专业生成提示词" + (f"(用户反馈: {feedback})" if feedback else "")
        state.append_log(TaskStatus.GENERATING_ASSETS, log)
        await task_store.save(state)
        try:
            await self._run_stage(
                state, "prompt_engineering",
                lambda s: self._run_prompt_engineering(s, reason="重新编译", feedback=feedback),
            )
            state.append_log(TaskStatus.PROMPT_REVIEW, "Prompt 已重新编译,等待确认")
            await task_store.save(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def switch_model(self, state: VideoGenerationState, *, model_id: str) -> VideoGenerationState:
        """Gate 4 手动切换视频模型:重新路由并按新模型能力重新编译 Prompt(模型感知)。

        用户覆盖 AI 自动路由决策后,生成阶段将使用用户指定的模型。
        """
        state.append_log(TaskStatus.GENERATING_ASSETS, f"正在切换视频模型为 {model_id}")
        await task_store.save(state)
        try:
            # 手动路由会抛 ModelUnavailableError(已在 API 层预检),此处安全
            await self._route_models(state, model_id)
            await self._run_stage(state, "prompt_engineering", lambda s: self._run_prompt_engineering(s, reason=f"切换模型 {model_id}"))
            state.append_log(TaskStatus.PROMPT_REVIEW, f"已切换为 {state.model_used} 并重新编译 Prompt,等待确认")
            await task_store.save(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    # ======================== Dependency Graph + 局部重生成 ========================

    @staticmethod
    def _shot_impact(
        state: VideoGenerationState, wanted: set[int],
    ) -> dict:
        """镜头影响分析的单一实现(依赖图语义):wanted 中未锁定的受影响,其余不受影响。

        所有依赖分析(镜头级/场景级)统一走这里,与 DependencyGraph 的
        compute_affected(BFS + locked 跳过)保持同一语义,避免两套口径。
        """
        if state.storyboard is None:
            return {"affected": [], "unaffected": [], "locked": []}
        n = len(state.storyboard.shots)
        wanted &= {i for i in range(n)}
        locked = [i for i in sorted(wanted) if state.storyboard.shots[i].locked]
        affected = [i for i in sorted(wanted) if not state.storyboard.shots[i].locked]
        unaffected = [i for i in range(n) if i not in wanted]
        return {"affected": affected, "unaffected": unaffected, "locked": locked}

    @classmethod
    def analyze_dependencies(
        cls, state: VideoGenerationState, shot_indices: List[int],
    ) -> dict:
        """依赖图影响分析:修改指定镜头后,哪些内容会/不会受影响。

        依赖链: 镜头编辑 → 该镜头 Prompt → 关键帧图 → I2V 片段 → 重新合成。
        锁定的镜头即使被点名也不会被修改。
        """
        return cls._shot_impact(state, set(shot_indices))

    @classmethod
    def analyze_scene_dependencies(
        cls, state: VideoGenerationState, scene_index: int,
    ) -> dict:
        """节点级依赖传播:修改脚本 Scene 后,哪些镜头链路受影响。

        依赖链: Scene 编辑 → 该场景关联 Shot → Shot Prompt → 关键帧图 → I2V 片段 → 重新合成。
        通过 shot.scene_id 关联(无对应场景的镜头不受影响),锁定镜头被排除。
        """
        if state.storyboard is None or state.script is None:
            return {"affected": [], "unaffected": [], "locked": []}
        scene_id = scene_index + 1
        wanted = {i for i, s in enumerate(state.storyboard.shots) if s.scene_id == scene_id}
        impact = cls._shot_impact(state, wanted)
        impact.update({"scene_index": scene_index, "scene_id": scene_id})
        return impact

    async def revise_scene(
        self, state: VideoGenerationState, scene_index: int, *,
        scene_edits: dict | None = None, feedback: str | None = None,
    ) -> VideoGenerationState:
        """Scene 级局部重生成:编辑脚本场景后,仅重生成该场景关联镜头链,然后重新合成。

        Incremental Generation:
        1. 应用场景编辑(visual/dialogue/voiceover 等)
        2. 按 scene_id 找到关联镜头,以新场景为上下文重新生成分镜镜头(storyboard_agent)
        3. 对每个受影响镜头走完整素材链(Prompt → 图 → TTS → I2V)
        4. 未受影响镜头素材直接复用,重新合成整片
        """
        if state.script is None or not (0 <= scene_index < len(state.script.scenes)):
            raise IndexError(f"场景索引越界: {scene_index}")
        impact = self.analyze_scene_dependencies(state, scene_index)
        affected = impact["affected"]
        if not affected:
            state.append_log(state.status, f"场景 {scene_index + 1} 没有关联的可重生成镜头(可能全部被锁定)")
            await task_store.save(state)
            return state

        # 1) 应用场景编辑
        if scene_edits:
            from ..schemas.script import ScriptScene
            current = state.script.scenes[scene_index].model_dump()
            current.update(scene_edits)
            state.script.scenes[scene_index] = ScriptScene(**current)
            state.save_version(
                "script", state.script.model_dump(),
                label=state.script.title,
                reason=f"编辑场景 {scene_index + 1}",
            )

        state.append_log(
            TaskStatus.GENERATING_ASSETS,
            f"场景修改:将重新生成镜头 {[i + 1 for i in affected]}的完整链路,"
            f"镜头 {[i + 1 for i in impact['unaffected']]}不受影响",
        )
        await task_store.save(state)

        try:
            # 2) 以新场景为上下文重新生成关联镜头(分镜层)
            for i in affected:
                await self.storyboard_agent.regenerate_shot(state, i, feedback=feedback)
            # 3) 完整素材链重生成
            for i in affected:
                await self._revise_single_shot(state, i, feedback=feedback)
            state.save_version(
                "storyboard", state.storyboard.model_dump(),
                label=f"{len(state.storyboard.shots)} 个镜头",
                reason=f"场景 {scene_index + 1} 修改,局部重生成镜头 {[i + 1 for i in affected]}",
            )
            if state.prompt_engineering_result:
                state.save_version(
                    "prompt", state.prompt_engineering_result,
                    label=f"场景修改重生成 {len(affected)} 个镜头, 模型={state.model_used or ''}",
                    reason=f"场景 {scene_index + 1} 修改",
                )
            # 4) 重新合成 + 质检
            await self._run_stage(state, "assembly", self._run_assembly)
            state.append_log(TaskStatus.COMPLETED, f"场景 {scene_index + 1} 局部修改完成")
            await task_store.save(state)
            update_project_memory(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state


    async def toggle_shot_lock(
        self, state: VideoGenerationState, shot_index: int, *, locked: bool,
    ) -> VideoGenerationState:
        """锁定/解锁单个镜头(对连续角色/场景保持一致性非常重要)。"""
        if state.storyboard is None or not (0 <= shot_index < len(state.storyboard.shots)):
            raise IndexError(f"镜头索引越界: {shot_index}")
        shot = state.storyboard.shots[shot_index]
        shot.locked = locked
        # 同步依赖图锁定状态,保证 /dependency-graph 展示与实际重生成行为一致
        if locked:
            dependency_graph.lock_node(f"shot_{shot_index}")
        else:
            dependency_graph.unlock_node(f"shot_{shot_index}")
        state.append_log(
            state.status,
            f"镜头 {shot_index + 1} 已{'锁定,后续重生成不会修改' if locked else '解锁'}",
        )
        await task_store.save(state)
        return state

    async def revise_shots(
        self, state: VideoGenerationState, shot_indices: List[int], *,
        edits: dict | None = None, feedback: str | None = None,
    ) -> VideoGenerationState:
        """局部重生成:仅重新生成受影响镜头的 Prompt/图/音/视频片段,然后重新合成。

        依赖图: 镜头编辑 → Prompt i → Image i → I2V i → 合成。
        未受影响镜头的既有素材直接复用,锁定镜头不会被修改。
        feedback 为用户对修改效果的补充说明(如"画面要更暗"),注入单镜头 Prompt 重编译。
        """
        impact = self.analyze_dependencies(state, shot_indices)
        affected = impact["affected"]
        if not affected:
            state.append_log(state.status, "没有可重新生成的镜头(可能全部被锁定)")
            await task_store.save(state)
            return state
        if edits:
            for idx_str, shot_dict in edits.items():
                idx = int(idx_str)
                if idx in affected and 0 <= idx < len(state.storyboard.shots):
                    from ..schemas.storyboard import StoryboardShot
                    current = state.storyboard.shots[idx].model_dump()
                    current.update(shot_dict)
                    state.storyboard.shots[idx] = StoryboardShot(**current)

        unaffected_desc = [i + 1 for i in impact["unaffected"]]
        state.append_log(
            TaskStatus.GENERATING_ASSETS,
            f"局部修改:将重新生成镜头 {[i + 1 for i in affected]},不影响镜头 {unaffected_desc}",
        )
        await task_store.save(state)

        try:
            for i in affected:
                await self._revise_single_shot(state, i, feedback=feedback)
            # 局部重生成更新了受影响镜头的 Prompt/素材 → storyboard/prompt 变更记入版本历史
            state.save_version(
                "storyboard", state.storyboard.model_dump(),
                label=f"{len(state.storyboard.shots)} 个镜头",
                reason=f"局部修改镜头 {[i + 1 for i in affected]}",
            )
            if state.prompt_engineering_result:
                state.save_version(
                    "prompt", state.prompt_engineering_result,
                    label=f"局部修改 {len(affected)} 个镜头, 模型={state.model_used or ''}",
                    reason=f"局部修改镜头 {[i + 1 for i in affected]}",
                )
            # 重新合成 + 质检
            await self._run_stage(state, "assembly", self._run_assembly)
            state.append_log(TaskStatus.COMPLETED, "局部修改完成")
            await task_store.save(state)
            update_project_memory(state)
        except ProviderError as e:
            await self._handle_failure(state, e, e.error_code, e.provider)
        except Exception as e:
            await self._handle_failure(state, e, "PIPELINE_ERROR")
        return state

    async def _revise_single_shot(self, state: VideoGenerationState, i: int, *, feedback: str | None = None) -> None:
        """重新生成单个镜头的完整素材链:Prompt → 关键帧 → TTS → I2V。"""
        shot = state.storyboard.shots[i]
        shot_index_display = i + 1

        # 1) 重编译该镜头 Prompt(单镜头上下文,模型感知,携带用户反馈)
        state.append_log(TaskStatus.GENERATING_ASSETS, f"正在重新编译镜头 {shot_index_display} 的 Prompt")
        from .prompt_engineering_context import build_single_shot_context
        context = build_single_shot_context(state, i)
        if feedback:
            context["user_feedback"] = feedback
        data = await self.llm.generate(task="prompt_engineering", context=context)
        from ..schemas.structured_prompt import PromptEngineeringResult
        single = PromptEngineeringResult(**data)
        for p in single.prompts:
            if p.raw_image_prompt:
                shot.image_prompt = p.raw_image_prompt
            if p.raw_video_prompt:
                shot.video_prompt = p.raw_video_prompt
            if p.negative_prompt:
                shot.negative_prompt = p.negative_prompt
        if state.prompt_engineering_result:
            result = state.prompt_engineering_result
            result["prompts"] = [p.model_dump() for p in single.prompts if p.shot_index == i] + \
                [p for p in result["prompts"] if p.get("shot_index") != i]
            result["prompts"].sort(key=lambda p: p.get("shot_index", 0))

        # 2) 关键帧图片(Workflow 固定步骤;t2v/r2v 镜头按规划跳过)
        if (shot.desired_mode or "").lower() not in ("t2v", "r2v"):
            await self.image_workflow.generate_shot(state, i)

        # 3) TTS 旁白(Workflow 固定步骤)
        await self.tts_workflow.generate_shot(state, i)

        # 4) 动态片段(Workflow:逐镜头模式决策 t2v/i2v/r2v/first_last,
        #    用户参考图与下一镜首帧(尾帧衔接)由 VideoWorkflow 统一装配)
        user_refs = VideoWorkflow._user_reference_paths(state)
        await self.video_workflow.generate_shot(state, i, user_reference_paths=user_refs)
        await task_store.save(state)

    async def _route_models(self, state: VideoGenerationState, preferred_model: str | None) -> None:
        """阶段级模型路由:为视频和图片生成阶段选择最优模型。"""
        if settings.llm_provider == "mock" or settings.enable_mock_providers:
            # Mock 模式(测试环境)不覆盖注入的 Provider,保持零真实 API 调用
            return
        strategy = settings.routing_strategy if settings.routing_strategy != "manual" else "auto"

        # 视频模型路由
        if preferred_model or settings.routing_strategy != "manual":
            decision = model_router.select(
                user_input=state.user_input,
                duration=state.duration,
                style=state.style,
                aspect_ratio=state.aspect_ratio,
                preferred_model=preferred_model,
                strategy=strategy,
            )
            self.video = get_video_provider(decision.selected_provider)
            self.video_workflow.video = self.video
            state.model_used = decision.selected_model or self.video.name
            state.routing_decision = decision.to_dict()
            if state.spec:
                state.spec.routing_decision = decision.to_dict()
            stars = f"质量{'★'*decision.quality_stars} 速度{'★'*decision.speed_stars} 成本{'★'*decision.cost_stars}"
            state.append_log(state.status, f"视频模型路由: {decision.selected_provider}/{state.model_used} ({decision.strategy}) {stars}")
            logger.info(
                "视频路由 task=%s: %s/%s (%s), %s, 理由: %s",
                state.task_id, decision.selected_provider, state.model_used,
                decision.strategy, stars, decision.reason,
            )
            await task_store.save(state)

        # 图片模型路由
        try:
            img_decision = model_router.select_image(
                user_input=state.user_input,
                style=state.style,
                aspect_ratio=state.aspect_ratio,
                strategy=strategy,
            )
            self.image = get_image_provider(img_decision.selected_provider)
            self.image_workflow.image = self.image
            state.image_model_used = img_decision.selected_model
            state.image_routing_decision = img_decision.to_dict()
            logger.info(
                "图片路由 task=%s: %s/%s (%s), 理由: %s",
                state.task_id, img_decision.selected_provider, img_decision.selected_model,
                img_decision.strategy, img_decision.reason,
            )
        except Exception as e:
            logger.warning("图片模型路由失败,使用默认: %s", e)

        # 语音模型路由
        try:
            voice_decision = model_router.select_voice(strategy=strategy)
            self.voice = get_voice_provider(voice_decision.selected_provider)
            self.tts_workflow.voice = self.voice
            state.voice_model_used = voice_decision.selected_model
            logger.info(
                "语音路由 task=%s: %s/%s",
                state.task_id, voice_decision.selected_provider, voice_decision.selected_model,
            )
        except Exception as e:
            logger.warning("语音模型路由失败,使用默认: %s", e)

    async def _run_stage(
        self,
        state: VideoGenerationState,
        stage_name: str,
        stage_fn,
    ) -> None:
        """执行单个阶段,带计时和阶段级错误记录。"""
        t0 = time.time()
        logger.info("阶段开始 task=%s stage=%s", state.task_id, stage_name)
        try:
            await stage_fn(state)
        except ProviderError:
            raise
        except Exception as e:
            logger.error("阶段失败 task=%s stage=%s: %s", state.task_id, stage_name, e)
            raise
        elapsed = time.time() - t0
        logger.info("阶段完成 task=%s stage=%s elapsed=%.2fs", state.task_id, stage_name, elapsed)

    async def _handle_failure(
        self,
        state: VideoGenerationState,
        error: Exception,
        error_code: str,
        provider: str = "",
    ) -> None:
        """统一失败处理:记录结构化 failure_detail 并标记 FAILED。"""
        failed_stage = state.status.value
        input_files = list(state.assets) if state.assets else []
        state.failure_detail = {
            "stage": failed_stage,
            "reason": f"{type(error).__name__}: {error}",
            "error_code": error_code,
            "provider": provider or getattr(error, "provider", ""),
            "input_files": input_files,
        }
        err_msg = f"[阶段:{failed_stage}] {error_code}"
        if provider:
            err_msg += f" [{provider}]"
        err_msg += f": {getattr(error, 'message', str(error))}"
        if input_files:
            err_msg += f" | 已生成素材 {len(input_files)} 个"
        state.mark_failed(err_msg)
        await task_store.save(state)

    # ---- 各阶段 ----
    async def _run_input_processing(self, state: VideoGenerationState) -> None:
        """处理多模态输入源(文本/图片/视频/URL),构建 multimodal_context 注入 RequirementAgent。"""
        if not state.input_sources:
            return
        state.append_log(TaskStatus.ANALYZING, "正在处理多模态输入")
        await task_store.save(state)
        state.multimodal_context = await self._build_multimodal_context(state.input_sources)
        logger.info(
            "多模态输入处理完成: %d 个源, context %d 字符",
            len(state.input_sources), len(state.multimodal_context),
        )
        await task_store.save(state)

    async def _build_multimodal_context(self, input_sources) -> str:
        """将 InputSourceItem 列表解析为 multimodal_context 文本(带用途标注)。"""
        sources = []
        for s in input_sources:
            data = s.model_dump() if hasattr(s, "model_dump") else dict(s)
            sources.append(InputSource(**data))
        payloads = await process_all(sources)
        for src, payload in zip(sources, payloads):
            payload.purpose = src.purpose
        return build_multimodal_context(payloads)

    async def understand(
        self,
        *,
        user_input: str,
        duration: int = 30,
        style: str = "",
        aspect_ratio: str = "9:16",
        input_sources: list | None = None,
        spec: VideoSpecification | None = None,
    ) -> VideoGenerationState:
        """独立需求理解:不创建任务、不落库,用于创作方案确认前的 AI 结构化。"""
        state = VideoGenerationState(
            user_id="", user_input=user_input, duration=duration,
            style=style, aspect_ratio=aspect_ratio,
            input_sources=input_sources or [],
        )
        if spec:
            state.spec = spec
        if state.input_sources:
            state.multimodal_context = await self._build_multimodal_context(state.input_sources)
        await self.requirement_agent.run(state)
        return state

    async def _run_requirement(self, state: VideoGenerationState) -> None:
        state.append_log(TaskStatus.ANALYZING, "正在理解视频需求")
        await task_store.save(state)
        # 项目记忆继承:同项目任务自动带入系列设定(主体/场景/风格),保持内容一致性
        from ..services.project_memory import load_project_memory
        project_memory = load_project_memory(state.project_id)
        await self.requirement_agent.run(state, project_memory=project_memory)
        logger.info("需求理解完成: %s", state.requirement.topic if state.requirement else "?")
        if state.creative_intent:
            state.save_version("creative_intent", state.creative_intent.model_dump(), label="创作方案", reason="初始生成")
        state.append_log(TaskStatus.SCRIPTING, "需求理解完成")
        await task_store.save(state)

    async def _run_planning(self, state: VideoGenerationState) -> None:
        """作品级规划阶段(Agent 决策层):故事结构 → Character Bible → World/Style Bible。

        产物写入 state.project_state,供脚本/分镜/Prompt 全链路读取。
        三个 Agent 均幂等(已规划则跳过),重试与恢复时安全重复调用。
        """
        if state.requirement is None:
            logger.warning("planning 阶段缺少 requirement,跳过作品规划")
            return
        state.append_log(TaskStatus.SCRIPTING, "正在规划故事结构")
        await task_store.save(state)
        await self.story_planner_agent.run(state)

        state.append_log(TaskStatus.SCRIPTING, "正在建立人物设定")
        await task_store.save(state)
        await self.character_agent.run(state)

        state.append_log(TaskStatus.SCRIPTING, "正在建立世界观与视觉风格")
        await task_store.save(state)
        await self.world_agent.run(state)

        ps = state.get_or_create_project_state()
        logger.info(
            "作品规划完成: 节拍=%d 人物=%d 世界场景=%d 风格=%s",
            len(ps.story_state.beats),
            len(ps.character_state.bibles),
            len(ps.world_state.bible.scenes) if ps.world_state.bible else 0,
            ps.style_state.bible.visual_style if ps.style_state.bible else "?",
        )
        await task_store.save(state)

    async def _run_script(
        self, state: VideoGenerationState, *, reason: str = "初始生成", feedback: str | None = None,
    ) -> None:
        # 防御:确保作品级规划就绪(正常链路 planning 阶段已执行;Agent 自身幂等)
        await self.story_planner_agent.run(state)
        await self.character_agent.run(state)
        await self.world_agent.run(state)
        await self.script_agent.run(state, feedback=feedback)
        logger.info("脚本生成完成: %s", state.script.title if state.script else "?")
        if state.script:
            state.save_version("script", state.script.model_dump(), label=state.script.title, reason=reason)
        state.append_log(TaskStatus.COMPLIANCE_CHECKING, "脚本生成完成")
        await task_store.save(state)

    async def _run_compliance(self, state: VideoGenerationState) -> None:
        """内容合规预审:脚本级规则+LLM 语义检查,不通过则自动修订并复检。"""
        if not state.compliance_enabled:
            state.append_log(TaskStatus.STORYBOARDING, "合规预审已关闭,跳过")
            await task_store.save(state)
            return
        if state.script is None:
            state.append_log(TaskStatus.STORYBOARDING, "无脚本,跳过合规预审")
            return

        state.append_log(TaskStatus.COMPLIANCE_CHECKING, "正在执行内容合规预审")
        await task_store.save(state)

        max_rev = settings.compliance_max_revisions
        revision_count = 0

        while True:
            result = await self.compliance_agent.check({
                "script": state.script,
                "topic": state.user_input,
                "metadata": {"duration": state.duration, "style": state.style},
            })
            result.revision_count = revision_count

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
                await task_store.save(state)
                return

            if result.status == "review":
                state.human_review_required = True
                state.compliance_report = result.model_dump()
                if settings.compliance_halt_on_review:
                    state.append_log(TaskStatus.HUMAN_REVIEW, "合规边界,进入人工审核")
                    state.status = TaskStatus.HUMAN_REVIEW
                    await task_store.save(state)
                    return
                state.append_log(
                    TaskStatus.STORYBOARDING,
                    f"合规边界(review),已标记人工审核,继续生成草稿: {result.review_reason}",
                )
                await task_store.save(state)
                return

            if revision_count < max_rev:
                state.append_log(
                    TaskStatus.COMPLIANCE_CHECKING,
                    f"合规不通过(reject),自动修订 {revision_count + 1}/{max_rev}",
                )
                await task_store.save(state)
                new_script = await self.revision_agent.revise(state.script, result)
                state.script = new_script
                revision_count += 1
                state.revision_count = revision_count
                continue

            state.human_review_required = True
            state.compliance_report = result.model_dump()
            state.append_log(
                TaskStatus.HUMAN_REVIEW,
                f"多次修订({max_rev}次)仍不通过,进入人工审核兜底",
            )
            state.status = TaskStatus.HUMAN_REVIEW
            await task_store.save(state)
            return

    async def _run_storyboard(
        self, state: VideoGenerationState, *, reason: str = "初始生成", feedback: str | None = None,
    ) -> None:
        await self.storyboard_agent.run(state, feedback=feedback)
        n = len(state.storyboard.shots) if state.storyboard else 0
        logger.info("分镜生成完成: %d 个镜头", n)
        state.append_log(TaskStatus.GENERATING_ASSETS, f"分镜生成完成,共 {n} 个镜头")
        if state.storyboard:
            state.save_version("storyboard", state.storyboard.model_dump(), label=f"{n} 个镜头", reason=reason)
            for i in range(n):
                dependency_graph.add_shot_node(i)
                # 全量重生成后按分镜实际状态重置依赖图锁定(新分镜默认未锁定)
                if state.storyboard.shots[i].locked:
                    dependency_graph.lock_node(f"shot_{i}")
                else:
                    dependency_graph.unlock_node(f"shot_{i}")
        await task_store.save(state)

    async def _run_prompt_engineering(
        self, state: VideoGenerationState, *, reason: str = "初始编译", feedback: str | None = None,
    ) -> None:
        """Prompt Engineering:将基础 Prompt 增强为专业、结构化、模型感知的 Prompt。"""
        state.append_log(TaskStatus.GENERATING_ASSETS, "正在编译专业生成提示词")
        await task_store.save(state)
        await self.prompt_engineering_agent.run(state, feedback=feedback)
        result = state.prompt_engineering_result
        if result:
            n = len(result.get("prompts", []))
            model = result.get("model_id", "?")
            notes = result.get("compilation_notes", "")
            logger.info("Prompt Engineering: %d 个镜头, 模型=%s, notes=%s", n, model, notes)
            state.append_log(TaskStatus.GENERATING_ASSETS, f"Prompt 增强完成: {n} 个镜头, 模型={model}")
            state.save_version("prompt", result, label=f"{n} 个镜头, 模型={model}", reason=reason)
        await task_store.save(state)

    async def _run_content_guard(self, state: VideoGenerationState) -> None:
        """ContentGuard 预检查:在素材生成前评估三维度风险(安全/平台/文化历史)。"""
        state.append_log(TaskStatus.GENERATING_ASSETS, "正在执行内容风险预检查")
        await task_store.save(state)
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
        await task_store.save(state)

    async def _run_media(self, state: VideoGenerationState) -> None:
        """素材生成:Agent 决策(音频规划/内容质检) + Workflow 执行固定生成步骤。

        顺序: ImageWorkflow(关键帧) → AudioPlanner 决策 → TTSWorkflow(旁白)
             → VideoWorkflow(逐镜头模式决策 + 失败修复闭环)
             → QualityJudge 内容质检(限次返工) → MusicWorkflow(BGM)。
        Orchestrator 只编排顺序与阶段状态;"选什么模式/模型/怎么修"由 Agent
        决策 + Router 判定,Workflow 仅执行固定步骤。
        """
        assert state.storyboard is not None

        # 1) 关键帧图片(t2v/r2v 镜头按规划跳过)
        await self.image_workflow.run(state)
        await task_store.save(state)

        # 2) 音频规划决策(逐镜 cue + 全片音乐情绪),再执行 TTS
        await self.audio_planner_agent.run(state)
        await self.tts_workflow.run(state)
        await task_store.save(state)

        # 3) 动态视频片段(逐镜头 t2v/i2v/r2v/first_last 决策 + 失败自动修复闭环)
        await self.video_workflow.run(state)
        await task_store.save(state)

        # 4) 内容级质检 + 限次返工(人物/场景/连续性问题)
        await self._content_quality_loop(state)

        # 5) 整片 BGM(情绪/风格取自 audio_state 规划)
        await self.music_workflow.run(state)
        await task_store.save(state)

        total_duration = sum(s.duration for s in state.storyboard.shots)
        n_clips = sum(1 for s in state.storyboard.shots if s.video_path)
        logger.info(
            "素材生成完成: %d 文件, 时间轴总时长 %ds, 动态片段 %d/%d",
            len(state.assets), total_duration, n_clips, len(state.storyboard.shots),
        )
        state.append_log(TaskStatus.ASSEMBLING, "素材生成完成,开始合成视频")
        await task_store.save(state)

    async def _content_quality_loop(self, state: VideoGenerationState, *, max_rounds: int = 1) -> None:
        """内容质检返工闭环:QualityJudge 评判 → FailureAnalysis 决策 → 重生成。

        技术校验(文件/时长/音轨)由合成后 _quality_repair_loop 负责;
        本环只处理"拍得对不对"(人物一致/场景连续/因果完整),限次自动返工,
        仍不通过的镜头保留质检报告并放行(交人工 Gate 判断,不阻塞整片)。
        """
        assert state.storyboard is not None
        for round_no in range(1, max_rounds + 1):
            await self.quality_judge_agent.run(state)
            ps = state.get_or_create_project_state()
            failed = list(ps.quality_state.failed_shots)
            if not failed:
                return
            state.append_log(
                TaskStatus.GENERATING_ASSETS,
                f"内容质检发现 {len(failed)} 个镜头待返工: {failed}(第 {round_no} 轮自动修复)",
            )
            for shot_index in failed:
                report = ps.quality_state.latest_for_shot(shot_index)
                issues = report.issues if report else []
                decision = self.failure_analysis_agent.analyze_quality_failure(
                    shot_index=shot_index, issues=issues, attempt=round_no,
                )
                if decision.should_abort:
                    continue
                # 内容返工:按决策强制参考图模式,重新生成关键帧(若需要)+ 动态片段
                shot = state.storyboard.shots[shot_index]
                need_keyframe = decision.force_mode != "r2v" or not (
                    shot.image_path and os.path.exists(shot.image_path)
                )
                if need_keyframe and (shot.image_path is None or decision.force_mode in ("", "i2v")):
                    await self.image_workflow.generate_shot(state, shot_index)
                user_refs = VideoWorkflow._user_reference_paths(state)
                await self.video_workflow.generate_shot(state, shot_index, user_reference_paths=user_refs)
            await task_store.save(state)
        # 终轮复评(仅刷新报告,不再返工)
        await self.quality_judge_agent.run(state)

    async def _switch_video_model(
        self, state: VideoGenerationState, shot_index: int, reason: str,
    ) -> bool:
        """失败修复回调:切换到备选视频厂商。返回是否切换成功。

        决策依据 model_router 的评分候选列表,排除当前厂商;
        mock/无备选真实厂商时返回 False(失败升级为阶段错误)。
        """
        current = getattr(self.video, "name", "")
        try:
            candidates = registry.list_by_types(["image_to_video", "text_to_video", "reference_to_video"])
            alternatives = [m for m in candidates if m.provider != current and m.provider != "mock"]
            if not alternatives:
                logger.warning("镜头 %s 切厂商失败:无备选厂商(当前=%s)", shot_index + 1, current)
                return False
            entry = max(alternatives, key=lambda m: m.quality_score)
            new_provider = get_video_provider(entry.provider)
            self.video = new_provider
            self.video_workflow.video = new_provider
            state.model_used = entry.model_name
            state.append_log(
                TaskStatus.GENERATING_ASSETS,
                f"镜头 {shot_index+1} 失败修复:切换视频厂商 {current} → {entry.provider}({reason[:40]})",
            )
            logger.info("镜头 %s 切换视频厂商: %s → %s", shot_index + 1, current, entry.provider)
            return True
        except Exception as e:
            logger.warning("镜头 %s 切换视频厂商异常: %s", shot_index + 1, e)
            return False

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

    async def _build_timeline(self, state: VideoGenerationState) -> list[TimelineSegment]:
        """合成后构建音轨时间轴:按剪辑决策顺序排列镜头时段 + 旁白/字幕绑定。"""
        from ..models.state import TimelineSegment
        if state.storyboard is None:
            return []
        # 时间轴顺序与成片一致(EditingPlanner 的 shot_order;无决策单时叙事原序)
        ps = state.get_or_create_project_state()
        n = len(state.storyboard.shots)
        editing = ps.editing_state
        if editing.decision_source == "agent" and sorted(editing.shot_order) == list(range(n)):
            order = editing.shot_order
        else:
            order = list(range(n))
        segments: list[TimelineSegment] = []
        t = 0.0
        for narrative_idx in order:
            shot = state.storyboard.shots[narrative_idx]
            d = float(max(shot.duration, 1))
            narration_dur = await self._get_audio_duration(shot.audio_path) if shot.audio_path and os.path.exists(shot.audio_path) else None
            segments.append(TimelineSegment(
                shot_index=narrative_idx,
                start=t, end=t + d, duration=d,
                narration_path=shot.audio_path,
                narration_duration=narration_dur,
                subtitle_text=shot.subtitle or shot.voiceover or shot.visual_description or "",
                subtitle_enabled=shot.subtitle_enabled,
            ))
            t += d
        return segments

    async def update_subtitles(
        self, state: VideoGenerationState, updates: list[dict],
    ) -> VideoGenerationState:
        """字幕逐条编辑:更新文本/开关/字号 → 重新合成(新版本,旧视频保留)。

        不触发任何模型调用,纯本地重合成。
        """
        if state.storyboard is None:
            raise ValueError("任务尚无分镜,无法编辑字幕")
        changed = 0
        for item in updates:
            idx = item.get("shot_index")
            if not isinstance(idx, int) or not (0 <= idx < len(state.storyboard.shots)):
                continue
            shot = state.storyboard.shots[idx]
            if "text" in item and item["text"] is not None:
                shot.subtitle = str(item["text"])
                changed += 1
            if "enabled" in item and item["enabled"] is not None:
                shot.subtitle_enabled = bool(item["enabled"])
                changed += 1
            if "font_size" in item and item["font_size"] is not None:
                shot.subtitle_font_size = max(0, int(item["font_size"]))
                changed += 1
        if changed:
            state.append_log(TaskStatus.ASSEMBLING, f"字幕已更新({changed} 处),正在重新合成")
            state.save_version(
                "storyboard", state.storyboard.model_dump(),
                label=f"{len(state.storyboard.shots)} 个镜头",
                reason="字幕编辑",
            )
            await task_store.save(state)
            try:
                await self._run_stage(state, "assembly", self._run_assembly)
                state.append_log(TaskStatus.COMPLETED, "字幕更新完成,新版本已生成")
                await task_store.save(state)
            except ProviderError as e:
                await self._handle_failure(state, e, e.error_code, e.provider)
            except Exception as e:
                await self._handle_failure(state, e, "PIPELINE_ERROR")
        else:
            state.append_log(state.status, "字幕无变更")
            await task_store.save(state)
        return state

    @staticmethod
    def export_srt(state: VideoGenerationState) -> str:
        """按音轨时间轴导出 SRT 字幕(逐镜头一条,时间取镜头时段)。"""
        def _fmt(t: float) -> str:
            h, rem = divmod(int(t), 3600)
            m, s = divmod(rem, 60)
            ms = int(round((t - int(t)) * 1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        lines: list[str] = []
        for i, seg in enumerate(state.timeline or [], start=1):
            text = seg.subtitle_text.strip()
            if not text or not seg.subtitle_enabled:
                continue
            lines.append(f"{i}\n{_fmt(seg.start)} --> {_fmt(seg.end)}\n{text}\n")
        return "\n".join(lines)

    async def _run_assembly(self, state: VideoGenerationState) -> None:
        assert state.storyboard is not None
        # 剪辑决策(Agent):镜头顺序/转场/节奏 → editing_state,EditingWorkflow 按决策执行
        await self.editing_planner_agent.run(state)
        # 合成固定步骤由 EditingWorkflow 执行(版本化输出/BGM 定位/成片台账)
        output_path = await self.editing_workflow.run(state)
        # 构建音轨时间轴(按剪辑决策顺序,镜头时段/旁白/字幕绑定,供编辑与导出)
        state.timeline = await self._build_timeline(state)

        try:
            report = await validate_video(
                video_path=output_path,
                storyboard=state.storyboard,
                expected_duration=state.duration,
            )
            state.quality_report = report
            logger.info(
                "质量校验完成: grade=%s dur=%.2fs %dx%d audio=%s",
                report.get("grade"), report.get("duration", 0),
                report.get("width", 0), report.get("height", 0),
                report.get("has_audio"),
            )
            state.append_log(TaskStatus.COMPLETED, f"质量校验完成: grade={report.get('grade')}")
        except Exception as e:
            logger.warning("质量校验失败(不影响产物): %s", e)
            state.append_log(TaskStatus.COMPLETED, f"质量校验失败: {e}")

        state.append_log(TaskStatus.COMPLETED, "视频生成完成")
        # 成片 + 镜头图 → 项目素材库(幂等,失败不影响产物)
        register_generated_assets(state)
        await task_store.save(state)

    async def _run_indexing(self, state: VideoGenerationState) -> None:
        """索引视频到历史库(元数据 + 语义描述 + Embedding → Milvus)。"""
        if not state.video_path:
            return
        try:
            state.append_log(TaskStatus.COMPLETED, "正在索引视频到历史库")
            await task_store.save(state)
            await self.video_indexer.index(state)
            state.append_log(TaskStatus.COMPLETED, "视频已索引,可通过自然语言检索")
            await task_store.save(state)
        except Exception as e:
            logger.warning("视频索引失败(不影响产物): %s", e)

    # QA 自动闭环:最多修复次数(防无限循环)
    _QUALITY_MAX_REPAIRS = 1

    async def _quality_repair_loop(self, state: VideoGenerationState) -> None:
        """质检闭环:errors 级缺陷(素材缺失/规格错误)→ 自动补齐素材并重新合成,限次。

        可修复范围:shot 图片/TTS 缺失(重新生成)、无音轨/时长偏差(重新合成)。
        分辨率错误等需要模型能力变更的缺陷不在自动修复范围,如实保留报告由用户决策。
        """
        for attempt in range(self._QUALITY_MAX_REPAIRS + 1):
            report = state.quality_report or {}
            errors = report.get("errors") or []
            if not errors or report.get("grade") in ("A", "B"):
                return
            if attempt >= self._QUALITY_MAX_REPAIRS:
                state.append_log(
                    TaskStatus.COMPLETED,
                    f"质检发现 {len(errors)} 处缺陷,自动修复未完全消除,详见质检报告",
                )
                await task_store.save(state)
                return

            state.append_log(
                TaskStatus.ASSEMBLING,
                f"质检发现 {len(errors)} 处缺陷(grade={report.get('grade')}),正在自动修复(第 {attempt + 1} 次)",
            )
            await task_store.save(state)
            repaired = await self._repair_quality_errors(state, errors)
            if not repaired:
                return
            # 修复后重新合成 + 重新质检
            await self._run_stage(state, "assembly", self._run_assembly)

    async def _repair_quality_errors(self, state: VideoGenerationState, errors: list[str]) -> bool:
        """按质检 errors 修复可修复项,返回是否有实际修复动作。

        修复动作全部走 Workflow 单镜入口(与主链路同一套模式决策/台账逻辑)。
        """
        assert state.storyboard is not None
        repaired = False
        user_refs = VideoWorkflow._user_reference_paths(state)

        for i, shot in enumerate(state.storyboard.shots):
            has_visual = (shot.video_path and os.path.exists(shot.video_path)) or (
                shot.image_path and os.path.exists(shot.image_path)
            )
            # shot{i} 画面素材缺失 → 按模式补关键帧/动态片段
            if not has_visual and any(f"shot{i} 画面素材缺失" in e for e in errors):
                state.append_log(TaskStatus.GENERATING_ASSETS, f"自动修复:重新生成镜头 {i+1} 画面素材")
                if (shot.desired_mode or "").lower() not in ("t2v", "r2v") and (
                    not shot.image_path or not os.path.exists(shot.image_path)
                ):
                    await self.image_workflow.generate_shot(state, i)
                if not shot.video_path or not os.path.exists(shot.video_path):
                    await self.video_workflow.generate_shot(state, i, user_reference_paths=user_refs)
                repaired = True
            # shot{i} TTS 缺失 → 重新合成旁白
            if (not shot.audio_path or not os.path.exists(shot.audio_path)) and any(
                f"shot{i} TTS 缺失" in e for e in errors
            ):
                state.append_log(TaskStatus.GENERATING_ASSETS, f"自动修复:重新生成镜头 {i+1} 旁白")
                await self.tts_workflow.generate_shot(state, i)
                repaired = True

        # 无音轨 → 检查 BGM 是否缺失(旁白已逐 shot 修复)
        if any("无音轨" in e for e in errors):
            bgm_exists = any(a.endswith(f"{state.task_id}_bgm.wav") for a in state.assets)
            if not bgm_exists:
                await self.music_workflow.run(state)
                repaired = True
            else:
                # BGM 存在仍无音轨 → 重新合成即可(交给 repaired=True 触发重合成)
                repaired = True

        # 数量不匹配类错误(画面/TTS 数量):重合成前上述逐 shot 修复已覆盖
        return repaired


orchestrator = Orchestrator()
