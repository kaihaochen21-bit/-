from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def data_dir() -> Path:
    return Path(os.getenv("NOVEL_PROMO_DATA_DIR") or (PROJECT_ROOT / "data")).resolve()

def content_dir() -> Path:
    return Path(os.getenv("NOVEL_PROMO_CONTENT_DIR") or (PROJECT_ROOT / "content")).resolve()

def assets_dir() -> Path:
    return Path(os.getenv("NOVEL_PROMO_ASSETS_DIR") or (PROJECT_ROOT / "assets")).resolve()

def db_path() -> Path:
    return data_dir() / "app.db"

def radar_data_dir() -> Path:
    return data_dir() / "radar"


def radar_reports_dir() -> Path:
    return radar_data_dir() / "reports"


def ensure_dirs() -> None:
    for path in (
        data_dir(), content_dir(), assets_dir(), assets_dir() / "manual",
        assets_dir() / "candidates", assets_dir() / "generated",
        radar_data_dir(), radar_reports_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)

def mcp_source_root() -> Path:
    configured = os.getenv("JIMENG_MCP_SOURCE_ROOT")
    default = Path(r"C:\Users\陈楷浩\OneDrive\桌面\脚本数据\kling-image-mcp")
    return Path(configured).resolve() if configured else default

def ffmpeg_executable() -> str:
    configured = os.getenv("FFMPEG_PATH")
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def ark_ready() -> bool:
    return bool(os.getenv("ARK_API_KEY") or os.getenv("VOLCENGINE_API_KEY"))

def pexels_ready() -> bool:
    return bool(os.getenv("PEXELS_API_KEY"))

def pixabay_ready() -> bool:
    return bool(os.getenv("PIXABAY_API_KEY"))

def seedream_model() -> str:
    return os.getenv("ARK_MODEL_NAME") or "doubao-seedream-5-0-flash-260915"

def seedance_model() -> str:
    return os.getenv("SEEDANCE_MODEL_NAME") or "doubao-seedance-2-0-mini-260615"

def price_seedream() -> float:
    return float(os.getenv("SEEDREAM_UNIT_COST_CNY", "0.12"))

def price_seedance() -> float:
    return float(os.getenv("SEEDANCE_UNIT_COST_CNY", "0.50"))

def per_video_limit() -> float:
    return float(os.getenv("NOVEL_PROMO_PER_VIDEO_LIMIT", "20"))

def monthly_limit() -> float:
    return float(os.getenv("NOVEL_PROMO_MONTHLY_LIMIT", "600"))

def max_seedance_shots() -> int:
    return int(os.getenv("NOVEL_PROMO_MAX_SEEDANCE_SHOTS", "3"))
