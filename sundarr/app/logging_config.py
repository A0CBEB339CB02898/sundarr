import os
import sys
from pathlib import Path


DEFAULT_LOG_MAX_BYTES = 100 * 1024 * 1024
LOG_TO_FILE_ENV = "SUNDARR_LOG_TO_FILE"
LOG_FILE_ENV = "SUNDARR_LOG_FILE"
LOG_MAX_BYTES_ENV = "SUNDARR_LOG_MAX_BYTES"


class RotatingTextStream:
    def __init__(self, path: Path, max_bytes: int) -> None:
        self.path = path
        self.max_bytes = max(1, max_bytes)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._rotate_if_needed(len(text.encode("utf-8", errors="replace")))
        return self._handle.write(text)

    def flush(self) -> None:
        self._handle.flush()

    def isatty(self) -> bool:
        return False

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        current_size = self._handle.tell()
        if current_size + incoming_bytes <= self.max_bytes:
            return
        self._handle.close()
        self.path.write_text("", encoding="utf-8")
        self._handle = self.path.open("a", encoding="utf-8", buffering=1)


def configure_file_logging_from_env() -> None:
    if os.environ.get(LOG_TO_FILE_ENV, "").lower() not in {"1", "true", "yes"}:
        return
    log_file = os.environ.get(LOG_FILE_ENV)
    if not log_file:
        return
    stream = RotatingTextStream(Path(log_file), _log_max_bytes_from_env())
    sys.stdout = stream
    sys.stderr = stream


def _log_max_bytes_from_env() -> int:
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
