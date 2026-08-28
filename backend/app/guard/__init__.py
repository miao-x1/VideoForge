"""ContentGuard — 轻量级内容风险预检查模块。

在生成图片 / I2V / TTS 之前,对 storyboard 内容做三维度风险评估,
避免高风险内容消耗素材生成 API,并提供修改建议。

三个维度(不混为一谈):
1. 内容安全风险(safety_risk):明显违法违规、色情、暴力、毒品、赌博、欺诈等
2. 平台审核风险(platform_risk):可能触发平台审核的敏感现实议题、易引发严重争议的内容
3. 文化/历史一致性风险(cultural_risk):历史时代错误、服饰与时代不匹配、地域文化错误、
   历史人物设定错误、容易造成明显文化误导

设计原则:
- 不接外部法律 API,不构建复杂法律知识库
- 复用现有 LLM Provider 做语义评估(零额外依赖)
- 输出结构化 JSON 报告,不直接声称"违法",用"内容风险/平台风险/文化历史一致性风险"措辞
- 作为独立模块/阶段预留接口,不强制阻断 Pipeline(预留阻断开关位置)
- 不破坏 Provider 工厂,不增加无意义 Agent
"""
from __future__ import annotations

from .content_guard import ContentGuard, ContentGuardReport

__all__ = ["ContentGuard", "ContentGuardReport"]
