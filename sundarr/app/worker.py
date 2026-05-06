import signal
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from sundarr.app.core.database import get_session_factory
from sundarr.app.models import Setting


WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
DEFAULT_WORKER_ENABLED = True
DEFAULT_WORKER_CONCURRENCY = 2


@dataclass(frozen=True)
class WorkerSettings:
    enabled: bool = DEFAULT_WORKER_ENABLED
    concurrency: int = DEFAULT_WORKER_CONCURRENCY


class WorkerRuntime:
    def __init__(self, poll_interval_seconds: float = 5.0) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._running = True

    def stop(self, signum: int | None = None, frame: object | None = None) -> None:
        self._running = False

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        session_factory = get_session_factory()
        print("Sundarr Worker 已启动。", flush=True)
        while self._running:
            with session_factory() as session:
                settings = load_worker_settings(session)
            if not settings.enabled:
                print("Sundarr Worker 已禁用，保持空转。", flush=True)
            time.sleep(self.poll_interval_seconds)
        print("Sundarr Worker 已停止。", flush=True)


def load_worker_settings(session: Session) -> WorkerSettings:
    enabled = _read_bool_setting(session, WORKER_ENABLED_KEY, DEFAULT_WORKER_ENABLED, "enabled")
    concurrency = _read_int_setting(session, WORKER_CONCURRENCY_KEY, DEFAULT_WORKER_CONCURRENCY, "value")
    return WorkerSettings(enabled=enabled, concurrency=max(1, concurrency))


def _read_bool_setting(session: Session, key: str, default: bool, field: str) -> bool:
    setting = session.get(Setting, key)
    if setting is None:
        return default
    value = setting.value_json.get(field)
    return value if isinstance(value, bool) else default


def _read_int_setting(session: Session, key: str, default: int, field: str) -> int:
    setting = session.get(Setting, key)
    if setting is None:
        return default
    value = setting.value_json.get(field)
    return value if isinstance(value, int) else default


def main() -> None:
    WorkerRuntime().run()


if __name__ == "__main__":
    main()
