import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

DEFAULT_LOG_MAX_BYTES = 100 * 1024 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description="运行子进程并写入有大小上限的日志文件。")
    parser.add_argument("--log-file", required=True, help="日志文件路径。")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_LOG_MAX_BYTES, help="单个日志文件最大字节数。")
    parser.add_argument("--command-json", help="JSON 编码的命令参数列表。")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的命令，需以 -- 分隔。")
    args = parser.parse_args()

    command = json.loads(args.command_json) if args.command_json else args.command
    if isinstance(command, list) and command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("缺少要执行的命令。")
    if not all(isinstance(item, str) for item in command):
        raise SystemExit("命令参数必须是字符串列表。")

    raise SystemExit(run_with_limited_log(command, Path(args.log_file), max(1, args.max_bytes)))


def run_with_limited_log(command: list[str], log_file: Path, max_bytes: int = DEFAULT_LOG_MAX_BYTES) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    _ensure_log_within_limit(log_file, max_bytes)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def terminate_child(_signum, _frame) -> None:
        if process.poll() is None:
            process.terminate()

    if os.name != "nt":
        signal.signal(signal.SIGTERM, terminate_child)
        signal.signal(signal.SIGINT, terminate_child)

    assert process.stdout is not None
    with log_file.open("ab") as handle:
        while True:
            chunk = process.stdout.readline()
            if not chunk:
                break
            _write_limited_chunk(handle, log_file, chunk, max_bytes)
    return process.wait()


def _ensure_log_within_limit(log_file: Path, max_bytes: int) -> None:
    if log_file.exists() and log_file.stat().st_size > max_bytes:
        log_file.write_bytes(b"")


def _write_limited_chunk(handle, log_file: Path, chunk: bytes, max_bytes: int) -> None:
    if handle.tell() + len(chunk) > max_bytes:
        handle.seek(0)
        handle.truncate()
    handle.write(chunk)
    handle.flush()


if __name__ == "__main__":
    main()
