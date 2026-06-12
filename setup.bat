@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  景区导览AI数字人 — 一键环境部署脚本 (Windows)
::  评委下载项目后，双击 setup.bat 或在终端执行
:: ============================================================

echo.
echo ============================================================
echo   景区导览AI数字人 — 环境自动部署
echo ============================================================
echo.

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

:: ==================== 1. 检查 Python ====================
echo [1/5] 检查 Python 环境...

set "PYTHON="
where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
    for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
        if %%a geq 3 if %%b geq 10 set "PYTHON=python"
    )
)

if "%PYTHON%"=="" (
    echo [错误] 未找到 Python 3.10+，请先安装 Python
    echo   下载: https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo   [OK] Python 就绪

:: ==================== 2. 检查 Node.js ====================
echo [2/5] 检查 Node.js 环境...

set "NODE="
where node >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=1 delims=v" %%i in ('node --version 2^>^&1') do set "NODE_VER=%%i"
    for /f "tokens=1 delims=." %%a in ("!NODE_VER!") do (
        if %%a geq 18 set "NODE=node"
    )
)

if "%NODE%"=="" (
    echo [错误] 未找到 Node.js 18+，请先安装 Node.js
    echo   下载: https://nodejs.org/
    pause
    exit /b 1
)
node --version

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 npm，请重新安装 Node.js
    pause
    exit /b 1
)
echo   [OK] Node.js + npm 就绪

:: ==================== 3. Python 虚拟环境 ====================
echo [3/5] 创建 Python 虚拟环境 ^& 安装依赖...

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
    echo   [OK] 虚拟环境创建完成: venv\
) else (
    echo   [OK] 虚拟环境已存在，跳过创建
)

echo   正在安装 Python 依赖 (可能需要几分钟，请耐心等待)...
venv\Scripts\python.exe -m pip install --upgrade pip -q 2>nul
venv\Scripts\pip.exe install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装可能失败，请检查网络连接
    echo   可手动执行: venv\Scripts\pip.exe install -r requirements.txt
)
echo   [OK] Python 依赖安装完成

:: ==================== 4. 环境变量配置 ====================
echo [4/5] 配置环境变量...

if not exist ".env" (
    copy .env.example .env >nul
    echo   [WARN] 已从 .env.example 创建 .env
    echo          请编辑 .env 填入你的 API Key:
    echo            - DEEPSEEK_API_KEY  (DeepSeek 大模型)
    echo            - DASHSCOPE_API_KEY (通义千问多模态)
    echo            - AMAP_API_KEY      (高德地图 MCP)
) else (
    echo   [OK] .env 已存在，跳过
)

if not exist "backend\.env" (
    copy .env backend\.env >nul 2>nul
    echo   [OK] backend\.env 就绪
)

:: ==================== 5. 前端依赖 ====================
echo [5/5] 安装前端依赖...

call :install_frontend "frontend\visitor" "游客端 (visitor)"
call :install_frontend "frontend\admin" "管理后台 (admin)"

:: ==================== 完成 ====================
echo.
echo ============================================================
echo   部署完成！
echo ============================================================
echo.
echo   下一步:
echo   1. 编辑 .env 填入 API Key (如尚未配置)
echo   2. 启动所有服务: 双击 start.bat
echo.
echo   手动启动方式:
echo   后端:   cd backend ^&^& ..\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo   游客端: cd frontend\visitor ^&^& npm run dev
echo   管理端: cd frontend\admin ^&^& npm run dev
echo.
pause
exit /b 0

:: ==================== 子过程: 安装前端依赖 ====================
:install_frontend
set "dir=%~1"
set "name=%~2"
if exist "%dir%\package.json" (
    echo   正在安装 %name% 依赖...
    cd /d "%PROJECT_ROOT%%dir%"
    call npm install --silent 2>nul
    cd /d "%PROJECT_ROOT%"
    echo   [OK] %name% 依赖安装完成
) else (
    echo   [WARN] %dir%\package.json 不存在，跳过 %name%
)
exit /b
