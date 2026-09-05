# VideoForge

3D 导演台：在摄影棚里摆角色、定镜头、贴场景图，从底部生成视频。成片记在当前账号下，可在历史作品里查看、改名、删除。

仓库：https://github.com/miao-x1/VideoForge

## 现在能做什么

- **导演台**：3D 视口布置角色 / 道具 / 机位，场景自动保存
- **出片**：底部「生成视频」走 MiniMax-H3，支持时长和画幅；生成中也可打开历史记录
- **历史作品**：登录账号下已生成的图片和视频，支持查看、改名、删除
- **计费**：平台钱包按秒扣费（开发环境新用户有测试额度）；也可在设置里填自己的 MiniMax Key（不扣本站余额）
- **登录**：邮箱 / 手机号注册登录后才能进导演台

尚未开放、不要按已上线理解：图生 3D、角色商城、微信支付充值。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18、TypeScript、Vite、Ant Design 5、Three.js / R3F |
| 后端 | FastAPI、SQLAlchemy、Alembic、SQLite（可换 DATABASE_URL） |
| 出片 | MiniMax-H3（平台 Key 或用户 BYOK） |
| 鉴权 | JWT |

## 目录

```
VideoForge/
├── backend/
│   ├── app/
│   │   ├── api/                 # 登录、导演台、生成、素材、计费
│   │   ├── generation/          # 出片版本链、轮询、落盘
│   │   ├── billing/             # 钱包、扣费、用户 Key
│   │   ├── db/                  # 模型、所有权、Alembic
│   │   └── providers/video/     # MiniMax / Qwen
│   ├── alembic/                 # 数据库迁移
│   └── .env.example
├── frontend/
│   ├── src/director/            # 导演台页面与 3D 摄影棚
│   └── src/pages/HistoryPage.tsx
└── storage/                     # 本地库和成片（不入库）
```

## 快速开始

### 1. 克隆

```bash
git clone https://github.com/miao-x1/VideoForge.git
cd VideoForge
```

### 2. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

开发环境把 `APP_ENV` 保持为 `development`。出片至少要配一项：

```
APP_ENV=development
MINIMAX_API_KEY=你的_minimax_key
MINIMAX_VIDEO_MODEL=MiniMax-H3
VIDEO_MODEL_PROVIDER=minimax
```

用户也可以在导演台设置里填写自己的 MiniMax Key，不配服务器 Key 也能出片。

启动：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Windows 上请绑 `127.0.0.1`。前端把 `localhost` 解析到 IPv6 时，验证码等接口会 404。

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 ，注册登录后进入导演台。

## 使用顺序

1. 注册并登录
2. 左侧进导演台：放角色、调机位、需要时贴场景图
3. 底部选时长 / 画幅，点「生成视频」（通常 2–4 分钟）
4. 成片可在本页播放，或打开右上角「历史记录」
5. 侧栏「历史作品」管理本账号全部成片

## 计费说明

| 方式 | 谁出 MiniMax 的钱 | 本站钱包 |
|------|-------------------|----------|
| 平台 Key（服务器 `.env`） | 运营方 MiniMax 账户 | 按秒扣本站额度 |
| 用户自己的 Key | 用户的 MiniMax 账户 | 不扣 |

开发环境新账号会有测试额度，仅写在本地 SQLite，不是微信支付，也不是给 MiniMax 充值。生产充值接口尚未接入。

## 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` `/login` | 注册 / 登录 |
| POST | `/api/director/generate/video` | 提交出片（`wait=false` 后轮询） |
| GET | `/api/director/generate/works` | 当前用户全部成片 |
| PATCH / DELETE | `/api/director/generate/{id}` | 改名 / 删除 |
| GET | `/api/billing/wallet` | 钱包余额 |

## 测试

```bash
cd backend
python -m pytest tests/test_wave0_security.py tests/test_wave1_alembic.py tests/test_wave4_generation.py -q
```

## 不要提交的内容

- `backend/.env` 和任何 API Key
- `storage/videoforge.db`、成片、上传图

配置模板见 [backend/.env.example](backend/.env.example)。
