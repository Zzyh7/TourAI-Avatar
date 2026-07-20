# 🏛️ 景区导览AI数字人 — TourAI

> **A5竞赛项目** | 基于 Multi-Agent + RAG + MCP 的智能景区导览数字人系统
>
> **Live2D 小僧数字人** · **语音对话** · **拍照识景** · **个性化推荐** · **地图服务**

---

## 快速开始

### 环境要求

| 工具 | 最低版本 | 说明 |
|------|---------|------|
| **Python** | 3.10+ | 后端运行环境 |
| **Node.js** | 18+ | 前端运行环境（含 npm/pnpm） |

### 配置 API Key

编辑 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DASHSCOPE_API_KEY=sk-your-dashscope-api-key-here
AMAP_API_KEY=your-amap-api-key-here
DOUBAO_TTS_API_KEY=your-doubao-tts-key-here
```

| Key | 用途 | 申请地址 |
|-----|------|---------|
| `DEEPSEEK_API_KEY` | 大模型对话 | https://platform.deepseek.com/ |
| `DASHSCOPE_API_KEY` | 多模态拍照识景 + 语音识别 | https://dashscope.console.aliyun.com/ |
| `AMAP_API_KEY` | 高德地图 MCP | https://lbs.amap.com/ |
| `DOUBAO_TTS_API_KEY` | 豆包语音合成 | https://console.volcengine.com/speech |

### 启动服务

**Windows：**
```bat
双击 start.bat
```

**macOS / Linux：**
```bash
bash start.sh
```

### 服务地址

| 服务 | 地址 |
|------|------|
| 🌐 暗黑首页 | http://localhost:8000 |
| 🧠 后端 API | http://localhost:8000 |
| 📖 Swagger 文档 | http://localhost:8000/docs |
| 👤 Live2D 数字人 | http://localhost:3000/sentio |
| 🎨 游客端 | http://localhost:5173 |
| ⚙️ 管理后台 | http://localhost:5174 |

> **提示**：数字人互动请打开 `localhost:3000/sentio`，文字和语音对话都在数字人页面内。

---

## 系统架构

```
浏览器
  ├─ :3000/sentio  →  Live2D 小僧数字人 (Next.js)
  │     ├─ /adh/agent/v0/engine  →  Live2D API :8880 → TourAI :8000/v1
  │     ├─ /adh/tts/v0/engine    →  Live2D API :8880 → TourAI :8000/api/tts
  │     └─ /adh/asr/v0/engine    →  Live2D API :8880 → DashScope 语音识别
  │
  ├─ :5173  →  游客端 (React + Vite)
  ├─ :5174  →  管理后台 (React + Vite)
  └─ :8000  →  暗黑首页 + 地图页 (静态 HTML)
                 │
                 ▼
        TourAI Backend :8000 (FastAPI)
        ├─ /api/chat            SSE 流式问答 + RAG + TTS
        ├─ /api/stt             语音识别 (DashScope Paraformer)
        ├─ /api/tts             语音合成 (Edge-TTS)
        ├─ /api/photo-recognize 拍照识景 (通义千问-VL)
        ├─ /v1/chat/completions OpenAI 兼容接口 (供 Live2D)
        └─ /api/admin/*         管理后台 API
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
    DeepSeek  阿里百炼   高德MCP
     (LLM)   (多模态+ASR)  (地图)
```

---

## 核心功能

| 能力 | 说明 |
|------|------|
| 👤 **Live2D 小僧数字人** | 4 表情状态（中性/开心/思考/播报），沉浸式 AI 导览 |
| 🗣️ **RAG 智能问答** | FAISS + BM25 + RRF 混合检索 + DeepSeek，275条景区知识库 |
| 🎤 **语音对话** | DashScope Paraformer 识别 + Edge-TTS 合成，自然语音交互 |
| 📷 **拍照识景** | 通义千问-VL 多模态识别 + RAG 知识增强，实时讲解 |
| 📍 **地图服务** | 高德 MCP 15 工具，POI搜索/天气/路线规划/GPS触发讲解 |
| 🧭 **个性化推荐** | 家庭游 / 文化深度游 / 休闲游 / 祈福游 |
| 📊 **管理后台** | 数据大屏 / 满意度追踪 / 答不上率统计 / FAQ管理 / 员工账号 |
| 🌐 **暗黑电影级首页** | 金色描边 + 荧光字体 + 轮播Hero + 平滑滚动 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **AI/Agent** | LangChain + LangGraph + DeepSeek |
| **RAG 检索** | FAISS + BM25 + RRF 混合检索 |
| **语音合成** | Edge-TTS |
| **语音识别** | DashScope Paraformer |
| **数字人** | AWESOME-DIGITAL-HUMAN Live2D v3.0 |
| **数据库** | SQLite + SQLAlchemy |
| **前端** | React 18 + TypeScript + Vite 5 |
| **管理端** | React + ECharts |
| **数字人前端** | Next.js 15 + Tailwind + pnpm |
| **地图服务** | 高德 MCP (Model Context Protocol) |
| **多模态** | 通义千问-VL (DashScope) |

---

## 项目结构

```
TourAI-Avatar/
├── backend/                    # Python 后端 (FastAPI)
│   ├── main.py                 # API 入口 & SSE 流式对话
│   ├── config.py               # 配置中心
│   ├── database.py             # 数据库 ORM (SQLAlchemy)
│   ├── openai_compat_api.py    # OpenAI 兼容接口 (供 Live2D)
│   ├── agents/                 # Multi-Agent 导览系统
│   │   ├── planner.py          # GuideAgent 主控
│   │   └── specialist.py       # SpecialistAgent 基类
│   ├── services/
│   │   ├── tts/                # TTS 语音合成 (Edge-TTS)
│   │   ├── stt/                # STT 语音识别 (DashScope)
│   │   └── sentiment/          # 情感分析
│   ├── rag_system/             # RAG 混合检索系统
│   │   ├── hybrid_retriever.py # FAISS + BM25 + RRF
│   │   └── api.py              # RAG 管理 API
│   └── admin/                  # 管理后台路由 (12模块)
│       ├── stats.py            # 满意度 + 答不上率统计
│       └── analytics.py        # 游客分析
├── frontend/
│   ├── visitor/                # 游客端 (React + Vite + TypeScript)
│   └── admin/                  # 管理后台 (React + Vite + TypeScript)
├── live2d/                     # Live2D 数字人 (awesome-digital-human)
│   ├── web/                    # Next.js 前端
│   ├── configs/                # ASR/TTS/Agent 引擎配置
│   └── digitalHuman/           # Python API 服务端
├── web/                        # 静态页面 (暗黑首页 + 地图 + 轮播)
├── data/                       # 知识库 & 向量数据库
├── docs/                       # 设计文档
├── start.py                    # 一键启动脚本
└── .env                        # API Key 配置
```

---

## 开发历程

### Phase 1 — 核心引擎
- FastAPI + LangChain + LangGraph Multi-Agent 导览系统
- GuideAgent 总控 + 3 个 SpecialistAgent（天气/景点/路线）
- FAISS + BM25 + RRF 混合检索引擎，BGE-small-zh 本地嵌入
- 高德 MCP 15 工具标准化接入
- DeepSeek 大模型 + 通义千问-VL 多模态拍照识景

### Phase 2 — 前端与语音
- React 18 游客端 & 管理后台
- 暗黑电影级首页 + 移动端 H5 适配 + PWA
- Edge-TTS 语音合成 + DashScope Paraformer 语音识别
- SSE 流式对话 + 句级 TTS 并行合成
- 管理后台 12 模块 + 员工账号系统

### Phase 3 — 数字人集成
- AWESOME-DIGITAL-HUMAN Live2D v3.0 深度集成
- 小僧 Live2D 角色：4 表情状态 + 背景自定义
- OpenAI 兼容 API 桥接 Live2D ↔ TourAI
- DashScope 语音识别引擎直连

### Phase 4 — 数据与体验优化
- 满意度追踪 + 答不上率统计 + 负面对话记录
- 拟人化对话 Prompt：禁用"根据资料"等机械用语
- 首页字体加粗 + 金色描边 + 荧光效果
- 自定义卡片图标 + 数字人背景
- 275 条 FAQ 精标知识库

---

## 常见问题

**Q: 数字人文字/语音输入没反应？**
确认访问的是 `http://localhost:3000/sentio`，不是 `localhost:5173`。

**Q: 语音识别不可用？**
确认 `.env` 中 `DASHSCOPE_API_KEY` 已配置有效的阿里百炼 Key。

**Q: TTS 语音没声音？**
确认后台管理 → 系统配置 → 音色选择正确（Edge-TTS 中文男声如 `zh-CN-YunxiNeural`）。

**Q: 端口被占用？**
启动脚本 `start.py` 会自动释放 8000/5173/5174 端口。数字人 3000/8880 端口需手动清理。
