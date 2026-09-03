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

    # 环境控制:production 禁止 Mock，test 允许 Mock
    app_env: Literal["production", "test"] = "production"
    enable_mock_providers: bool = False  # 仅 APP_ENV=test 时可设 True

    # Provider 选择 (生产默认全部使用真实 Provider)
    llm_provider: Literal["mock", "dashscope"] = "dashscope"
    image_provider: Literal["mock", "dashscope"] = "dashscope"
    image_model: str = "wanx2.1-t2i-turbo"
    voice_provider: Literal["mock", "dashscope"] = "dashscope"
    music_provider: Literal["mock", "ambient"] = "ambient"
    tts_model: str = "qwen-audio-3.0-tts-flash"
    tts_voice: str = "longanhuan_v3.6"
    tts_language: str = "zh-CN"
    # 图生视频 Provider: qwen | minimax | comfy (mock 仅测试环境可用)
    video_model_provider: Literal["mock", "qwen", "minimax", "comfy"] = "qwen"
    i2v_provider: Literal["mock", "dashscope"] = "dashscope"
    # Qwen(DashScope)视频模型
    qwen_api_key: str = ""
    qwen_video_model: str = "wan2.6-i2v-flash"
    # MiniMax 视频模型(H3 直连,V2 API,pay-as-you-go)
    minimax_api_key: str = ""
    minimax_video_model: str = "MiniMax-H3"  # MiniMax-H3 / MiniMax-H3-Max
    minimax_base_url: str = "https://api.minimax.io"  # 国际站;国内站用 https://api.minimax.cn
    # 云端 ComfyUI(Workflow 执行层,如 MiniMax H3 官方模板)
    comfy_api_key: str = ""  # 环境变量 COMFY_API_KEY,禁止写入前端/数据库/Git
    comfy_base_url: str = "https://cloud.comfy.org"
    # 模型路由策略:auto(综合) | best_quality | lowest_cost | fastest | manual
    routing_strategy: Literal["auto", "best_quality", "lowest_cost", "fastest", "manual"] = "auto"

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

    # JWT 鉴权
    jwt_secret: str = "videoforge-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    # CORS 允许来源(逗号分隔,空则允许全部)
    cors_origins: str = ""

    # 多模态:图片理解模型(Qwen-VL 系列)
    vl_model: str = "qwen-vl-max"
    # 文件上传限制(MB)
    upload_max_size_mb: int = 20

    # RAG:视频历史库 + 向量检索
    embedding_model: str = "text-embedding-v3"
    embedding_dim: int = 1024
    milvus_uri: str = ""  # 空则使用 Milvus Lite 本地文件


settings = Settings()


def storage_dir(sub: str) -> Path:
    """获取 storage 子目录，不存在则创建。"""
    p = STORAGE_ROOT / sub
    p.mkdir(parents=True, exist_ok=True)
    return p
