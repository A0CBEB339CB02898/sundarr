import argparse
import os
from pathlib import Path

import uvicorn

from sundarr.app.logging_config import configure_file_logging_from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Sundarr API。")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    configure_file_logging_from_env()
    _write_service_pid()
    uvicorn.run("sundarr.app.main:app", host=args.host, port=args.port, reload=args.reload)


def _write_service_pid() -> None:
    pid_file = os.environ.get("SUNDARR_SERVICE_PID_FILE")
    if pid_file:
        Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")


if __name__ == "__main__":
    main()
