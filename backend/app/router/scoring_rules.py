"""评分规则配置:权重和特殊规则集中管理,调整不需要改业务代码。"""
from __future__ import annotations

# 评分维度权重 (auto 策略默认)
WEIGHTS = {
    "quality": 0.30,
    "speed": 0.30,
    "cost": 0.25,
    "fit": 0.15,
}

# 路由策略
ROUTING_STRATEGIES = ["auto", "best_quality", "lowest_cost", "fastest", "manual"]

# 关键词到需求维度的映射(用于 RequirementAnalyzer 纯规则提取)
QUALITY_KEYWORDS = {"高清", "高质量", "画质", "精细", "电影级", "4k", "高清画质", "high quality", "cinematic"}
SPEED_KEYWORDS = {"快速", "紧急", "尽快", "马上", "实时", "fast", "quick", "urgent", "speed"}
COST_KEYWORDS = {"便宜", "省钱", "低成本", "免费", "预算", "cheap", "free", "budget", "affordable"}

# 风格关键词映射(用于匹配模型 supported_styles)
STYLE_KEYWORDS = {
    "realistic": ["写实", "真实", "realistic", "真人"],
    "cinematic": ["电影感", "电影级", "cinematic", "电影"],
    "animation": ["动画", "卡通", "anime", "animation", "2d", "3d", "日漫", "国漫"],
    "documentary": ["纪录片", "documentary"],
    "commercial": ["广告", "商业", "commercial", "产品"],
    "cyberpunk": ["赛博朋克", "cyberpunk", "科技"],
}

# 特殊规则:时长阈值
SHORT_VIDEO_THRESHOLD = 6  # ≤6s 视为短视频,速度优先
LONG_VIDEO_THRESHOLD = 12  # ≥12s 视为长视频,质量优先(受 max_duration 限制)
