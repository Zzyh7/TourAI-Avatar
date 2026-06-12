@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  景区导览AI数字人 — 一键启动所有服务 (Windows)
::  双击 start.bat 启动，所有服务日志在同一个窗口显示
::  按 Ctrl+C 停止所有服务
:: ============================================================

cd /d "%~dp0"

:: 找到一个能用的 Python（优先 venv）
set "PYTHON="
if exist "venv\Scripts\python.exe" set "PYTHON=venv\Scripts\python.exe"
if "%PYTHON%"=="" for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON=%%i"
if "%PYTHON%"=="" (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo ============================================================
echo   TourAI - 一键启动所有服务
echo   Python: %PYTHON%
echo ============================================================
echo.

"%PYTHON%" start.py
pause
