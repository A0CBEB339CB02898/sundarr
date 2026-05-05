import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import uvicorn

RUNTIME_DIR = Path(".sundarr")
PID_FILE = RUNTIME_DIR / "sundarr-api.pid"
LOG_FILE = RUNTIME_DIR / "sundarr-api.log"


def main() -> None:
    parser = argparse.ArgumentParser(description="管理 Sundarr 本地开发服务。")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="前台运行 API，适合查看实时日志。")
    _add_server_options(run_parser, default_reload=True)

    start_parser = subparsers.add_parser("start", help="后台启动 API。")
    _add_server_options(start_parser, default_reload=False)

    subparsers.add_parser("stop", help="停止后台 API。")

    restart_parser = subparsers.add_parser("restart", help="重启后台 API。")
    _add_server_options(restart_parser, default_reload=False)

    subparsers.add_parser("status", help="查看后台 API 状态。")

    args = parser.parse_args()

    command = args.command or "run"
    if command == "run":
        _run_foreground(args.host, args.port, args.reload)
    elif command == "start":
        _start_background(args.host, args.port, args.reload)
    elif command == "stop":
        _stop_background()
    elif command == "restart":
        _stop_background(quiet=True)
        _start_background(args.host, args.port, args.reload)
    elif command == "status":
        _print_status()


def _add_server_options(parser: argparse.ArgumentParser, default_reload: bool) -> None:
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0。")
    parser.add_argument("--port", type=int, default=8080, help="监听端口，默认 8080。")
    parser.add_argument("--reload", action="store_true", default=default_reload, help="开启开发热重载。")
    parser.add_argument("--no-reload", action="store_false", dest="reload", help="关闭开发热重载。")


def _run_foreground(host: str, port: int, reload: bool) -> None:
    uvicorn.run(
        "sundarr.app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def _start_background(host: str, port: int, reload: bool) -> None:
    if _read_pid() and _is_process_running(_read_pid() or 0):
        print("Sundarr API 已在运行。")
        return

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "sundarr.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        command.append("--reload")

    log_file = LOG_FILE.open("ab")
    kwargs = {
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    log_file.close()
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    time.sleep(0.5)
    print(f"Sundarr API 已后台启动，PID={process.pid}。")
    print(f"日志文件：{LOG_FILE}")


def _stop_background(quiet: bool = False) -> None:
    pid = _read_pid()
    if not pid:
        if not quiet:
            print("Sundarr API 未运行。")
        return

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    PID_FILE.unlink(missing_ok=True)
    if not quiet:
        print("Sundarr API 已停止。")


def _print_status() -> None:
    pid = _read_pid()
    if pid and _is_process_running(pid):
        print(f"Sundarr API 正在运行，PID={pid}。")
        print(f"日志文件：{LOG_FILE}")
        return
    print("Sundarr API 未运行。")


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return None


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    main()
