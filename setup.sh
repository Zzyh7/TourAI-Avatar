#!/usr/bin/env bash
# ============================================================
#  景区导览AI数字人 — 一键环境部署脚本 (Linux / macOS)
#  评委下载项目后，在终端执行: bash setup.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}${BOLD}============================================================${NC}"
echo -e "${CYAN}${BOLD}  景区导览AI数字人 — 环境自动部署${NC}"
echo -e "${CYAN}${BOLD}============================================================${NC}"
echo ""

# ==================== 1. 检查 Python ====================
echo -e "${BOLD}[1/5] 检查 Python 环境...${NC}"

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}[错误] 未找到 Python 3.10+，请先安装 Python${NC}"
    echo "  下载: https://www.python.org/downloads/"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} 找到: $($PYTHON --version)"

# ==================== 2. 检查 Node.js ====================
echo -e "${BOLD}[2/5] 检查 Node.js 环境...${NC}"

NODE=""
for cmd in node nodejs; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+')
        if [ "$ver" -ge 18 ]; then
            NODE="$cmd"
            break
        fi
    fi
done

if [ -z "$NODE" ]; then
    echo -e "${RED}[错误] 未找到 Node.js 18+，请先安装 Node.js${NC}"
    echo "  下载: https://nodejs.org/"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} 找到: $($NODE --version)"

NPM=""
for cmd in npm pnpm yarn; do
    if command -v "$cmd" &>/dev/null; then
        NPM="$cmd"
        break
    fi
done
if [ -z "$NPM" ]; then
    echo -e "${RED}[错误] 未找到 npm，请先安装 Node.js (含 npm)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} 包管理器: $NPM"

# ==================== 3. Python 虚拟环境 ====================
echo -e "${BOLD}[3/5] 创建 Python 虚拟环境 & 安装依赖...${NC}"

if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo -e "  ${GREEN}✓${NC} 虚拟环境创建完成: venv/"
else
    echo -e "  ${GREEN}✓${NC} 虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境 (source 在当前 shell 无效，直接用 pip 路径)
PIP="venv/bin/pip"
if [ -f "venv/Scripts/pip.exe" ]; then
    # Windows Git Bash 使用 venv/Scripts/
    PIP="venv/Scripts/pip"
    PYTHON_BIN="venv/Scripts/python"
else
    PIP="venv/bin/pip"
    PYTHON_BIN="venv/bin/python"
fi

echo "  正在安装 Python 依赖 (可能需要几分钟)..."
"$PYTHON_BIN" -m pip install --upgrade pip -q 2>/dev/null
"$PIP" install -r requirements.txt -q
echo -e "  ${GREEN}✓${NC} Python 依赖安装完成"

# ==================== 4. 环境变量配置 ====================
echo -e "${BOLD}[4/5] 配置环境变量...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${YELLOW}⚠${NC} 已从 .env.example 创建 .env"
    echo -e "  ${YELLOW}  请编辑 .env 填入你的 API Key:${NC}"
    echo -e "  ${YELLOW}    - DEEPSEEK_API_KEY  (DeepSeek 大模型)${NC}"
    echo -e "  ${YELLOW}    - DASHSCOPE_API_KEY (通义千问多模态)${NC}"
    echo -e "  ${YELLOW}    - AMAP_API_KEY      (高德地图 MCP)${NC}"
else
    echo -e "  ${GREEN}✓${NC} .env 已存在，跳过"
fi

# 同时在 backend/ 也放一份，确保从 backend 目录启动时能找到
if [ ! -f "backend/.env" ]; then
    cp .env backend/.env 2>/dev/null || cp .env.example backend/.env
    echo -e "  ${GREEN}✓${NC} backend/.env 就绪"
fi

# ==================== 5. 前端依赖 ====================
echo -e "${BOLD}[5/5] 安装前端依赖...${NC}"

install_frontend() {
    local dir="$1"
    local name="$2"
    if [ -f "$dir/package.json" ]; then
        echo "  正在安装 $name 依赖..."
        cd "$dir"
        $NPM install --silent 2>/dev/null
        cd "$PROJECT_ROOT"
        echo -e "  ${GREEN}✓${NC} $name 依赖安装完成"
    else
        echo -e "  ${YELLOW}⚠${NC} $dir/package.json 不存在，跳过 $name"
    fi
}

install_frontend "frontend/visitor" "游客端 (visitor)"
install_frontend "frontend/admin" "管理后台 (admin)"

# ==================== 完成 ====================
echo ""
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo -e "${GREEN}${BOLD}  部署完成！${NC}"
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo ""
echo -e "  下一步:"
echo -e "  ${BOLD}1.${NC} 编辑 ${CYAN}.env${NC} 填入 API Key (如尚未配置)"
echo -e "  ${BOLD}2.${NC} 启动所有服务: ${CYAN}bash start.sh${NC}"
echo ""
echo -e "  手动启动方式:"
echo -e "  ${BOLD}后端:${NC}   cd backend && ../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo -e "  ${BOLD}游客端:${NC} cd frontend/visitor && npm run dev"
echo -e "  ${BOLD}管理端:${NC} cd frontend/admin && npm run dev"
echo ""
