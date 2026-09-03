"""PromptCompiler:将 VideoSpecification 编译为 RequirementAgent 可消费的 context。

作为 UI 数据结构与后端 Agent Pipeline 之间的桥梁:
- 将结构化的创作意图转换为 LLM 可理解的文本上下文
- 补充 creative_elements / environment / motion / camera 等维度信息
- 保持与现有 RequirementAgent context 格式兼容
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..schemas.specification import (
    AudioControl,
    CameraControl,
    CreativeElement,
    Environment,
    MotionControl,
    Narrative,
    ReferenceAsset,
    StyleItem,
    VideoSpecification,
)


class PromptCompiler:
    """编译 VideoSpecification → RequirementAgent context dict。"""

    @staticmethod
    def compile(spec: VideoSpecification) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "user_input": spec.prompt,
            "duration": spec.duration,
            "style": _compile_visual_style(spec.visual_style, spec.custom_style),
            "aspect_ratio": spec.aspect_ratio,
        }

        if spec.target_platform:
            context["target_platform"] = spec.target_platform

        elements_desc = _compile_creative_elements(spec.creative_elements)
        if elements_desc:
            context["creative_elements"] = elements_desc

        env_desc = _compile_environment(spec.environment)
        if env_desc:
            context["environment"] = env_desc

        narrative_desc = _compile_narrative(spec.narrative)
        if narrative_desc:
            context["narrative"] = narrative_desc

        motion_desc = _compile_motion(spec.motion)
        if motion_desc:
            context["motion"] = motion_desc

        camera_desc = _compile_camera(spec.camera)
        if camera_desc:
            context["camera"] = camera_desc

        audio_desc = _compile_audio(spec.audio)
        if audio_desc:
            context["audio"] = audio_desc

        refs_desc = _compile_references(spec.references)
        if refs_desc:
            context["references"] = refs_desc

        context["compiled_prompt"] = PromptCompiler.compile_full_prompt(spec)

        return context

    @staticmethod
    def compile_visual_directives(spec: VideoSpecification) -> Dict[str, Any]:
        """提取视觉参数指令,供 StoryboardAgent 注入 image_prompt / video_prompt 生成。

        确保用户的 lighting / color / style 设置真实贯通到分镜提示词。
        """
        directives: Dict[str, Any] = {}

        env = _compile_environment(spec.environment)
        if env:
            directives["environment"] = env

        style = _compile_visual_style(spec.visual_style, spec.custom_style)
        if style:
            directives["visual_style"] = style

        camera = _compile_camera(spec.camera)
        if camera:
            directives["camera"] = camera

        motion = _compile_motion(spec.motion)
        if motion:
            directives["motion"] = motion

        elements = _compile_creative_elements(spec.creative_elements)
        if elements:
            directives["creative_elements"] = elements

        # 构建英文提示词后缀,直接附加到 image_prompt / video_prompt
        # 这确保 Provider 收到的是英文,且参数明确存在
        en_parts: List[str] = []
        if spec.environment:
            env_obj = spec.environment
            if env_obj.lighting:
                en_parts.append(f"lighting: {env_obj.lighting}")
            if env_obj.lighting_type:
                en_parts.append(f"lighting type: {env_obj.lighting_type}")
            if env_obj.color_palette:
                en_parts.append(f"color palette: {env_obj.color_palette}")
            if env_obj.color_temperature:
                en_parts.append(f"color temperature: {env_obj.color_temperature}")
            if env_obj.color_grading:
                en_parts.append(f"color grading: {env_obj.color_grading}")
            if env_obj.atmosphere:
                en_parts.append(f"atmosphere: {env_obj.atmosphere}")
            if env_obj.time_of_day:
                en_parts.append(f"time of day: {env_obj.time_of_day}")
            if env_obj.weather:
                en_parts.append(f"weather: {env_obj.weather}")

        if style:
            en_parts.append(f"visual style: {style}")

        if spec.camera:
            if spec.camera.shot_type:
                en_parts.append(f"shot type: {spec.camera.shot_type}")
            if spec.camera.angle:
                en_parts.append(f"camera angle: {spec.camera.angle}")
            if spec.camera.movement:
                en_parts.append(f"camera movement: {spec.camera.movement}")

        if en_parts:
            directives["prompt_suffix"] = ", ".join(en_parts)

        return directives

    @staticmethod
    def compile_full_prompt(spec: VideoSpecification) -> str:
        """将 VideoSpecification 编译为单段自然语言 prompt,供 LLM 直接消费。"""
        parts: List[str] = []

        if spec.prompt:
            parts.append(spec.prompt)

        elements = _compile_creative_elements(spec.creative_elements)
        if elements:
            parts.append(f"创作元素: {elements}")

        env = _compile_environment(spec.environment)
        if env:
            parts.append(f"场景环境: {env}")

        narrative = _compile_narrative(spec.narrative)
        if narrative:
            parts.append(f"叙事: {narrative}")

        motion = _compile_motion(spec.motion)
        if motion:
            parts.append(f"运动: {motion}")

        style = _compile_visual_style(spec.visual_style, spec.custom_style)
        if style:
            parts.append(f"风格: {style}")

        camera = _compile_camera(spec.camera)
        if camera:
            parts.append(f"镜头: {camera}")

        audio = _compile_audio(spec.audio)
        if audio:
            parts.append(f"音频: {audio}")

        refs = _compile_references(spec.references)
        if refs:
            parts.append(f"参考素材: {refs}")

        params: List[str] = [f"时长{spec.duration}秒", f"比例{spec.aspect_ratio}"]
        if spec.target_platform:
            params.append(f"平台{spec.target_platform}")
        parts.append(f"技术参数: {', '.join(params)}")

        return "\n".join(parts)


def _compile_creative_elements(elements: List[CreativeElement]) -> str:
    if not elements:
        return ""
    descs: List[str] = []
    for el in sorted(elements, key=lambda e: e.sort_order):
        parts: List[str] = []
        if el.name:
            parts.append(el.name)
        parts.append(f"类型:{el.type.value}")
        if el.description:
            parts.append(el.description)
        if el.action:
            parts.append(f"动作:{el.action}")
        if el.attributes:
            attr_strs = [f"{k}={v}" for k, v in el.attributes.items()]
            parts.append(f"属性({', '.join(attr_strs)})")
        descs.append(" | ".join(parts))
    return "; ".join(descs)


def _compile_environment(env: Environment | None) -> str:
    if not env:
        return ""
    parts: List[str] = []
    if env.location:
        parts.append(f"地点:{env.location}")
    if env.time_of_day:
        parts.append(f"时间:{env.time_of_day}")
    if env.weather:
        parts.append(f"天气:{env.weather}")
    if env.lighting:
        parts.append(f"光照:{env.lighting}")
    if env.lighting_type:
        parts.append(f"光源类型:{env.lighting_type}")
    if env.atmosphere:
        parts.append(f"氛围:{env.atmosphere}")
    if env.color_palette:
        parts.append(f"色彩方案:{env.color_palette}")
    if env.color_temperature:
        parts.append(f"色温:{env.color_temperature}")
    if env.color_grading:
        parts.append(f"调色风格:{env.color_grading}")
    return ", ".join(parts) if parts else ""


def _compile_narrative(narrative: Narrative | None) -> str:
    if not narrative:
        return ""
    parts: List[str] = []
    if narrative.structure:
        parts.append(f"结构:{narrative.structure}")
    if narrative.theme:
        parts.append(f"主题:{narrative.theme}")
    if narrative.mood:
        parts.append(f"情绪:{narrative.mood}")
    return ", ".join(parts) if parts else ""


def _compile_motion(motion: MotionControl | None) -> str:
    if not motion:
        return ""
    parts: List[str] = []
    if motion.subject_motion:
        parts.append(f"主体运动:{motion.subject_motion}")
    if motion.camera_motion:
        parts.append(f"镜头运动:{motion.camera_motion}")
    if motion.environment_motion:
        parts.append(f"环境运动:{motion.environment_motion}")
    return ", ".join(parts) if parts else ""


def _compile_visual_style(styles: List[StyleItem], custom: str = "") -> str:
    parts: List[str] = []
    for s in styles:
        if s.category and s.name:
            parts.append(f"{s.category}/{s.name}")
        elif s.name:
            parts.append(s.name)
    if custom:
        parts.append(custom)
    return ", ".join(parts) if parts else ""


def _compile_camera(camera: CameraControl | None) -> str:
    if not camera:
        return ""
    parts: List[str] = []
    if camera.shot_type:
        parts.append(f"景别:{camera.shot_type}")
    if camera.angle:
        parts.append(f"角度:{camera.angle}")
    if camera.movement:
        parts.append(f"运动:{camera.movement}")
    if camera.rhythm:
        parts.append(f"节奏:{camera.rhythm}")
    return ", ".join(parts) if parts else ""


def _compile_audio(audio: AudioControl | None) -> str:
    if not audio:
        return ""
    parts: List[str] = []
    if audio.bgm_mode and audio.bgm_mode != "auto":
        parts.append(f"BGM:{audio.bgm_mode}")
    if audio.bgm_path:
        parts.append(f"BGM文件:{audio.bgm_path}")
    if audio.sfx_description:
        parts.append(f"音效:{audio.sfx_description}")
    if audio.dialogue_text:
        parts.append(f"台词:{audio.dialogue_text}")
    if audio.voice_style:
        parts.append(f"配音风格:{audio.voice_style}")
    return ", ".join(parts) if parts else ""


def _compile_references(refs: List[ReferenceAsset]) -> str:
    if not refs:
        return ""
    descs: List[str] = []
    for ref in refs:
        parts: List[str] = [f"{ref.type.value}"]
        if ref.purpose:
            parts.append(f"用途:{ref.purpose.value}")
        if ref.description:
            parts.append(ref.description)
        if ref.source:
            parts.append(f"来源:{ref.source}")
        descs.append(" | ".join(parts))
    return "; ".join(descs)
