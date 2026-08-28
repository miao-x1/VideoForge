# VideoForge

> 自然语言创意 → AI 拆解脚本与分镜 → 真实素材生成（文生图 / 图生视频 / TTS / BGM）→ 视频合成 → 输出竖屏 MP4

VideoForge 是一个端到端的 AI 短视频自动生成引擎。输入一句话创意，系统通过 LLM 完成需求理解、脚本撰写、分镜拆解，调用真实 AI 模型生成图片、旁白、背景音乐与动态视频片段，最终合成带字幕的竖屏短视频。内置内容合规预审层，对脚本进行规则 + 语义双重检查，自动修订高风险内容，并在边界场景标记人工审核。

## 功能特性

- **全链路自动生成**：一句话创意 → 脚本 → 分镜 → 文生图 → 图生视频 → TTS → BGM → 合成 MP4，无需人工介入
- **真实 AI 能力**：基于阿里云 DashScope 通义系列模型，覆盖文本理解、图像生成、语音合成、视频生成
- **内容合规预审**：独立 Compliance Agent，规则引擎 + LLM 语义判断双层架构，输出结构化合规报告，支持自动修订与人工审核兜底
- **内容安全护栏**：ContentGuard 三维度（安全 / 平台 / 文化）风险评估，分镜级内容审查
- **图生视频 + Ken Burns 双模式**：I2V 生成连续动态片段，失败时自动回退 Ken Burns 镜头运动，保证视频产出
- **可插拔 Provider 架构**：LLM / Image / Voice / Music / Video 每层都支持 Mock 与真实实现切换，`.env` 一行切换
- **实时进度推送**：FastAPI + SSE，前端实时展示任务阶段与日志
- **视频质量校验**：自动检查分辨率、帧率、音轨、时长，输出质量评级

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI、Python 3.10+、Pydantic |
| 前端 | React 18、TypeScript、Ant Design 5、Vite |
| AI 模型 | 通义千问 qwen-plus（LLM）、通义万相 wanx2.1-t2i-turbo（文生图）、wan2.6-i2v-flash（图生视频）、qwen-audio-3.0-tts-flash（TTS） |
| 视频合成 | MoviePy 2.x、FFmpeg |
| 实时通信 | Server-Sent Events（SSE） |
| 配置 | pydantic-settings、.env |

## Pipeline 架构

```
用户输入创意
    │
    ▼
┌─────────────┐
│ Requirement  │  LLM 理解创意 → 主题 / 风格 / 角色 / 时长
└─────┬───────┘
      ▼
┌─────────────┐
│   Script    │  LLM 生成标题 / Hook / 场景 / 旁白
└─────┬───────┘
      ▼
┌─────────────────┐
│ Compliance Agent │  规则筛查 + LLM 语义判断
│  (可配置开关)     │  ├─ pass  → 继续
└─────┬───────────┘  ├─ review → 标记人工审核
      │               └─ reject → Revision Agent 自动修订 → 复检
      ▼                  （最多 2 次，耗尽进入人工审核）
┌─────────────┐
│  Storyboard  │  LLM 拆解分镜 → 镜头 / 运镜 / 画面描述
└─────┬───────┘
      ▼
┌─────────────┐
│ ContentGuard │  分镜级三维度风险评估（安全 / 平台 / 文化）
└─────┬───────┘
      ▼
┌─────────────┐
│    Media     │  文生图 → 图生视频（失败回退 Ken Burns）→ TTS → BGM
└─────┬───────┘
      ▼
┌─────────────┐
│  Assembly    │  MoviePy 合成 → 字幕叠加 → BGM 混音 → 输出 MP4
└─────┬───────┘
      ▼
   竖屏 MP4 + 质量报告
```

## 目录结构

```
VideoForge/
├── backend/
│   ├── app/
│   │   ├── api/routes.py              # FastAPI 路由（REST + SSE）
│   │   ├── agents/                    # 需求 / 脚本 / 分镜 Agent
│   │   ├── orchestrator/orchestrator.py  # 状态机驱动 + 阶段编排
│   │   ├── compliance/                # 内容合规预审 Agent
│   │   │   ├── compliance_agent.py    #   规则 + LLM 双层判断
│   │   │   ├── rule_engine.py         #   确定性规则筛查
│   │   │   ├── rules_data.py          #   规则配置（COM-001~014）
│   │   │   ├── revision_agent.py     #   脚本自动修订
│   │   │   ├── audit.py               #   审计日志落盘
│   │   │   └── models.py              #   结构化合规结果模型
│   │   ├── guard/content_guard.py     # 分镜级内容安全护栏
│   │   ├── models/state.py            # 任务状态 + 全局状态机
│   │   ├── schemas/                   # Pydantic 数据契约
│   │   ├── providers/                 # 可插拔 Provider
│   │   │   ├── llm/                   #   LLM（mock / dashscope）
│   │   │   ├── image/                 #   文生图（mock / dashscope / seedream）
│   │   │   ├── voice/                 #   TTS（mock / dashscope）
│   │   │   ├── music/                 #   BGM（mock / ambient）
│   │   │   └── video/                 #   图生视频（mock / dashscope）
│   │   ├── services/task_service.py   # 任务存储 + SSE 推送
│   │   ├── video/                     # 合成 + 质量校验
│   │   │   ├── assembly.py            #   MoviePy 合成 MP4
│   │   │   └── quality.py            #   视频质量校验
│   │   ├── core/                      # 配置 + 日志
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/                          # React 18 + TS + Ant Design
│   └── src/
│       ├── components/                # 输入面板 / 进度时间线 / 视频结果
│       ├── api/client.ts
│       └── App.tsx
├── storage/                           # 生成产物（.gitignore 排除）
│   ├── images/                       #   分镜图
│   ├── audio/                         #   TTS + BGM
│   ├── clips/                         #   I2V 动态片段
│   ├── videos/                        #   最终 MP4
│   └── audit/                         #   合规审计日志
└── tests/                             # 端到端测试 + 专项验证
```

## 快速开始

### 1. 环境准备

```bash
git clone <repo-url>
cd VideoForge
```

### 2. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux
```

在 `.env` 中填入 DashScope API Key：

```
LLM_API_KEY=your_dashscope_api_key
LLM_PROVIDER=dashscope
IMAGE_PROVIDER=dashscope
VOICE_PROVIDER=dashscope
I2V_PROVIDER=dashscope
MUSIC_PROVIDER=ambient
```

启动服务：

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

界面预填样例创意，点击「开始生成」即可。任务进度通过 SSE 实时推送。

### 4. 不依赖前端运行

```bash
# 全 Mock 模式（无需 API Key，用于本地开发验证）
python tests/test_pipeline.py

# 真实 Pipeline（需配置 DashScope API Key）
python tests/run_compliance_pipeline.py
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/video/tasks` | 创建视频生成任务 |
| GET | `/api/video/tasks/{id}` | 获取任务全量状态 |
| GET | `/api/video/tasks/{id}/status` | 获取状态与日志 |
| GET | `/api/video/tasks/{id}/result` | 获取终态产物（含 video_url） |
| GET | `/api/video/tasks/{id}/stream` | SSE 实时进度推送 |

## 配置说明

核心环境变量（详见 `.env.example`）：

```bash
# Provider 切换（mock = 本地占位，dashscope = 真实 AI）
LLM_PROVIDER=dashscope
IMAGE_PROVIDER=dashscope
VOICE_PROVIDER=dashscope
I2V_PROVIDER=dashscope
MUSIC_PROVIDER=ambient

# 模型选择
LLM_MODEL=qwen-plus
IMAGE_MODEL=wanx2.1-t2i-turbo
I2V_MODEL=wan2.6-i2v-flash
TTS_MODEL=qwen-audio-3.0-tts-flash
TTS_VOICE=longanhuan_v3.6
TTS_LANGUAGE=zh-CN

# 视频输出（9:16 竖屏）
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=24

# 内容合规预审
COMPLIANCE_CHECK_ENABLED=true
COMPLIANCE_MAX_REVISIONS=2
COMPLIANCE_AUDIT_ENABLED=true
COMPLIANCE_HALT_ON_REVIEW=false
```

## 内容合规预审

Compliance Agent 作为 Pipeline 的独立阶段，位于脚本生成之后、分镜拆解之前。

**双层检查机制**：

1. **规则引擎**（RuleEngine）：基于正则的确定性快速筛查，覆盖 14 类风险（违法违规、色情露骨、极端暴力、仇恨歧视、危险行为、医疗虚假、金融虚假、虚假信息、历史错误、未成年人风险、侵权、标题党、平台风险、上下文语义）。规则配置在 [rules_data.py](backend/app/compliance/rules_data.py)，新增规则无需改代码。

2. **LLM 语义判断**：结合上下文分析，区分「讨论违法行为」与「教唆违法」、「历史战争叙述」与「鼓励现实暴力」等语境差异，避免关键词黑名单的误判。

**三态输出**：

| 状态 | 含义 | 处理 |
|------|------|------|
| pass | 无明显风险 | 继续 Pipeline |
| review | 边界问题 | 标记人工审核（可配置是否阻断） |
| reject | 明确高风险 | 触发 Revision Agent 自动修订，复检最多 2 次，耗尽进入人工审核 |

**失败保护**：LLM 调用失败或 JSON 解析异常时，降级为 review + 人工审核标记，绝不自动放行。

**审计日志**：每次审核记录 request_id / content_id / timestamp / status / risk_level / violations / revision_count，落盘至 `storage/audit/compliance_audit.jsonl`。

**多模态扩展**：`BaseComplianceAgent` 抽象基类已定义，未来可扩展 ImageComplianceAgent / VideoComplianceAgent。

## Provider 架构

每层 AI 能力通过 Provider 抽象隔离，Agent 与 Orchestrator 不直接依赖具体实现：

```
providers/
├── llm/        LLMProvider      → MockLLMProvider / DashScopeLLMProvider
├── image/     ImageProvider     → MockImageProvider / DashScopeImageProvider / SeedreamImageProvider
├── voice/     VoiceProvider     → MockVoiceProvider / DashScopeVoiceProvider
├── music/     MusicProvider     → MockMusicProvider / AmbientMusicProvider
└── video/     VideoProvider     → MockI2VProvider / DashScopeI2VProvider
```

切换 Provider 只需修改 `.env`，无需改动业务代码。新增 Provider 实现对应基类并在工厂方法分发即可。

## 测试

```bash
# Pipeline 端到端（全 Mock，无需 API Key）
python tests/test_pipeline.py

# Compliance Agent 测试套件（10 用例）
python tests/test_compliance.py

# 真实 Pipeline 验收（需 DashScope API Key + 额度）
python tests/run_compliance_pipeline.py
```

Compliance Agent 测试覆盖：正常内容通过、违法内容拒绝、医疗绝对化识别、危险历史叙述上下文判断、模糊边界人工审核、JSON 异常降级、LLM 失败保护、修订耗尽人工审核、原有 Pipeline 不破坏。

## 已知限制

- **I2V 固定 5 秒**：wan2.6-i2v-flash 输出固定 5s 片段，当 shot 数量 × 5s ≠ 目标时长时会产生偏差，需通过 shot 数量或末尾补齐对齐
- **I2V 内容安全审核**：DashScope 对生成视频执行绿网检查，部分 prompt + 图片组合可能触发 `DataInspectionFailed`，系统自动回退 Ken Burns 模式保证产出
- **合规预审定位于第一道防线**：AI 预审 + 风险识别 + 自动修订 + 人工审核兜底，不替代人工最终审核，不声称 100% 合规判定
- **DashScope 账户额度**：真实 Pipeline 依赖账户可用额度，欠费时返回 `Arrearage` 错误
- **多模态审核**：当前实现文本合规检查，图片 / 视频审核接口已设计（BaseComplianceAgent），尚未实现
