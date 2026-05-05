import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 Sundarr FastAPI 后端。")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0。")
    parser.add_argument("--port", type=int, default=8080, help="监听端口，默认 8080。")
    parser.add_argument("--no-reload", action="store_true", help="关闭开发热重载。")
    args = parser.parse_args()

    uvicorn.run(
        "sundarr.app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main()
