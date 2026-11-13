from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from logging.handlers import RotatingFileHandler

from . import config, radar


def _configure_logging() -> None:
    config.ensure_dirs()
    log_path = config.radar_data_dir() / "radar.log"
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(item, RotatingFileHandler) for item in root.handlers):
        root.addHandler(handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI 短剧情报雷达后台扫描")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="执行一次扫描")
    scan_parser.add_argument("--scheduled", action="store_true", help="计划任务模式，生成日报并发送提醒")
    args = parser.parse_args(argv)
    _configure_logging()
    try:
        with radar.scan_lock():
            result = asyncio.run(
                radar.scan_now(
                    generate_report=True,
                    notify=bool(args.scheduled),
                )
            )
        if sys.stdout is not None:
            print(json.dumps(result, ensure_ascii=False))
        logging.info("radar scan completed: %s", result)
        return 0
    except Exception as exc:
        logging.exception("radar scan failed")
        if sys.stdout is not None:
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
