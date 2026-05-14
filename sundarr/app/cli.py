import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sundarr.app.config import PROJECT_ROOT
from sundarr.app.db_admin import initialize_database
from sundarr.app.log_runner import DEFAULT_LOG_MAX_BYTES

RUNTIME_DIR = PROJECT_ROOT / ".sundarr"
WEB_DIR = PROJECT_ROOT / "web"

DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8080
DEFAULT_WEB_HOST = "0.0.0.0"
DEFAULT_WEB_PORT = 5173
LOG_MAX_BYTES_ENV = "SUNDARR_LOG_MAX_BYTES"


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
WORKER_SERVICE = ManagedService(
    name="worker",
    display_name="Sundarr Worker",
    pid_file=RUNTIME_DIR / "sundarr-worker.pid",
    log_file=RUNTIME_DIR / "sundarr-worker.log",
)
MANAGED_SERVICES = (API_SERVICE, WEB_SERVICE, WORKER_SERVICE)


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

    try:
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
    except RuntimeError as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


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
    _prepare_process(WORKER_SERVICE, quiet=False)

    api_process = subprocess.Popen(_api_command(api_host, api_port, reload))
    web_process = subprocess.Popen(_web_command(web_host, web_port), cwd=WEB_DIR)
    worker_process = subprocess.Popen(_worker_command())
    print("Sundarr 完整项目已前台启动，按 Ctrl+C 停止。")
    try:
        while True:
            api_code = api_process.poll()
            web_code = web_process.poll()
            worker_code = worker_process.poll()
            if api_code is not None:
                raise RuntimeError(f"Sundarr API 已退出，退出码={api_code}。")
            if web_code is not None:
                raise RuntimeError(f"Sundarr Web 已退出，退出码={web_code}。")
            if worker_code is not None:
                raise RuntimeError(f"Sundarr Worker 已退出，退出码={worker_code}。")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("正在停止 Sundarr 完整项目。")
    finally:
        _terminate_process(api_process)
        _terminate_process(web_process)
        _terminate_process(worker_process)


def _start_background(api_host: str, api_port: int, web_host: str, web_port: int, reload: bool) -> None:
    _setup_project()
    _prepare_port(API_SERVICE, api_host, api_port, quiet=True)
    _prepare_port(WEB_SERVICE, web_host, web_port, quiet=True)
    _prepare_process(WORKER_SERVICE, quiet=True)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _start_service(API_SERVICE, _api_command(api_host, api_port, reload), cwd=None)
    _start_service(WEB_SERVICE, _web_command(web_host, web_port), cwd=WEB_DIR)
    _start_service(WORKER_SERVICE, _worker_command(), cwd=None)
    print("Sundarr 完整项目已后台启动。")


def _setup_project() -> None:
    print("正在检查数据库并执行必要初始化。")
    print(f"项目目录：{PROJECT_ROOT}")
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
    wrapped_command = [
        sys.executable,
        "-m",
        "sundarr.app.log_runner",
        "--log-file",
        str(service.log_file),
        "--max-bytes",
        str(_log_max_bytes()),
        "--command-json",
        json.dumps(command),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = _prepend_pythonpath(PROJECT_ROOT, env.get("PYTHONPATH"))
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "cwd": cwd,
        "env": env,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(wrapped_command, **kwargs)
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
    _prepare_process(service, quiet=quiet)

    if _is_port_in_use(host, port):
        occupant_pid = _find_port_pid(host, port)
        if occupant_pid is not None and _is_sundarr_process(occupant_pid):
            if not quiet:
                print(f"端口 {port} 被 Sundarr 旧进程 PID={occupant_pid} 占用，准备清理。")
            _kill_process(occupant_pid)
            time.sleep(0.3)
            if _is_port_in_use(host, port):
                raise RuntimeError(f"{service.display_name} 端口 {port} 清理后仍被占用，请手动释放后重试。")
            return
        raise RuntimeError(f"{service.display_name} 端口 {port} 已被其他程序占用，请释放端口后重试。")


def _prepare_process(service: ManagedService, quiet: bool) -> None:
    pid = _read_pid(service)
    if pid and _is_process_running(pid):
        if not quiet:
            print(f"{service.display_name} 旧进程仍在运行，准备清理 PID={pid}。")
        _stop_service(service, quiet=True)
        time.sleep(0.2)
    elif pid:
        service.pid_file.unlink(missing_ok=True)


def _is_port_in_use(host: str, port: int) -> bool:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((check_host, port)) == 0


def _find_port_pid(host: str, port: int) -> int | None:
    """查找占用指定端口的进程 PID，找不到则返回 None。"""
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    if os.name == "nt":
        return _find_port_pid_windows(check_host, port)
    return _find_port_pid_posix(check_host, port)


def _find_port_pid_windows(host: str, port: int) -> int | None:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    target = f"{host}:{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        if parts[0] != "TCP":
            continue
        local_addr = parts[1]
        state = parts[3]
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if local_addr.endswith(f":{port}") and state == "LISTENING":
            return pid
    return None


def _find_port_pid_posix(host: str, port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    pid_str = result.stdout.strip()
    if pid_str.isdigit():
        return int(pid_str)
    return None


def _is_sundarr_process(pid: int) -> bool:
    """判断指定 PID 是否为 Sundarr 管理的进程。"""
    for service in MANAGED_SERVICES:
        service_pid = _read_pid(service)
        if service_pid == pid:
            return True
    current_pid: int | None = pid
    seen: set[int] = set()
    for _ in range(8):
        if current_pid is None or current_pid in seen:
            return False
        seen.add(current_pid)
        command_line = _process_command_line(current_pid)
        if _looks_like_sundarr_command(command_line):
            return True
        current_pid = _parent_pid(current_pid)
    return False


def _process_command_line(pid: int) -> str:
    if os.name != "nt":
        return ""
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    for line in result.stdout.splitlines():
        if line.startswith("CommandLine="):
            return line.removeprefix("CommandLine=").strip()
    return ""


def _parent_pid(pid: int) -> int | None:
    if os.name != "nt":
        return None
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "ParentProcessId", "/format:list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    for line in result.stdout.splitlines():
        if not line.startswith("ParentProcessId="):
            continue
        value = line.removeprefix("ParentProcessId=").strip()
        if value.isdigit():
            return int(value)
    return None


def _looks_like_sundarr_command(command_line: str) -> bool:
    normalized = command_line.replace("\\", "/")
    project_runtime = str(RUNTIME_DIR).replace("\\", "/")
    web_dir = str(WEB_DIR).replace("\\", "/")
    return "sundarr.app.main:app" in normalized or (
        "sundarr.app.log_runner" in normalized and project_runtime in normalized
    ) or (
        "vite" in normalized and web_dir in normalized
    )


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


def _worker_command() -> list[str]:
    return [sys.executable, "-m", "sundarr.app.worker"]


def _log_max_bytes() -> int:
    raw_value = os.environ.get(LOG_MAX_BYTES_ENV)
    if raw_value is None or raw_value.strip() == "":
        return DEFAULT_LOG_MAX_BYTES
    try:
        value = int(raw_value)
    except ValueError:
        raise RuntimeError(f"{LOG_MAX_BYTES_ENV} 必须是整数。") from None
    if value <= 0:
        raise RuntimeError(f"{LOG_MAX_BYTES_ENV} 必须大于 0。")
    return value


def _prepend_pythonpath(path: Path, current: str | None) -> str:
    path_text = str(path)
    if not current:
        return path_text
    return f"{path_text}{os.pathsep}{current}"


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
