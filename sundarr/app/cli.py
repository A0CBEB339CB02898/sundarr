import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sundarr.app.db_admin import initialize_database

RUNTIME_DIR = Path(".sundarr")
WEB_DIR = Path("web")

DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8080
DEFAULT_WEB_HOST = "0.0.0.0"
DEFAULT_WEB_PORT = 5173


@dataclass(frozen=True)
class ManagedService:
    name: str
    display_name: str
    pid_file: Path
    log_file: Path
    port: int | None = None


API_SERVICE = ManagedService(
    name="api",
    display_name="Sundarr API",
    pid_file=RUNTIME_DIR / "sundarr-api.pid",
    log_file=RUNTIME_DIR / "sundarr-api.log",
)
WEB_SERVICE = ManagedService(
    name="web",
    display_name="Sundarr Web",
    pid_file=RUNTIME_DIR / "sundarr-web.pid",
    log_file=RUNTIME_DIR / "sundarr-web.log",
)
MANAGED_SERVICES = (API_SERVICE, WEB_SERVICE)


def main() -> None:
    parser = argparse.ArgumentParser(description="管理 Sundarr 本地完整项目。")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="前台运行完整项目，适合查看实时日志。")
    _add_project_options(run_parser, default_reload=True)

    start_parser = subparsers.add_parser("start", help="后台启动完整项目。")
    _add_project_options(start_parser, default_reload=False)

    subparsers.add_parser("stop", help="停止后台完整项目。")

    restart_parser = subparsers.add_parser("restart", help="重启后台完整项目。")
    _add_project_options(restart_parser, default_reload=False)

    subparsers.add_parser("status", help="查看后台完整项目状态。")

    args = parser.parse_args()

    command = args.command or "run"
    if command == "run":
        _run_foreground(args.api_host, args.api_port, args.web_host, args.web_port, args.reload)
    elif command == "start":
        _start_background(args.api_host, args.api_port, args.web_host, args.web_port, args.reload)
    elif command == "stop":
        _stop_background()
    elif command == "restart":
        _stop_background(quiet=True)
        _start_background(args.api_host, args.api_port, args.web_host, args.web_port, args.reload)
    elif command == "status":
        _print_status()


def _add_project_options(parser: argparse.ArgumentParser, default_reload: bool) -> None:
    parser.add_argument("--api-host", "--host", default=DEFAULT_API_HOST, help="API 监听地址，默认 0.0.0.0。")
    parser.add_argument("--api-port", "--port", type=int, default=DEFAULT_API_PORT, help="API 监听端口，默认 8080。")
    parser.add_argument("--web-host", default=DEFAULT_WEB_HOST, help="Web 监听地址，默认 0.0.0.0。")
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT, help="Web 监听端口，默认 5173。")
    parser.add_argument("--reload", action="store_true", default=default_reload, help="开启 API 开发热重载。")
    parser.add_argument("--no-reload", action="store_false", dest="reload", help="关闭 API 开发热重载。")


def _run_foreground(api_host: str, api_port: int, web_host: str, web_port: int, reload: bool) -> None:
    _setup_project()
    _prepare_port(API_SERVICE, api_host, api_port, quiet=False)
    _prepare_port(WEB_SERVICE, web_host, web_port, quiet=False)

    api_process = subprocess.Popen(_api_command(api_host, api_port, reload))
    web_process = subprocess.Popen(_web_command(web_host, web_port), cwd=WEB_DIR)
    print("Sundarr 完整项目已前台启动，按 Ctrl+C 停止。")
    try:
        while True:
            api_code = api_process.poll()
            web_code = web_process.poll()
            if api_code is not None:
                raise RuntimeError(f"Sundarr API 已退出，退出码={api_code}。")
            if web_code is not None:
                raise RuntimeError(f"Sundarr Web 已退出，退出码={web_code}。")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("正在停止 Sundarr 完整项目。")
    finally:
        _terminate_process(api_process)
        _terminate_process(web_process)


def _start_background(api_host: str, api_port: int, web_host: str, web_port: int, reload: bool) -> None:
    _setup_project()
    _prepare_port(API_SERVICE, api_host, api_port, quiet=True)
    _prepare_port(WEB_SERVICE, web_host, web_port, quiet=True)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _start_service(API_SERVICE, _api_command(api_host, api_port, reload), cwd=None)
    _start_service(WEB_SERVICE, _web_command(web_host, web_port), cwd=WEB_DIR)
    print("Sundarr 完整项目已后台启动。")


def _setup_project() -> None:
    print("正在检查数据库并执行必要初始化。")
    initialize_database()
    _ensure_web_dependencies()


def _ensure_web_dependencies() -> None:
    package_json = WEB_DIR / "package.json"
    if not package_json.exists():
        raise FileNotFoundError("找不到 web/package.json，请在项目根目录执行命令。")
    if (WEB_DIR / "node_modules").exists():
        return
    print("Web 前端依赖未安装，正在执行 npm install。")
    result = subprocess.run([_npm_executable(), "install"], cwd=WEB_DIR)
    if result.returncode != 0:
        raise RuntimeError("Web 前端依赖安装失败，请检查 npm 输出后重试。")


def _start_service(service: ManagedService, command: list[str], cwd: Path | None) -> None:
    log_file = service.log_file.open("ab")
    kwargs = {
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "cwd": cwd,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    log_file.close()
    service.pid_file.write_text(str(process.pid), encoding="utf-8")
    time.sleep(0.5)
    print(f"{service.display_name} 已后台启动，PID={process.pid}。")
    print(f"日志文件：{service.log_file}")


def _stop_background(quiet: bool = False) -> None:
    stopped = False
    for service in reversed(MANAGED_SERVICES):
        if _stop_service(service, quiet=True):
            stopped = True
    if quiet:
        return
    print("Sundarr 完整项目已停止。" if stopped else "Sundarr 完整项目未运行。")


def _stop_service(service: ManagedService, quiet: bool = False) -> bool:
    pid = _read_pid(service)
    if not pid:
        return False
    if _is_process_running(pid):
        _kill_process(pid)
    service.pid_file.unlink(missing_ok=True)
    if not quiet:
        print(f"{service.display_name} 已停止。")
    return True


def _print_status() -> None:
    for service in MANAGED_SERVICES:
        pid = _read_pid(service)
        if pid and _is_process_running(pid):
            print(f"{service.display_name} 正在运行，PID={pid}。")
            print(f"日志文件：{service.log_file}")
        else:
            print(f"{service.display_name} 未运行。")


def _prepare_port(service: ManagedService, host: str, port: int, quiet: bool) -> None:
    pid = _read_pid(service)
    if pid and _is_process_running(pid):
        if not quiet:
            print(f"{service.display_name} 旧进程仍在运行，准备清理 PID={pid}。")
        _stop_service(service, quiet=True)
        time.sleep(0.2)
    elif pid:
        service.pid_file.unlink(missing_ok=True)

    if _is_port_in_use(host, port):
        raise RuntimeError(f"{service.display_name} 端口 {port} 已被其他程序占用，请释放端口后重试。")


def _is_port_in_use(host: str, port: int) -> bool:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((check_host, port)) == 0


def _api_command(host: str, port: int, reload: bool) -> list[str]:
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
    return command


def _web_command(host: str, port: int) -> list[str]:
    return [_npm_executable(), "run", "dev", "--", "--host", host, "--port", str(port)]


def _npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _read_pid(service: ManagedService) -> int | None:
    if not service.pid_file.exists():
        return None
    try:
        return int(service.pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        service.pid_file.unlink(missing_ok=True)
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


def _kill_process(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        process.terminate()


if __name__ == "__main__":
    main()
