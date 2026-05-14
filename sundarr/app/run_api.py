import argparse

import uvicorn

from sundarr.app.logging_config import configure_file_logging_from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Sundarr API。")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    configure_file_logging_from_env()
    uvicorn.run("sundarr.app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
