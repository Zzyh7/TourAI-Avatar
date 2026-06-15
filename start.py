#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
  TourAI 景区导览AI数字人 — 一键启动所有服务
  使用: python start.py  (或双击 start.bat)
  按 Ctrl+C 同时停止所有服务
============================================================
"""

import subprocess
import sys
import os
import time
import signal
import platform
import threading
from pathlib import Path

# ---- 修复 Windows 终端编码问题 ----
if platform.system() == "Windows":
    try:
        sys.stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", errors="replace", buffering=1)  # type: ignore
    except Exception:
        pass
    try:
        sys.stderr = open(sys.stderr.fileno(), "w", encoding="utf-8", errors="replace", buffering=1)  # type: ignore
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

BOLD = "\033[1m"
NC   = "\033[0m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"

CHECK = "[OK]"
CROSS = "[FAIL]"

processes: dict[str, subprocess.Popen] = {}
shutdown_event = threading.Event()
_python_exe: str | None = None


# ============================================================
# 查找带依赖的 Python 解释器
# ============================================================
def find_python() -> str | None:
    """找到一个已安装 uvicorn + fastapi 的 Python 解释器"""
    global _python_exe
    if _python_exe:
        return _python_exe

    candidates: list[Path] = []

    # 1) 项目 venv (最高优先)
    for venv_py in [
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "bin" / "python",
        PROJECT_ROOT / "venv" / "bin" / "python3",
    ]:
        if venv_py.exists():
            candidates.append(venv_py)

    # 2) 当前运行的这个 Python
    candidates.append(Path(sys.executable))

    # 3) 同级目录下其他版本的 Python (Windows 常见)
    if platform.system() == "Windows":
        this_dir = Path(sys.executable).parent
        try:
            for sibling_dir in this_dir.parent.iterdir():
                if sibling_dir.is_dir():
                    py_exe = sibling_dir / "python.exe"
                    if py_exe.exists() and py_exe not in candidates:
                        candidates.append(py_exe)
        except Exception:
            pass

    # 去重
    seen = set()
    unique: list[Path] = []
    for c in candidates:
        resolved = str(c.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique.append(c)

    for py_path in unique:
        try:
            result = subprocess.run(
                [str(py_path), "-c", "import uvicorn, fastapi, dotenv"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                _python_exe = str(py_path)
                return _python_exe
        except Exception:
            continue

    return None


# ============================================================
# 构建服务命令列表
# ============================================================
def build_services(python_exe: str) -> list[dict]:
    is_win = platform.system() == "Windows"
    return [
        {
            "name": "Backend API",
            "color": CYAN,
            "cwd": PROJECT_ROOT / "backend",
            "cmd": [
                python_exe, "-m", "uvicorn", "main:app",
                "--host", "0.0.0.0", "--port", "8000", "--reload",
            ],
            "shell": False,
            "url": "http://localhost:8000",
            "extra_urls": ["http://localhost:8000/docs"],
        },
        {
            "name": "Visitor",
            "color": GREEN,
            "cwd": PROJECT_ROOT / "frontend" / "visitor",
            "cmd": "npm run dev -- --host 0.0.0.0" if is_win
                   else ["npm", "run", "dev", "--", "--host", "0.0.0.0"],
            "shell": is_win,
            "url": "http://localhost:5173",
        },
        {
            "name": "Admin",
            "color": YELLOW,
            "cwd": PROJECT_ROOT / "frontend" / "admin",
            "cmd": "npm run dev -- --host 0.0.0.0" if is_win
                   else ["npm", "run", "dev", "--", "--host", "0.0.0.0"],
            "shell": is_win,
            "url": "http://localhost:5174",
        },
    ]


# ============================================================
# 端口冲突处理
# ============================================================
SERVICE_PORTS = [8000, 5173, 5174]


def free_ports() -> int:
    """检查并释放被占用的端口。返回清理后的占用数。"""
    busy = 0
    for port in SERVICE_PORTS:
        pid = _find_listening_pid(port)
        if pid is None:
            continue
        busy += 1
        print(f"  {YELLOW}[WARN]{NC} Port {port} is in use by PID {pid}, killing...")
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
            else:
                os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if _find_listening_pid(port) is None:
                print(f"  {GREEN}[OK]{NC} Port {port} freed")
            else:
                print(f"  {RED}[FAIL]{NC} Port {port} still occupied")
        except Exception as e:
            print(f"  {RED}[FAIL]{NC} Could not kill PID {pid}: {e}")
    return busy


def _find_listening_pid(port: int) -> int | None:
    """返回监听指定端口的进程 PID，如没有则返回 None"""
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["cmd", "/c", f"netstat -ano | findstr :{port}"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "LISTENING" in line:
                    parts = line.strip().split()
                    return int(parts[-1])
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
    return None


# ============================================================
# 启动前检查
# ============================================================
def preflight(python_exe: str) -> bool:
    ok = True

    if not (PROJECT_ROOT / ".env").exists():
        print(f"{RED}[ERROR]{NC} .env not found, please configure API Keys")
        print(f"       Copy from .env.example and fill in your keys")
        ok = False

    try:
        subprocess.run(
            "npm --version" if platform.system() == "Windows" else ["npm", "--version"],
            shell=(platform.system() == "Windows"),
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  {YELLOW}[WARN]{NC} npm not found, frontend services will be skipped")

    for fe in ["visitor", "admin"]:
        nm = PROJECT_ROOT / "frontend" / fe / "node_modules"
        if not nm.exists():
            print(f"  {YELLOW}[WARN]{NC} frontend/{fe}/node_modules missing, {fe} service skipped")
            print(f"       (Backend + static web pages are still available)")

    (PROJECT_ROOT / "backend" / "data").mkdir(exist_ok=True)
    return ok


# ============================================================
# 日志输出
# ============================================================
def format_line(prefix: str, color: str, line: str) -> str:
    return f"{color}[{prefix}]{NC} {line}"


def reader_thread(name: str, color: str, proc: subprocess.Popen):
    def read_stream(stream):
        try:
            for raw_line in iter(stream.readline, b""):
                if shutdown_event.is_set():
                    break
                try:
                    line = raw_line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    line = str(raw_line)
                if line:
                    print(format_line(name, color, line), flush=True)
        except ValueError:
            pass
        except Exception as e:
            print(format_line(name, color, f"[thread error] {e}"), flush=True)

    t1 = threading.Thread(target=read_stream, args=(proc.stdout,), daemon=True)
    t2 = threading.Thread(target=read_stream, args=(proc.stderr,), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


# ============================================================
# 启动 / 停止
# ============================================================
def start_services(services: list[dict]) -> bool:
    all_ok = True
    for svc in services:
        name, color = svc["name"], svc["color"]
        try:
            proc = subprocess.Popen(
                svc["cmd"],
                cwd=str(svc["cwd"]),
                shell=svc.get("shell", False),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                ),
            )
            processes[name] = proc
            threading.Thread(
                target=reader_thread, args=(name, color, proc), daemon=True
            ).start()
            print(f"  {color}{CHECK}{NC} {name} started (PID: {proc.pid})")
        except Exception as e:
            print(f"  {RED}{CROSS}{NC} {name} failed: {e}")
            all_ok = False
    return all_ok


def stop_services():
    if shutdown_event.is_set():
        return
    shutdown_event.set()

    print(f"\n{BOLD}Stopping all services...{NC}")

    for name, proc in processes.items():
        try:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
            print(f"  {CHECK} {name} stopped")
        except Exception as e:
            print(f"  {CROSS} {name} stop error: {e}")

    processes.clear()
    print(f"{BOLD}All services stopped{NC}")


def signal_handler(sig, frame):
    print()
    stop_services()
    sys.exit(0)


# ============================================================
# 主入口
# ============================================================
def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print()
    print(f"{BOLD}============================================================{NC}")
    print(f"{BOLD}  TourAI - One-Click Start All Services{NC}")
    print(f"{BOLD}============================================================{NC}")
    print()

    # 1. 查找 Python
    python_exe = find_python()
    if not python_exe:
        print(f"{RED}============================================================{NC}")
        print(f"{RED}  ERROR: No usable Python environment found{NC}")
        print(f"{RED}============================================================{NC}")
        print(f"  Current Python: {sys.executable}")
        print(f"  Please install dependencies:")
        print(f"    pip install -r requirements.txt")
        print(f"  Or use project venv:")
        print(f"    python -m venv venv")
        print(f"    venv\\Scripts\\pip install -r requirements.txt")
        print(f"{RED}============================================================{NC}")
        sys.exit(1)

    print(f"  {GREEN}{CHECK}{NC} Python: {python_exe}")

    # 2. 启动前检查
    if not preflight(python_exe):
        print(f"\n{RED}Preflight check failed. Please fix the issues above.{NC}")
        sys.exit(1)

    # 2.5 清理端口冲突
    free_ports()

    services = build_services(python_exe)

    # 如果没有 npm / node_modules，跳过前端服务
    has_npm = False
    try:
        subprocess.run(
            "npm --version" if platform.system() == "Windows" else ["npm", "--version"],
            shell=(platform.system() == "Windows"), capture_output=True, check=True
        )
        has_npm = True
    except Exception:
        pass
    if not has_npm:
        services = [s for s in services if s["name"] == "Backend API"]
    else:
        for fe in ["visitor", "admin"]:
            nm = PROJECT_ROOT / "frontend" / fe / "node_modules"
            if not nm.exists():
                services = [s for s in services if s["name"].lower() != fe]

    # 3. 启动
    print(f"\n{BOLD}Starting services...{NC}")
    if not start_services(services):
        stop_services()
        print(f"\n{RED}Some services failed to start. Terminated.{NC}")
        sys.exit(1)

    time.sleep(2)

    # 4. 访问地址
    print()
    print(f"{BOLD}============================================================{NC}")
    print(f"{GREEN}{BOLD}  All services running - URLs:{NC}")
    print(f"{BOLD}============================================================{NC}")
    for svc in services:
        print(f"  {svc['color']}{svc['name']}:{NC}  {svc['url']}")
        for extra in svc.get("extra_urls", []):
            pad = " " * (len(svc["name"]) + 2)
            print(f"  {pad}{extra}")
    print()
    print(f"  Press {BOLD}Ctrl+C{NC} to stop all services")
    print(f"{BOLD}============================================================{NC}")
    print()

    # 5. 监控
    try:
        while True:
            time.sleep(1)
            for name, proc in list(processes.items()):
                if proc.poll() is not None:
                    print(f"\n{RED}[!] {name} exited (code={proc.returncode}){NC}")
                    print(f"{YELLOW}Stopping all services...{NC}")
                    stop_services()
                    sys.exit(1)
    except KeyboardInterrupt:
        pass

    stop_services()


if __name__ == "__main__":
    main()
