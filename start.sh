#!/usr/bin/env bash
# ============================================================
#  景区导览AI数字人 — 一键启动所有服务 (Linux / macOS)
#  使用: bash start.sh
#  按 Ctrl+C 同时停止所有服务
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 确定 Python 路径
if [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    echo "错误: 未找到虚拟环境，请先运行: bash setup.sh"
    exit 1
fi

# 检查 .env
if [ ! -f ".env" ]; then
    echo "警告: 未找到 .env 文件，请先配置 API Key"
    echo "  从 .env.example 复制并填入你的 Key"
    exit 1
fi

# 清理函数: Ctrl+C 时停止所有后台进程
cleanup() {
    echo ""
    echo "正在停止所有服务..."
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "${VISITOR_PID:-}" ] && kill "$VISITOR_PID" 2>/dev/null
    [ -n "${ADMIN_PID:-}" ] && kill "$ADMIN_PID" 2>/dev/null
    wait 2>/dev/null
    echo "所有服务已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${CYAN}${BOLD}============================================================${NC}"
echo -e "${CYAN}${BOLD}  景区导览AI数字人 — 启动所有服务${NC}"
echo -e "${CYAN}${BOLD}============================================================${NC}"
echo ""

# 确保 data 目录存在
mkdir -p backend/data

# ==================== 1. 启动后端 (FastAPI :8000) ====================
echo -e "${BOLD}启动后端服务 (FastAPI :8000)...${NC}"
cd backend
"$PROJECT_ROOT/$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$PROJECT_ROOT"
echo -e "  ${GREEN}✓${NC} 后端 PID: $BACKEND_PID"

# ==================== 2. 启动游客端 (Vite :5173) ====================
echo -e "${BOLD}启动游客端 (Vite :5173)...${NC}"
cd frontend/visitor
npm run dev -- --host 0.0.0.0 &
VISITOR_PID=$!
cd "$PROJECT_ROOT"
echo -e "  ${GREEN}✓${NC} 游客端 PID: $VISITOR_PID"

# ==================== 3. 启动管理后台 (Vite :5174) ====================
echo -e "${BOLD}启动管理后台 (Vite :5174)...${NC}"
cd frontend/admin
npm run dev -- --host 0.0.0.0 &
ADMIN_PID=$!
cd "$PROJECT_ROOT"
echo -e "  ${GREEN}✓${NC} 管理后台 PID: $ADMIN_PID"

echo ""
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo -e "${GREEN}${BOLD}  所有服务已启动${NC}"
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo ""
echo -e "  ${BOLD}后端 API:${NC}    ${CYAN}http://localhost:8000${NC}"
echo -e "  ${BOLD}API 文档:${NC}    ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  ${BOLD}游客端:${NC}      ${CYAN}http://localhost:5173${NC}"
echo -e "  ${BOLD}管理后台:${NC}    ${CYAN}http://localhost:5174${NC}"
echo ""
echo -e "  按 ${BOLD}Ctrl+C${NC} 停止所有服务"
echo ""

# 等待所有后台进程
wait
