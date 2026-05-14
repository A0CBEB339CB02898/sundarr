import sys

from sundarr.app import logging_config
from sundarr.app.logging_config import LOG_FILE_ENV, LOG_MAX_BYTES_ENV, LOG_TO_FILE_ENV, RotatingTextStream


def test_rotating_text_stream_truncates_before_limit_is_exceeded(tmp_path) -> None:
    log_file = tmp_path / "service.log"
    stream = RotatingTextStream(log_file, max_bytes=5)

    stream.write("1234")
    stream.write("567")
    stream.flush()

    assert log_file.read_text(encoding="utf-8") == "567"


def test_configure_file_logging_from_env_replaces_stdout(tmp_path, monkeypatch) -> None:
    log_file = tmp_path / "service.log"
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    monkeypatch.setenv(LOG_TO_FILE_ENV, "true")
    monkeypatch.setenv(LOG_FILE_ENV, str(log_file))
    monkeypatch.setenv(LOG_MAX_BYTES_ENV, "10")

    try:
        logging_config.configure_file_logging_from_env()
        print("hello")
        sys.stdout.flush()
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    assert "hello" in log_file.read_text(encoding="utf-8")
