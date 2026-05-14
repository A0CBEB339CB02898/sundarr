from sundarr.app.log_runner import _ensure_log_within_limit, _write_limited_chunk
from sundarr.app import log_runner


def test_ensure_log_within_limit_truncates_oversized_file(tmp_path) -> None:
    log_file = tmp_path / "service.log"
    log_file.write_bytes(b"123456")

    _ensure_log_within_limit(log_file, max_bytes=5)

    assert log_file.read_bytes() == b""


def test_write_limited_chunk_truncates_before_limit_is_exceeded(tmp_path) -> None:
    log_file = tmp_path / "service.log"
    with log_file.open("ab") as handle:
        _write_limited_chunk(handle, log_file, b"1234", max_bytes=5)
        _write_limited_chunk(handle, log_file, b"567", max_bytes=5)

    assert log_file.read_bytes() == b"567"


def test_main_accepts_command_json(tmp_path, monkeypatch) -> None:
    calls: list[tuple[list[str], object, int]] = []

    def fake_run(command, log_file, max_bytes):
        calls.append((command, log_file, max_bytes))
        return 0

    monkeypatch.setattr(log_runner.sys, "argv", [
        "log_runner",
        "--log-file",
        str(tmp_path / "service.log"),
        "--max-bytes",
        "1024",
        "--command-json",
        '["python", "-m", "demo"]',
    ])
    monkeypatch.setattr(log_runner, "run_with_limited_log", fake_run)

    try:
        log_runner.main()
    except SystemExit as exc:
        assert exc.code == 0

    assert calls == [(["python", "-m", "demo"], tmp_path / "service.log", 1024)]
