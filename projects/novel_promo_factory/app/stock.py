from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import config, db


class StockError(RuntimeError):
    pass


@dataclass
class StockCandidate:
    provider: str
    provider_id: str
    title: str
    source_url: str
    author: str
    license: str
    download_url: str
    width: int
    height: int
    duration: float


def _slug(value: str, fallback: str = "asset") -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_-]+", "-", value).strip("-")
    return cleaned[:60] or fallback


def _select_pexels_file(video: dict[str, Any]) -> dict[str, Any] | None:
    files = [item for item in (video.get("video_files") or []) if item.get("link")]
    if not files:
        return None
    usable = [item for item in files if int(item.get("height") or 0) >= 720 or int(item.get("width") or 0) >= 720]
    pool = usable or files
    return sorted(pool, key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0))[0]


def _select_pixabay_file(video: dict[str, Any]) -> dict[str, Any] | None:
    sizes = video.get("videos") or {}
    ranked = []
    for key in ("large", "medium", "small", "tiny"):
        item = sizes.get(key)
        if item and item.get("url"):
            ranked.append(item)
    if not ranked:
        return None
    usable = [item for item in ranked if int(item.get("height") or 0) >= 720 or int(item.get("width") or 0) >= 720]
    return (usable or ranked)[-1]


class PexelsClient:
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 30):
        self.api_key = api_key
        self.transport = transport
        self.timeout = timeout

    async def search_videos(self, query: str, *, per_page: int = 3) -> list[StockCandidate]:
        if not self.api_key:
            return []
        params = {"query": query, "per_page": per_page, "orientation": "portrait", "size": "medium"}
        headers = {"Authorization": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport, follow_redirects=True) as client:
            response = await client.get("https://api.pexels.com/videos/search", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        candidates: list[StockCandidate] = []
        for video in data.get("videos") or []:
            selected = _select_pexels_file(video)
            if not selected:
                continue
            user = video.get("user") or {}
            candidates.append(
                StockCandidate(
                    provider="pexels",
                    provider_id=str(video.get("id", "")),
                    title=str(video.get("url") or video.get("id") or "Pexels video"),
                    source_url=str(video.get("url") or ""),
                    author=str(user.get("name") or ""),
                    license="Pexels License",
                    download_url=str(selected.get("link") or ""),
                    width=int(selected.get("width") or video.get("width") or 0),
                    height=int(selected.get("height") or video.get("height") or 0),
                    duration=float(video.get("duration") or 0),
                )
            )
        return candidates


class PixabayClient:
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 30):
        self.api_key = api_key
        self.transport = transport
        self.timeout = timeout

    async def search_videos(self, query: str, *, per_page: int = 3) -> list[StockCandidate]:
        if not self.api_key:
            return []
        params = {"key": self.api_key, "q": query, "per_page": per_page, "safesearch": "true", "order": "popular"}
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport, follow_redirects=True) as client:
            response = await client.get("https://pixabay.com/api/videos/", params=params)
            response.raise_for_status()
            data = response.json()
        candidates: list[StockCandidate] = []
        for video in data.get("hits") or []:
            selected = _select_pixabay_file(video)
            if not selected:
                continue
            candidates.append(
                StockCandidate(
                    provider="pixabay",
                    provider_id=str(video.get("id", "")),
                    title=str(video.get("tags") or video.get("id") or "Pixabay video"),
                    source_url=str(video.get("pageURL") or ""),
                    author=str(video.get("user") or ""),
                    license="Pixabay Content License",
                    download_url=str(selected.get("url") or ""),
                    width=int(selected.get("width") or 0),
                    height=int(selected.get("height") or 0),
                    duration=float(video.get("duration") or 0),
                )
            )
        return candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _download(url: str, target: Path, *, transport: httpx.AsyncBaseTransport | None = None, timeout: float = 90) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=timeout, transport=transport, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    handle.write(chunk)


class StockService:
    def __init__(self, *, pexels: PexelsClient | None = None, pixabay: PixabayClient | None = None):
        self.pexels = pexels or PexelsClient(os.getenv("PEXELS_API_KEY", ""))
        self.pixabay = pixabay or PixabayClient(os.getenv("PIXABAY_API_KEY", ""))

    async def search_for_project(self, project_id: str, shots: list[dict[str, Any]], *, per_shot: int = 3) -> dict[str, Any]:
        project = db.get_project(project_id)
        if not project:
            raise StockError("项目不存在")
        warnings: list[str] = []
        downloaded = 0
        for shot in shots:
            if shot.get("kind") != "stock":
                continue
            shot_id = str(shot.get("id"))
            query = " ".join(str(item) for item in (shot.get("keywords") or [])[:2]).strip() or "cinematic"
            candidates: list[StockCandidate] = []
            if self.pexels.api_key:
                try:
                    candidates.extend(await self.pexels.search_videos(query, per_page=per_shot))
                except Exception as exc:
                    warnings.append(f"{shot_id} Pexels 搜索失败：{exc}")
            if len(candidates) < per_shot and self.pixabay.api_key:
                try:
                    candidates.extend(await self.pixabay.search_videos(query, per_page=per_shot - len(candidates)))
                except Exception as exc:
                    warnings.append(f"{shot_id} Pixabay 搜索失败：{exc}")
            if not self.pexels.api_key and not self.pixabay.api_key:
                warnings.append("未配置 PEXELS_API_KEY 或 PIXABAY_API_KEY；可把素材放到 assets/manual/ 后手动关联。")
                break
            selected_any = False
            for index, candidate in enumerate(candidates[:per_shot]):
                suffix = Path(candidate.download_url.split("?")[0]).suffix or ".mp4"
                target = config.assets_dir() / "candidates" / project_id / shot_id / f"{candidate.provider}-{_slug(candidate.provider_id, str(index))}{suffix}"
                try:
                    await _download(candidate.download_url, target)
                    sidecar = {
                        "path": str(target.resolve()),
                        "provider": candidate.provider,
                        "source_url": candidate.source_url,
                        "author": candidate.author,
                        "license": candidate.license,
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "sha256": _sha256(target),
                        "width": candidate.width,
                        "height": candidate.height,
                        "duration": candidate.duration,
                        "selected": not selected_any,
                    }
                    target.with_suffix(target.suffix + ".json").write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
                    db.add_asset(project_id, shot_id, "video", candidate.provider, str(target), **sidecar)
                    selected_any = True
                    downloaded += 1
                except Exception as exc:
                    warnings.append(f"{shot_id} 下载失败：{exc}")
            if not selected_any:
                warnings.append(f"{shot_id} 没有找到可用素材，渲染时会回退到 Seedream 图片。")
        return {"downloaded": downloaded, "warnings": warnings, "project": db.get_project(project_id)}
