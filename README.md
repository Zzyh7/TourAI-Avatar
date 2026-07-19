# 🏛️ 景区导览AI数字人 — TourAI

> **A5竞赛项目** | 基于 Multi-Agent + RAG + MCP 的智能景区导览数字人系统
>
> 支持 **Live2D小和尚数字人** · **语音对话** · **拍照识景** · **个性化推荐** · **地图服务**

---

## 快速开始（评委请直接看这里）

### 第一步：环境要求

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| **Python** | 3.10+ | 后端运行环境 |
| **Node.js** | 18+ | 前端运行环境（含 npm） |

### 第二步：一键部署

下载项目后，在项目根目录打开终端，运行部署脚本：

**Windows：**
```bat
双击 setup.bat
```

**macOS / Linux：**
```bash
bash setup.sh
```

脚本会自动完成：
1. ✅ 检查 Python & Node.js 环境
2. ✅ 创建 Python 虚拟环境
3. ✅ 安装所有 Python 依赖
4. ✅ 安装前端依赖（游客端 + 管理后台）
5. ✅ 创建 `.env` 配置文件模板

### 第三步：配置 API Key

编辑项目根目录的 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DASHSCOPE_API_KEY=sk-your-dashscope-api-key-here
AMAP_API_KEY=your-amap-api-key-here
```

| Key | 用途 | 申请地址 |
|-----|------|---------|
| `DEEPSEEK_API_KEY` | 大模型对话（DeepSeek） | https://platform.deepseek.com/ |
| `DASHSCOPE_API_KEY` | 多模态拍照识景（通义千问-VL） | https://dashscope.console.aliyun.com/ |
| `AMAP_API_KEY` | 地图服务（高德 MCP） | https://lbs.amap.com/ |
| `DOUBAO_TTS_API_KEY` | 豆包语音合成（火山引擎） | https://console.volcengine.com/speech |

### 第四步：启动所有服务

**Windows：**
```bat
双击 start.bat
```

**macOS / Linux：**
```bash
bash start.sh
```

服务启动后：

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| Live2D 数字人 | http://localhost:3000/sentio |
| 游客端 | http://localhost:5173 |
| 管理后台 | http://localhost:5174 |

---

## 手动启动（可选）

如果你希望手动控制每个服务：

```bash
# 1. 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. 启动后端
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. 新终端，启动游客端
cd frontend/visitor
npm run dev

# 4. 新终端，启动管理后台
cd frontend/admin
npm run dev
```

---

## 项目结构

```
TravelAgent/
├── backend/                    # Python 后端 (FastAPI)
│   ├── main.py                # API 入口 & SSE 流式对话
│   ├── config.py              # 配置中心（LLM/TTS/RAG/数据库）
│   ├── database.py            # 数据库 ORM (SQLAlchemy)
│   ├── rag_system.py          # RAG 检索系统 (FAISS + BM25 + RRF)
│   ├── models/                # 数据模型 (SQLAlchemy)
│   ├── agents/                # Multi-Agent 导览系统
│   │   ├── planner.py         # GuideAgent 主控
│   │   └── ...
│   ├── services/              # 服务层
│   │   ├── tts/               # TTS 语音合成 (Edge-TTS)
│   │   └── common_dialogue/   # 常用对话匹配
│   ├── admin/                 # 管理后台路由
│   └── data/                  # 知识库 & 向量数据库
├── frontend/
│   ├── visitor/               # 游客端 (React + Vite + TypeScript)
│   │   └── src/
│   │       ├── App.tsx        # 主应用
│   │       ├── components/    # UI 组件
│   │       └── services/      # API 调用
│   └── admin/                 # 管理后台 (React + Vite + TypeScript)
├── docs/
│   └── 产品总体设计文档.md     # 详细设计文档
├── requirements.txt           # Python 依赖清单
├── .env.example               # 环境变量模板
├── setup.sh / setup.bat       # 一键部署脚本
├── start.sh / start.bat       # 一键启动脚本
└── README.md                  # 本文件
```

---

## 核心功能

| 能力 | 说明 |
|------|------|
| 👤 **Live2D 数字人** | 小和尚角色，4 表情状态，语音交互，沉浸式 AI 导览 |
| 🗣️ **智能问答** | RAG (FAISS+BM25+RRF) + DeepSeek，275条FAQ+景区知识库 |
| 🎤 **语音对话** | 豆包 Seed-TTS-2.0 语音合成 + DashScope Paraformer 语音识别 |
| 📷 **拍照识景** | 通义千问-VL 多模态识别 + RAG 知识增强，实时讲解 |
| 📍 **地图服务** | 高德 MCP 15 工具，POI搜索/天气/路线/GPS触发讲解 |
| 🧭 **个性化推荐** | 家庭游/文化深度游/休闲游/祈福游，千人千面 |
| 📊 **管理后台** | 12 模块数据大屏，满意度+答不上率统计，员工管理 |
| 🔧 **知识库管理** | 文档上传(PDF/Word/TXT/MD)，自动分块+向量化+混合检索 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **AI/Agent** | LangChain + LangGraph + DeepSeek |
| **RAG 检索** | FAISS + BM25 + RRF 混合检索 |
| **语音合成** | 豆包 TTS (Seed-TTS-2.0 WebSocket) |
| **数据库** | SQLite + SQLAlchemy |
| **前端** | React 18 + TypeScript + Vite 5 |
| **地图服务** | 高德 MCP (Model Context Protocol) |
| **多模态** | 通义千问-VL (DashScope) |

---

## 开发历程

### Phase 1 — 核心引擎搭建
- 基于 **FastAPI + LangChain + LangGraph** 搭建 Multi-Agent 导览系统
- GuideAgent 总控 + 3 个 SpecialistAgent（天气/景点/路线），最小权限原则
- **RAG 混合检索**：FAISS 向量 + BM25 关键词 + RRF 排名融合，BGE-small-zh 本地嵌入
- **MCP 协议集成**：高德地图 15 个工具标准化接入，单例管理器懒加载
- DeepSeek 大模型对话 + 通义千问-VL 多模态拍照识景
- SQLite 数据库：会话/对话/文档/景点/数字人配置/员工账号

### Phase 2 — 前端与语音
- React 18 + Vite + TypeScript 游客端 & 管理后台
- **暗黑电影级首页** + 移动端 H5 适配 + PWA 支持
- 豆包 TTS (火山引擎) → 升级到 **Seed-TTS-2.0 WebSocket V3** 协议
- Edge-TTS 作为免费备选方案
- 双语音识别：浏览器 Web Speech API + DashScope Paraformer 服务端 STT
- SSE 流式对话 + **句级 TTS 并行合成**（边生成边播报，首音延迟<2s）
- 回答中断机制：客户端断开自动取消 LLM + TTS

### Phase 3 — 数字人集成
- 集成 **AWESOME-DIGITAL-HUMAN Live2D** (v3.0.0)
- 小和尚 Live2D 角色：4 种表情状态（中性/开心/思考/播报）
- OpenAI 兼容 API (`/v1/chat/completions`) 桥接 Live2D ↔ TourAI
- TTS 引擎对接：Live2D → TourAI 代理 → 豆包/Edge 语音合成
- STT 引擎对接：Live2D → TourAI 代理 → DashScope Paraformer 语音识别
- 暗色三栏布局 + 推荐卡片 + GPS 景点触发

### Phase 4 — 数据与管理
- **管理后台 12 个模块**：数据大屏/景点热度/时间对比/问答分析/游客画像/游客分层/负面反馈/常用对话/会话记录/知识库文档/景点管理/系统配置
- **员工账号系统**：登录/权限/增删改查
- 275 条 FAQ 精标 + 30 条常用对话 + 34 条无关问题处理
- **满意度追踪**：显式关键词识别（"我很满意"/"我不满意"）+ LLM 情感分析
- **答不上率统计**：自动检测系统无法回答的问题并量化
- 精细化 Prompt 工程：禁用"根据资料"等机械用语，拟人口语风格

### 系统架构速览

```
浏览器 / 手机
    ├─ http://localhost:3000/sentio  →  Live2D 小和尚数字人 (Next.js)
    │     ├─ /adh/agent/v0/engine    →  Live2D API :8880 → TourAI :8000/v1
    │     ├─ /adh/tts/v0/engine      →  Live2D API :8880 → TourAI :8000/api/tts
    │     └─ /adh/asr/v0/engine/file →  Live2D API :8880 → TourAI :8000/api/stt
    │
    ├─ http://localhost:5173  →  游客端 (React + Vite)
    └─ http://localhost:5174  →  管理后台 (React + Vite)
                   │
                   ▼
          TourAI Backend :8000 (FastAPI)
          ├─ /api/chat          SSE 流式问答 + RAG + TTS
          ├─ /api/stt           语音识别 (DashScope Paraformer)
          ├─ /api/tts           语音合成 (豆包/Edge)
          ├─ /api/photo-recognize  多模态拍照识景
          ├─ /v1/chat/completions  OpenAI 兼容 (供 Live2D)
          └─ /api/admin/*       管理后台 API
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
      DeepSeek  阿里百炼   高德MCP
       (LLM)   (多模态+STT)  (地图)</pre>
```

---

## 常见问题

### Q: 启动后端报 "请配置 DEEPSEEK_API_KEY"
编辑项目根目录的 `.env` 文件，确保已填入有效的 DeepSeek API Key。

### Q: 虚拟环境激活失败
- Windows PowerShell 可能需要先执行：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- 也可以直接用 `venv\Scripts\python` 代替 `python`，无需激活

### Q: npm install 很慢或失败
- 设置国内镜像：`npm config set registry https://registry.npmmirror.com`
- 然后重新运行 setup 脚本，或手动 `cd frontend/visitor && npm install`

### Q: pip install 很慢或失败
- 使用国内镜像：`venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### Q: 端口被占用 (8000/5173/5174)
- 后端端口可在 `start.sh`/`start.bat` 中修改 `--port` 参数
- 前端端口可在 `frontend/visitor/vite.config.ts` 和 `frontend/admin/vite.config.ts` 中修改
