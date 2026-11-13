from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config

CACHE_DIR = Path.home() / "AppData/Local/Doubao/User Data/Default/Cache/Cache_Data"


def _number(path: Path) -> int | None:
    match = re.fullmatch(r"f_([0-9a-fA-F]+)", path.name)
    return int(match.group(1), 16) if match else None


def _name(number: int) -> str:
    return f"f_{number:06x}"


def _expected_mp4_size(data: bytes) -> int | None:
    position = 0
    expected = None
    while position + 8 <= len(data):
        size, box_type = struct.unpack(">I4s", data[position : position + 8])
        if size == 1 and position + 16 <= len(data):
            size = struct.unpack(">Q", data[position + 8 : position + 16])[0]
        if size < 8:
            break
        if box_type == b"mdat":
            expected = position + size
            break
        position += size
    return expected


def _probe(path: Path) -> dict | None:
    result = subprocess.run(
        [config.ffmpeg_executable(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    text = result.stderr or ""
    if "Video:" not in text:
        return None
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", text)
    if not duration:
        return None
    h, m, s = duration.groups()
    return {
        "duration": round(int(h) * 3600 + int(m) * 60 + float(s), 3),
        "width": int(size.group(1)) if size else 0,
        "height": int(size.group(2)) if size else 0,
        "has_audio": "Audio:" in text,
        "size": path.stat().st_size,
    }


def extract(*, since_epoch: float, output: Path, min_seconds: float = 5.0) -> dict:
    candidates: list[tuple[float, Path, dict]] = []
    for first in CACHE_DIR.glob("f_*"):
        first_number = _number(first)
        if first_number is None or not first.is_file():
            continue
        stat = first.stat()
        if stat.st_mtime < since_epoch or stat.st_size < 100_000:
            continue
        with first.open("rb") as handle:
            if b"ftyp" not in handle.read(64):
                continue
        data = first.read_bytes()
        expected = _expected_mp4_size(data)
        parts = [first]
        if expected and len(data) < expected:
            nearby = []
            for part in CACHE_DIR.glob("f_*"):
                if part == first or not part.is_file() or part.stat().st_size < 100_000:
                    continue
                if abs(part.stat().st_mtime - stat.st_mtime) > 2.0:
                    continue
                with part.open("rb") as handle:
                    head = handle.read(16)
                if b"ftyp" in head or head.startswith((b"\x89PNG", b"\xff\xd8", b"PK\x03\x04", b"RIFF")):
                    continue
                nearby.append(part)
            for part in sorted(nearby, key=lambda item: item.stat().st_size, reverse=True):
                parts.append(part)
                if sum(part.stat().st_size for part in parts) >= expected:
                    break
        if len(parts) == 1:
            cursor = first_number + 1
            while True:
                part = CACHE_DIR / _name(cursor)
                if not part.is_file() or part.stat().st_size < 100_000:
                    break
                parts.append(part)
                cursor += 1
        temporary = output.with_suffix(".candidate.mp4")
        with temporary.open("wb") as target:
            for part in parts:
                with part.open("rb") as source:
                    shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
        if expected:
            with temporary.open("r+b") as handle:
                handle.truncate(expected)
        info = _probe(temporary)
        decode = subprocess.run(
            [config.ffmpeg_executable(), "-hide_banner", "-v", "error", "-i", str(temporary), "-f", "null", "NUL"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if info and info["duration"] >= min_seconds and decode.returncode == 0 and "partial file" not in (decode.stderr or ""):
            candidates.append((stat.st_mtime, temporary, info))
        else:
            temporary.unlink(missing_ok=True)
    if not candidates:
        raise SystemExit(f"未找到可用的豆包 MP4 缓存。缓存目录：{CACHE_DIR}")
    candidates.sort(key=lambda item: (item[0], item[2]["duration"], item[2]["size"]), reverse=True)
    _, temporary, info = candidates[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.replace(output)
    metadata = {"path": str(output.resolve()), **info}
    output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="从豆包 Chromium 缓存提取最近生成的 MP4")
    parser.add_argument("output", type=Path)
    parser.add_argument("--since-minutes", type=float, default=30)
    parser.add_argument("--min-seconds", type=float, default=5.0)
    args = parser.parse_args()
    info = extract(
        since_epoch=time.time() - args.since_minutes * 60,
        output=args.output.resolve(),
        min_seconds=args.min_seconds,
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
