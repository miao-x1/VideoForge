# VideoForge

在 3D 导演台里摆场景、定镜头，生成视频。登录后可在历史作品里查看、改名、删除自己的成片。

https://github.com/miao-x1/VideoForge

## 怎么跑

```bash
git clone https://github.com/miao-x1/VideoForge.git
cd VideoForge
```

后端：

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
# 在 .env 里填 MINIMAX_API_KEY，APP_ENV=development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 ，注册登录后进导演台。

## 怎么用

1. 导演台摆角色和镜头  
2. 底部点「生成视频」  
3. 历史作品里看自己的片子  

出片用 MiniMax。可以配服务器 Key，也可以在设置里填自己的 Key。  
不要提交 `.env` 和 `storage` 里的数据库、成片。
