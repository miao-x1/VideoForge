"""合规规则数据(独立配置,不硬编码在 Agent Prompt 中)。

采用 Python 数据模块而非 YAML,目的是零外部依赖即可运行(与项目"不引入外部依赖即可跑通"原则一致)。
未来新增规则只需在此追加一条 dict,无需修改 Agent 核心代码。

每条规则字段:
  rule_id     - 规则 ID(如 COM-001)
  category    - 类别
  description - 规则描述
  severity    - low / medium / high
  enabled     - 是否启用
  action      - reject / review(reject=明确违规应阻断;review=边界需人工)
  examples    - 典型违规示例(供 LLM 参考)
  patterns    - 正则列表(确定性快速筛查,仅作辅助;语义判断由 LLM 完成)
"""
from __future__ import annotations

from typing import Any, Dict, List

RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "COM-001",
        "category": "legal_violation",
        "description": "违法违规风险:内容涉及明显违法活动(毒品、赌博、诈骗、传销、非法武器等)的鼓励或教学",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["教人如何制毒", "网络诈骗手法教程", "聚众赌博组织方法"],
        "patterns": [r"如何.*制毒", r"诈骗.*手法", r"赌博.*组织", r"传销.*加盟"],
    },
    {
        "rule_id": "COM-002",
        "category": "pornography",
        "description": "色情/露骨性内容:直白的性描写或露骨画面描述",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["露骨性行为描述", "色情画面"],
        "patterns": [r"(?i)(porn|sexual explicit)"],
    },
    {
        "rule_id": "COM-003",
        "category": "violence",
        "description": "极端暴力/血腥内容:渲染虐杀、酷刑、自残等极端暴力(区分历史叙述与鼓励现实暴力)",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["详细虐杀过程", "酷刑教学", "鼓励对现实人群施暴"],
        "patterns": [r"虐杀.*过程", r"酷刑.*教学", r"鼓励.*施暴"],
    },
    {
        "rule_id": "COM-004",
        "category": "hate_discrimination",
        "description": "仇恨、歧视、侮辱性内容:针对种族/民族/性别/宗教/地域等的仇恨或侮辱",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["种族侮辱称谓", "地域歧视性口号"],
        "patterns": [r"(?i)(racial slur|歧视.*劣等)"],
    },
    {
        "rule_id": "COM-005",
        "category": "dangerous_behavior",
        "description": "危险行为及危险行为引导:鼓励或教学现实危险行为(注意区分:历史战争叙述≠鼓励暴力,讨论≠教学)",
        "severity": "medium",
        "enabled": True,
        "action": "review",
        "examples": ["教人轻生方法", "危险挑战教程", "吸食毒品示范"],
        "patterns": [r"轻生.*方法", r"危险挑战.*教程"],
    },
    {
        "rule_id": "COM-006",
        "category": "medical_falsehood",
        "description": "医疗健康领域的明显虚假或绝对化疗效承诺",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["100%治愈癌症", "包治百病", "根除糖尿病", "三天彻底断根"],
        "patterns": [r"100%.*治愈", r"包治百病", r"根治|根除", r"彻底断根", r"一定.{0,4}治好"],
    },
    {
        "rule_id": "COM-007",
        "category": "finance_falsehood",
        "description": "金融领域的明显虚假承诺或收益保证",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["稳赚不赔", "保本保息月入百万", "零风险高回报"],
        "patterns": [r"稳赚不赔", r"保本保息", r"零风险.*高回报", r"月入百万"],
    },
    {
        "rule_id": "COM-008",
        "category": "false_information",
        "description": "明显虚假信息:编造重大公共事件、伪造权威发布等",
        "severity": "medium",
        "enabled": True,
        "action": "review",
        "examples": ["编造突发灾难死亡人数", "伪造官方政策"],
        "patterns": [r"官方.{0,6}宣布.*?(?=假)"],
    },
    {
        "rule_id": "COM-009",
        "category": "historical_error",
        "description": "明显的历史事实错误(注意:穿越/架空喜剧的时代混搭属创意,不在此列)",
        "severity": "low",
        "enabled": True,
        "action": "review",
        "examples": ["声称李白是武将", "把和服当汉服且标榜正史"],
        "patterns": [],
    },
    {
        "rule_id": "COM-010",
        "category": "minor_protection",
        "description": "未成年人相关高风险内容:涉未成年人的不当内容或引导",
        "severity": "high",
        "enabled": True,
        "action": "reject",
        "examples": ["涉及未成年人的不当内容", "诱导未成年人危险行为"],
        "patterns": [r"未成年.{0,8}(不当|色情|暴力)"],
    },
    {
        "rule_id": "COM-011",
        "category": "infringement",
        "description": "明显侵权风险:明显侵犯他人著作权/肖像权/商标权等",
        "severity": "medium",
        "enabled": True,
        "action": "review",
        "examples": ["直接搬运他人付费课程", "冒用明星肖像代言"],
        "patterns": [],
    },
    {
        "rule_id": "COM-012",
        "category": "clickbait_exaggeration",
        "description": "标题党、夸张、绝对化表达:严重误导性标题或绝对化用语",
        "severity": "low",
        "enabled": True,
        "action": "review",
        "examples": ["震惊!不看后悔一辈子", "全网第一", "绝对最好的"],
        "patterns": [r"震惊!", r"不看.{0,4}后悔", r"全网第一", r"绝对最"],
    },
    {
        "rule_id": "COM-013",
        "category": "platform_common_risk",
        "description": "当前平台常见内容风险:可能触发平台限流/下架的常见敏感议题(政治/宗教冲突/地域争议)",
        "severity": "medium",
        "enabled": True,
        "action": "review",
        "examples": ["煽动地域对立", "宗教信仰攻击"],
        "patterns": [r"地域.*(劣等|对立|攻击)"],
    },
    {
        "rule_id": "COM-014",
        "category": "contextual_semantic",
        "description": "上下文语义风险:需结合上下文判断的隐含风险,不能仅靠关键词匹配",
        "severity": "medium",
        "enabled": True,
        "action": "review",
        "examples": ["讨论某种违法行为(可接受) vs 教唆实施(违规)", "历史战争叙述(可接受) vs 鼓励现实暴力(违规)"],
        "patterns": [],
    },
]

RULES_VERSION = "1.0"


def get_enabled_rules() -> List[Dict[str, Any]]:
    return [r for r in RULES if r.get("enabled", True)]
