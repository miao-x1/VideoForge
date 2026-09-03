# VideoForge 全量产品重构 — Phase 1 审计报告

## 一、当前架构总览

### 后端结构

```
backend/app/
├── agents/          # 4 个 Agent: Requirement, Script, Storyboard, PromptCompiler
├── api/             # routes.py + auth_routes.py
├── auth/            # JWT 认证体系
├── compliance/      # ComplianceAgent + RevisionAgent + RuleEngine (14 条规则)
├── core/            # config.py + exceptions.py + logging.py
├── db/              # SQLite + SQLAlchemy (仅 3 张表)
├── guard/           # ContentGuard (分镜级风险预检)
├── input/           # 多模态输入处理 (text/image/video/url)
├── knowledge/       # Embedding + Milvus 向量搜索
├── models/          # VideoGenerationState 状态机
├── orchestrator/    # Orchestrator (单一 Pipeline)
├── providers/       # 5 类 Provider: llm/image/voice/music/video
├── router/          # ModelRouter + ModelScorer (仅视频模型路由)
├── schemas/         # VideoSpecification, StructuredRequirement, VideoScript, Storyboard
├── services/        # TaskStore (DB + 内存缓存 + SSE)
└── video/           # VideoAssembler + Quality 检测
```

### 前端结构

```
frontend/src/
├── api/client.ts          # Axios + SSE + 类型定义
├── components/
│   ├── CreativeWorkspace   # 快速/专业模式切换
│   ├── InputPanel          # 快速模式表单
│   ├── AIPlanPanel         # AI 创意分析侧栏
│   ├── ProgressTimeline    # 7 阶段进度
│   ├── VideoResult         # 结果展示
│   ├── MultiModalInput     # 多模态上传
│   ├── Sidebar/UserMenu    # 导航
│   └── panels/             # 9 个专业模式面板
├── pages/
│   ├── LoginPage           # 登录/注册
│   └── HistoryPage         # 历史 + 语义搜索
├── store/useCreativeStore  # Zustand 状态管理
└── App.tsx                 # 路由 + StudioPage
```

### 数据库结构 (当前)

| 表名 | 用途 | 状态 |
|------|------|------|
| `users` | 用户账号 | 完整 |
| `task_records` | 任务记录 (含 state_json) | 基础 |
| `task_logs` | 任务日志 | 基础 |

---

## 二、Gap 分析: 当前 vs 新规格

### 2.1 Model Registry (新规格第三章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| 统一模型注册中心 | 无 | 完全缺失 |
| 模型元数据 (model_id, provider, capabilities...) | 仅 video/capabilities.py 有部分 | 需扩展到所有模型类型 |
| 阶段级模型路由 (不同 Agent 用不同模型) | 仅视频模型有路由 | LLM/Image/Voice 路由缺失 |
| 模型评分算法 | 基础规则评分 (quality/speed/cost/fit) | 缺少风格匹配、参考素材能力评分 |
| 路由策略 (AI推荐/最佳质量/最低成本/最快速度) | 仅 auto/manual | 缺少用户策略选择 |

### 2.2 Agent Pipeline (新规格第五章、第十九章)

| Agent | 当前状态 | 缺失 |
|-------|---------|------|
| Requirement Understanding Agent | 已实现，使用 LLM | 缺少 Creative Intent 结构化输出 (subject/scene/action/emotion/lighting 等) |
| Creative Planning Agent | 无 (合并到 Requirement) | 完全缺失 |
| Script Agent | 已实现 | 基本可用 |
| Storyboard Agent | 已实现 | 基本可用 |
| **Prompt Engineering Agent** | 无 (仅有 PromptCompiler 辅助类) | **完全缺失 — 核心模块** |
| Image Generation Agent | 无独立 Agent (Orchestrator 直接调 Provider) | 缺少 Agent 层封装 |
| Model Router Agent | 已实现 (ModelRouter) | 缺少多类型路由 |
| Video Generation Agent | 无独立 Agent | 缺少 Agent 层封装 |
| Quality Agent | 已实现 (video/quality.py) | 仅基础检测，缺少主体一致性/动作异常等 |
| Compliance Agent | 已实现 | 基本可用 |
| Memory / Asset Agent | 无 | 完全缺失 |

### 2.3 Prompt Engineering (新规格第五章、第七章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| PromptCompiler 辅助类 | 已实现 (compile_visual_directives) | 仅做参数后缀附加 |
| 独立 Prompt Engineering Agent | 无 | 完全缺失 |
| 模型感知 Prompt (不同模型不同 Prompt) | 无 | 完全缺失 |
| 结构化 Prompt (Subject/Environment/Action/...) | 部分 (VideoSpecification 有这些字段) | 缺少到 Prompt 的专业编译 |
| Negative Prompt | 无 | 完全缺失 |
| 生成参数输出 | 无 | 完全缺失 |
| Prompt Inspector UI | 无 | 完全缺失 |

### 2.4 依赖感知与局部重生成 (新规格第十六、十七章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| Dependency Graph | 无 | 完全缺失 |
| 增量重生成 | 无 | 完全缺失 |
| 节点级操作 (查看/编辑/重生成/删除/锁定/复制/恢复) | 无 | 完全缺失 |
| 版本控制 | 无 | 完全缺失 |
| 影响范围分析 UI | 无 | 完全缺失 |

### 2.5 项目与连续内容 (新规格第十五、二十四章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| Project 系统 | 无 | 完全缺失 |
| Episode 系统 | 无 | 完全缺失 |
| 项目素材复用 | 无 | 完全缺失 |
| 生成历史详情 | 仅列表 (HistoryPage) | 缺少详情页和继续创作 |
| 用户独立空间 | 已实现 (JWT + user_id) | 基本可用 |

### 2.6 Asset Library (新规格第十四章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| 项目素材库 | 无 | 完全缺失 |
| Asset 数据模型 | 无 | 完全缺失 |
| @-mention 引用 | 无 | 完全缺失 |
| 资产类型 (人/场景/物品/风格...) | 无 | 完全缺失 |
| 资产 embedding + 检索 | 仅视频有 | 需扩展到所有资产类型 |

### 2.7 知识库 / 记忆系统 (新规格第二十五章)

| 能力 | 当前状态 | 缺失 |
|------|---------|------|
| 项目级记忆 | 无 | 完全缺失 |
| 风格记忆 | 无 | 完全缺失 |
| 角色记忆 | 无 | 完全缺失 |
| 场景记忆 | 无 | 完全缺失 |
| Embedding + 向量搜索 | 已实现 (仅视频) | 需扩展到所有内容类型 |

### 2.8 数据库 (新规格第二十六章)

| 新表 | 当前状态 |
|------|---------|
| users | 已存在 |
| projects | 缺失 |
| project_assets | 缺失 |
| assets | 缺失 |
| creative_intents | 缺失 |
| scripts | 缺失 |
| script_scenes | 缺失 |
| storyboards | 缺失 |
| storyboard_shots | 缺失 |
| prompts | 缺失 |
| model_registry | 缺失 |
| generation_tasks | 部分 (task_records) |
| generation_results | 缺失 |
| quality_reports | 部分 (quality_grade 字段) |
| compliance_reports | 部分 (JSONL 文件) |
| generation_versions | 缺失 |
| dependencies | 缺失 |

### 2.9 前端 UI (新规格第二十七~三十四章)

| 界面 | 当前状态 | 缺失 |
|------|---------|------|
| 首页创作入口 | 已实现 (InputPanel) | 缺少项目/素材库导航 |
| AI 理解结果展示 | 部分 (AIPlanPanel) | 缺少结构化 Creative Intent 展示和修改 |
| 脚本界面 | 仅结果展示 | 缺少编辑/新增/删除/重生成 |
| 分镜界面 | 仅结果展示 | 缺少卡片式编辑和重生成 |
| Prompt Inspector | 无 | 完全缺失 |
| 模型选择界面 | 仅下拉框 | 缺少推荐原因、评分、策略选择 |
| 生成进度界面 | 已实现 (ProgressTimeline) | 缺少真实阶段级状态 |
| 结果页面 | 已实现 (VideoResult) | 缺少重生成/换模型/延长等操作 |
| 版本控制 UI | 无 | 完全缺失 |
| 依赖图 UI | 无 | 完全缺失 |

### 2.10 AI 参与程度 (新规格第十八章)

| 模式 | 当前状态 | 缺失 |
|------|---------|------|
| 快速生成 | 已实现 (quick mode) | — |
| AI 协作 (关键节点确认) | 无 | 完全缺失 |
| 专业控制 | 已实现 (professional mode) | — |
| 底层同一 Pipeline | 已实现 | — |

---

## 三、技术债与问题清单

### 3.1 后端技术债

| # | 问题 | 严重度 | 文件 |
|---|------|--------|------|
| 1 | 无数据库迁移系统 (手动 ALTER TABLE) | 高 | db/database.py |
| 2 | 状态重建不完整 (_reconstruct_from_record 遗漏字段) | 高 | services/task_service.py |
| 3 | Orchestrator 异常处理过于宽泛 (单个 try/except) | 中 | orchestrator/orchestrator.py |
| 4 | 无任务级重试预算 | 中 | orchestrator/orchestrator.py |
| 5 | HTTP 轮询/下载逻辑在多个 Provider 重复 | 中 | providers/video/*.py |
| 6 | task_store.save() 被频繁调用 | 低 | orchestrator/orchestrator.py |
| 7 | 12 字符 hex task_id 碰撞风险 | 低 | models/state.py |
| 8 | 硬编码 Windows 字体路径 | 低 | video/assembly.py |
| 9 | ContentGuard 仅为建议性 | 中 | guard/content_guard.py |
| 10 | 搜索仅覆盖已完成视频 | 中 | knowledge/video_indexer.py |

### 3.2 前端技术债

| # | 问题 | 严重度 | 文件 |
|---|------|--------|------|
| 1 | 历史导航失效 (/?task= 未被解析) | 高 | App.tsx, HistoryPage.tsx |
| 2 | video_id 被当作 task_id 使用 | 高 | HistoryPage.tsx |
| 3 | 全部内联样式，无设计系统 | 中 | 所有组件 |
| 4 | Store 无领域分离 (无 projects/assets/versions) | 中 | useCreativeStore.ts |
| 5 | 无测试文件 | 中 | — |
| 6 | 多处 any 类型 | 低 | App.tsx |
| 7 | 无加载/错误边界 | 低 | — |
| 8 | 无状态持久化 (刷新丢失) | 中 | store |
| 9 | 无响应式布局 | 低 | — |
| 10 | 模型推荐仅在快速模式调用 | 中 | CreativeWorkspace.tsx |

### 3.3 Mock/Demo 数据清单

| 位置 | 内容 | 状态 |
|------|------|------|
| providers/llm/mock_llm.py | 硬编码"主角/配角"、"MOCK IMAGE" | 仅测试可用 (Phase 2 已门控) |
| providers/image/mock_image.py | 水印占位图 | 仅测试可用 |
| providers/voice/mock_voice.py | 静音 WAV | 仅测试可用 |
| providers/music/mock_music.py | 单音 WAV | 仅测试可用 |
| providers/video/mock_video.py | Ken Burns 占位视频 | 仅测试可用 |
| InputPanel.tsx | DEFAULT_INPUT 默认文案 | 非问题 (占位提示) |
| router/scoring_rules.py | 硬编码关键词和阈值 | 设计问题 (应模型感知) |

---

## 四、实现优先级建议

根据新规格第四十三章的优先级排序：

### 第一优先级: 用户一句话 → AI 真正理解用户想法

需要:
- 强化 RequirementAgent 输出 Creative Intent (subject/scene/action/emotion/lighting/...)
- 可能引入 Creative Planning Agent

### 第二优先级: AI 理解 → 高质量结构化创作方案

需要:
- Creative Intent → 完整创作方案的转换
- 前端 AI 理解结果展示界面 (可修改)

### 第三优先级: 创作方案 → 高质量专业 Prompt

需要:
- Prompt Engineering Agent (核心模块)
- 模型感知 Prompt 编译
- Prompt Inspector UI

### 第四优先级: 根据任务自动选择最适合的模型

需要:
- Model Registry (统一模型注册中心)
- 阶段级模型路由 (LLM/Image/Voice/Video 各有路由)
- 模型选择 UI (推荐原因/评分/策略)

### 第五优先级: 生成 → 质量检测 → 局部修改 → 局部重生成

需要:
- Dependency Graph
- 增量重生成
- 版本控制
- 节点级操作 UI

---

## 五、建议实现路径 (11 个 Phase)

| Phase | 内容 | 修改范围 | 预估工作量 |
|-------|------|---------|-----------|
| 1 | 完整审查 (本报告) | 无修改 | 已完成 |
| 2 | Model Registry + Provider Abstraction + Model Router | 后端核心 | 大 |
| 3 | Orchestrator + Agent Pipeline 强化 | 后端核心 | 大 |
| 4 | Requirement Understanding Agent 强化 | 后端 Agent | 中 |
| 5 | Prompt Engineering Agent | 后端核心 | 大 |
| 6 | Image/Video Model Router 完善 | 后端路由 | 中 |
| 7 | Storyboard/Script/Prompt Inspector | 前端 UI | 中 |
| 8 | Dependency Graph + Incremental Regeneration + Version Control | 全栈 | 大 |
| 9 | User/Project/Asset/History/Memory | 全栈 | 大 |
| 10 | Compliance + Quality 强化 | 后端 | 中 |
| 11 | UI/UX 统一优化 | 前端 | 中 |

---

## 六、结论

VideoForge 已有的基础:
- 可用的 Agent Pipeline (Requirement → Script → Storyboard → Media → Assembly)
- 可用的 Provider 抽象 (LLM/Image/Voice/Music/Video)
- 可用的 ModelRouter (视频模型)
- 可用的用户认证 + SQLite 持久化
- 可用的 SSE 实时进度
- 可用的多模态输入 + 语义搜索

VideoForge 缺失的核心:
- Model Registry (统一模型注册中心)
- Prompt Engineering Agent (核心模块)
- Creative Intent 结构化输出
- Dependency Graph + 增量重生成
- Project/Episode 系统
- Asset Library
- 版本控制
- Prompt Inspector UI
- 模型选择 UI
- 13 张数据库表

按照新规格的 11 个 Phase 逐步实现，每个 Phase 聚焦一个核心领域。
