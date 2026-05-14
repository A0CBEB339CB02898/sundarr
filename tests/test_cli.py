import subprocess
import sys
from pathlib import Path

import pytest

from sundarr.app import cli
from sundarr.app.config import find_project_root


def test_db_init_command_is_not_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["sundarr", "db", "init"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2


def test_ensure_web_dependencies_runs_npm_install_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    (web_dir / "package.json").write_text("{}", encoding="utf-8")
    calls: list[tuple[list[str], Path | None]] = []

    def fake_run(command, cwd=None, **kwargs):
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli, "WEB_DIR", web_dir)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    cli._ensure_web_dependencies()

    assert calls == [([cli._npm_executable(), "install"], web_dir)]


def test_find_project_root_works_from_venv_scripts(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    scripts_dir = project_root / ".venv" / "Scripts"
    web_dir = project_root / "web"
    scripts_dir.mkdir(parents=True)
    web_dir.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (project_root / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (web_dir / "package.json").write_text("{}", encoding="utf-8")

    assert find_project_root(scripts_dir) == project_root


def test_main_prints_friendly_runtime_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["sundarr", "start"])
    monkeypatch.setattr(cli, "_start_background", lambda *args: (_ for _ in ()).throw(RuntimeError("数据库连接失败")))

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 1
    assert "启动失败：数据库连接失败" in capsys.readouterr().err


def test_prepare_port_cleans_project_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    service.pid_file.write_text("123", encoding="utf-8")
    killed: list[int] = []

    monkeypatch.setattr(cli, "_is_process_running", lambda pid: pid == 123)
    monkeypatch.setattr(cli, "_is_sundarr_process", lambda pid: True)
    monkeypatch.setattr(cli, "_kill_process", lambda pid: killed.append(pid) or True)
    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: False)

    cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)

    assert killed == [123]
    assert service.pid_file.exists()


def test_prepare_port_waits_after_pid_file_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    service.pid_file.write_text("123", encoding="utf-8")
    killed: list[int] = []

    monkeypatch.setattr(cli, "_is_process_running", lambda pid: pid == 123)
    monkeypatch.setattr(cli, "_is_sundarr_process", lambda pid: True)
    monkeypatch.setattr(cli, "_kill_process", lambda pid: killed.append(pid) or True)
    monkeypatch.setattr(cli, "_wait_port_released", lambda host, port, timeout_seconds=3.0: True)
    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: (_ for _ in ()).throw(AssertionError("不应继续检查端口")))

    cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)

    assert killed == [123]


def test_stop_service_keeps_pid_file_when_cleanup_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    service.pid_file.write_text("123", encoding="utf-8")

    monkeypatch.setattr(cli, "_is_process_running", lambda pid: pid == 123)
    monkeypatch.setattr(cli, "_kill_process", lambda pid: False)

    with pytest.raises(RuntimeError, match="清理失败"):
        cli._stop_service(service, quiet=True)

    assert service.pid_file.exists()


def test_stop_service_keeps_pid_file_when_cleanup_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    service.pid_file.write_text("123", encoding="utf-8")

    monkeypatch.setattr(cli, "_is_process_running", lambda pid: pid == 123)
    monkeypatch.setattr(cli, "_kill_process", lambda pid: True)

    assert cli._stop_service(service, quiet=True) is True
    assert service.pid_file.exists()


def test_prepare_port_rejects_pid_file_reused_by_external_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    service.pid_file.write_text("123", encoding="utf-8")

    monkeypatch.setattr(cli, "_is_process_running", lambda pid: pid == 123)
    monkeypatch.setattr(cli, "_sundarr_process_tree_root", lambda pid: None)

    with pytest.raises(RuntimeError, match="PID 文件指向非 Sundarr 进程"):
        cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)


def test_taskkill_process_tree_retries_until_process_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    states = iter([True, True, False])
    calls: list[list[str]] = []

    monkeypatch.setattr(cli.time, "monotonic", iter([0.0, 0.1, 0.2, 0.3]).__next__)
    monkeypatch.setattr(cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(cli, "_is_process_running", lambda _pid: next(states))
    monkeypatch.setattr(cli.subprocess, "run", lambda command, **_kwargs: calls.append(command))

    assert cli._taskkill_process_tree(123) is True
    assert calls == [["taskkill", "/PID", "123", "/T", "/F"], ["taskkill", "/PID", "123", "/T", "/F"]]


def test_prepare_port_rejects_external_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(cli, "_find_port_pid", lambda host, port: None)

    with pytest.raises(RuntimeError, match="端口 8080 已被其他程序占用"):
        cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)


def test_prepare_port_cleans_sundarr_port_process_without_pid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    killed: list[int] = []
    port_checks = iter([True, False])

    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: next(port_checks))
    monkeypatch.setattr(cli, "_find_sundarr_port_cleanup_pid", lambda host, port: (456, 456))
    monkeypatch.setattr(cli, "_kill_process", lambda pid: killed.append(pid) or True)
    monkeypatch.setattr(cli, "_wait_port_released", lambda host, port: True)

    cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)

    assert killed == [456]


def test_prepare_port_cleans_sundarr_process_tree_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    killed: list[int] = []

    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(cli, "_find_sundarr_port_cleanup_pid", lambda host, port: (456, 100))
    monkeypatch.setattr(cli, "_kill_process", lambda pid: killed.append(pid) or True)
    monkeypatch.setattr(cli, "_wait_port_released", lambda host, port: True)

    cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)

    assert killed == [100]


def test_prepare_port_reports_when_cleanup_does_not_release_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )

    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: True)
    monkeypatch.setattr(cli, "_find_sundarr_port_cleanup_pid", lambda host, port: (456, 100))
    monkeypatch.setattr(cli, "_kill_process", lambda pid: True)
    monkeypatch.setattr(cli, "_wait_port_released", lambda host, port: False)

    with pytest.raises(RuntimeError, match="清理后仍被占用"):
        cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)


def test_is_sundarr_process_detects_api_command_without_pid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "MANAGED_SERVICES", ())
    monkeypatch.setattr(cli, "_process_command_line", lambda pid: f"{cli.PROJECT_ROOT} python -m sundarr.app.run_api --port 8080")
    monkeypatch.setattr(cli, "_parent_pid", lambda pid: None)

    assert cli._is_sundarr_process(456) is True


def test_is_sundarr_process_detects_worker_command(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = str(cli.RUNTIME_DIR)

    monkeypatch.setattr(cli, "MANAGED_SERVICES", ())
    monkeypatch.setattr(cli, "_process_command_line", lambda pid: f"{runtime} python -m sundarr.app.worker")
    monkeypatch.setattr(cli, "_parent_pid", lambda pid: 123 if pid == 456 else None)

    assert cli._is_sundarr_process(456) is True


def test_is_sundarr_process_detects_deep_web_log_runner_ancestor(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = {
        456: "node vite.js --host 0.0.0.0 --port 5173",
        300: "cmd.exe /d /s /c vite --host 0.0.0.0 --port 5173",
        200: "node npm-cli.js run dev -- --host 0.0.0.0 --port 5173",
        100: f"node {cli.WEB_DIR / 'node_modules' / 'vite' / 'bin' / 'vite.js'} --host 0.0.0.0 --port 5173",
    }
    parents = {456: 300, 300: 200, 200: 100, 100: None}

    monkeypatch.setattr(cli, "MANAGED_SERVICES", ())
    monkeypatch.setattr(cli, "_process_command_line", lambda pid: commands.get(pid, ""))
    monkeypatch.setattr(cli, "_parent_pid", lambda pid: parents.get(pid))

    assert cli._is_sundarr_process(456) is True


def test_is_sundarr_process_detects_project_vite_command(monkeypatch: pytest.MonkeyPatch) -> None:
    command = f"node {cli.WEB_DIR / 'node_modules' / '.bin' / '..' / 'vite' / 'bin' / 'vite.js'} --port 5173"

    monkeypatch.setattr(cli, "MANAGED_SERVICES", ())
    monkeypatch.setattr(cli, "_process_command_line", lambda pid: command)
    monkeypatch.setattr(cli, "_parent_pid", lambda pid: None)

    assert cli._is_sundarr_process(456) is True


def test_sundarr_process_tree_root_prefers_highest_sundarr_ancestor(monkeypatch: pytest.MonkeyPatch) -> None:
    commands = {
        456: "python -m sundarr.app.run_api --port 8080",
        300: "python -m sundarr.app.run_api --port 8080",
        200: f"python -m sundarr.app.worker {cli.RUNTIME_DIR}",
        100: "powershell.exe",
    }
    parents = {456: 300, 300: 200, 200: 100, 100: None}

    monkeypatch.setattr(cli, "MANAGED_SERVICES", ())
    monkeypatch.setattr(cli, "_process_command_line", lambda pid: commands.get(pid, ""))
    monkeypatch.setattr(cli, "_parent_pid", lambda pid: parents.get(pid))

    assert cli._sundarr_process_tree_root(456) == 200


def test_worker_is_managed_service() -> None:
    assert cli.WORKER_SERVICE in cli.MANAGED_SERVICES
    assert cli.WORKER_SERVICE.pid_file.name == "sundarr-worker.pid"
    assert cli.WORKER_SERVICE.log_file.name == "sundarr-worker.log"


def test_worker_command_uses_module_entry() -> None:
    assert cli._worker_command() == [sys.executable, "-m", "sundarr.app.worker"]


def test_api_command_uses_module_entry() -> None:
    assert cli._api_command("127.0.0.1", 8080, False) == [sys.executable, "-m", "sundarr.app.run_api", "--host", "127.0.0.1", "--port", "8080"]


def test_log_max_bytes_defaults_to_100mb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(cli.LOG_MAX_BYTES_ENV, raising=False)

    assert cli._log_max_bytes() == cli.DEFAULT_LOG_MAX_BYTES


def test_log_max_bytes_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cli.LOG_MAX_BYTES_ENV, "1024")

    assert cli._log_max_bytes() == 1024


def test_log_max_bytes_rejects_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cli.LOG_MAX_BYTES_ENV, "0")

    with pytest.raises(RuntimeError, match="SUNDARR_LOG_MAX_BYTES"):
        cli._log_max_bytes()
