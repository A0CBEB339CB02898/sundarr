import subprocess
import sys
from pathlib import Path

import pytest

from sundarr.app import cli


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
    monkeypatch.setattr(cli, "_kill_process", lambda pid: killed.append(pid))
    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: False)

    cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)

    assert killed == [123]
    assert not service.pid_file.exists()


def test_prepare_port_rejects_external_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = cli.ManagedService(
        name="api",
        display_name="Sundarr API",
        pid_file=tmp_path / "api.pid",
        log_file=tmp_path / "api.log",
    )
    monkeypatch.setattr(cli, "_is_port_in_use", lambda host, port: True)

    with pytest.raises(RuntimeError, match="端口 8080 已被其他程序占用"):
        cli._prepare_port(service, "127.0.0.1", 8080, quiet=True)


def test_worker_is_managed_service() -> None:
    assert cli.WORKER_SERVICE in cli.MANAGED_SERVICES
    assert cli.WORKER_SERVICE.pid_file.name == "sundarr-worker.pid"
    assert cli.WORKER_SERVICE.log_file.name == "sundarr-worker.log"


def test_worker_command_uses_module_entry() -> None:
    assert cli._worker_command() == [sys.executable, "-m", "sundarr.app.worker"]
