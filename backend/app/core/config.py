"""应用配置：集中读取 .env 与路径常量。"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录：backend/ 的上一级
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STORAGE_ROOT = PROJECT_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Provider 选择
    llm_provider: Literal["mock", "dashscope"] = "mock"
    image_provider: Literal["mock", "seedream", "dashscope"] = "mock"
    image_model: str = "wanx2.1-t2i-turbo"  # 通义万相文生图模型(wanx2.1-t2i-turbo / wanx2.1-t2i-plus / wanx-v1)
    voice_provider: Literal["mock", "dashscope"] = "mock"
    music_provider: Literal["mock", "ambient"] = "mock"
    tts_model: str = "qwen-audio-3.0-tts-flash"
    tts_voice: str = "longanhuan_v3.6"  # 中文女声(适合中文旁白)
    # TTS 目标语言(BCP-47 tag):zh-CN(中文普通话,默认) / en-US / ja-JP 等
    # LLM 在 storyboard 阶段会按此语言生成 voiceover 文本,Voice Provider voice 已含语言
    tts_language: str = "zh-CN"
    # 图生视频(I2V)Provider: mock(伪 Ken Burns,本地测试) | dashscope(通义万相 wan2.6-i2v-flash,真实连续动作)
    i2v_provider: Literal["mock", "dashscope"] = "mock"
    i2v_model: str = "wan2.6-i2v-flash"  # 通义万相图生视频模型(wan2.6-i2v-flash 默认,支持 2-15s + 720P/1080P)

    # 通用 LLM 连接(OpenAI 兼容,DashScope/DeepSeek 等均可用)
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"

    # 兼容旧字段(向后保留)
    dashscope_api_key: str = ""
    deepseek_api_key: str = ""

    # 视频输出配置(9:16 竖屏,开发用 720×1280,可调 1080×1920)
    video_width: int = 720
    video_height: int = 1280
    video_fps: int = 24
    transition_duration: float = 0.4  # 转场时长(秒)
    bgm_volume: float = 0.20  # BGM 音量比例(0~1)
    subtitle_font_path: str = "C:/Windows/Fonts/msyh.ttc"  # 中文字体
    subtitle_font_size: int = 42  # 字幕字号

    # 内容合规预审(Compliance Agent):关闭即完全回退到原 Pipeline 顺序
    # 开启:Topic -> Script -> Compliance -> (reject 时 Revision 循环) -> Storyboard -> Media
    # 关闭:Topic -> Script -> Storyboard -> Media(原流程)
    compliance_check_enabled: bool = True
    # 合规不通过时的最大自动修订次数(耗尽后进入 HUMAN_REVIEW)
    compliance_max_revisions: int = 2
    # 审计日志落盘开关
    compliance_audit_enabled: bool = True
    # review(边界)时是否阻断 Pipeline:True=进入人工审核不生成;False=打标后继续生成草稿
    compliance_halt_on_review: bool = False


settings = Settings()


def storage_dir(sub: str) -> Path:
    """获取 storage 子目录，不存在则创建。"""
    p = STORAGE_ROOT / sub
    p.mkdir(parents=True, exist_ok=True)
    return p
