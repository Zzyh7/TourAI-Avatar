@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  景区导览AI数字人 — 一键启动所有服务 (Windows)
::  双击 start.bat 启动，关闭各窗口停止服务
:: ============================================================

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

:: 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)

:: 检查 .env
if not exist ".env" (
    echo [错误] 未找到 .env 文件，请先配置 API Key
    echo   从 .env.example 复制并填入你的 Key
    pause
    exit /b 1
)

:: 确保 data 目录存在
if not exist "backend\data" mkdir backend\data

echo ============================================================
echo   景区导览AI数字人 — 启动所有服务
echo ============================================================
echo.
echo   将在 3 个独立窗口中启动:
echo     - 后端 API      :8000
echo     - 游客端        :5173
echo     - 管理后台      :5174
echo.
echo   关闭各窗口即可停止对应服务
echo ============================================================

:: ==================== 1. 后端 (FastAPI :8000) ====================
start "TourAI-后端-API:8000" cmd /c ^
    "cd /d "%PROJECT_ROOT%backend" && ^
    echo ============================================================ && ^
    echo   TourAI 后端 API (FastAPI) — http://localhost:8000 && ^
    echo   API 文档: http://localhost:8000/docs && ^
    echo ============================================================ && ^
    ..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 && ^
    pause"

:: ==================== 2. 游客端 (Vite :5173) ====================
start "TourAI-游客端:5173" cmd /c ^
    "cd /d "%PROJECT_ROOT%frontend\visitor" && ^
    echo ============================================================ && ^
    echo   TourAI 游客端 (Vite) — http://localhost:5173 && ^
    echo ============================================================ && ^
    npm run dev -- --host 0.0.0.0 && ^
    pause"

:: ==================== 3. 管理后台 (Vite :5174) ====================
start "TourAI-管理后台:5174" cmd /c ^
    "cd /d "%PROJECT_ROOT%frontend\admin" && ^
    echo ============================================================ && ^
    echo   TourAI 管理后台 (Vite) — http://localhost:5174 && ^
    echo ============================================================ && ^
    npm run dev -- --host 0.0.0.0 && ^
    pause"

echo.
echo   所有服务已启动！请在弹出的窗口中查看运行日志。
echo.
echo   后端 API:   http://localhost:8000
echo   API 文档:   http://localhost:8000/docs
echo   游客端:     http://localhost:5173
echo   管理后台:   http://localhost:5174
echo.
pause
