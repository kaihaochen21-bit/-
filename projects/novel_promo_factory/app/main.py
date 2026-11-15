from __future__ import annotations

import hashlib
import os
from datetime import datetime
from contextlib import asynccontextmanager
import shutil
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, doubao, generation, media, novel, package, radar, radar_curation, sound, stock, templates
from .jimeng_client import JimengMCPClient

@asynccontextmanager
async def lifespan(_: FastAPI):
    config.ensure_dirs()
    db.init_db()
    yield


app = FastAPI(title="AI 短剧工作台", version="1.1.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    genre: str = Field(default="", max_length=30)
    source_text: str = Field(min_length=1)
    rights_status: Literal["unconfirmed", "owned", "authorized"] = "unconfirmed"
    target_duration: int = Field(default=30, ge=15, le=60)
    budget_limit_cny: float = Field(default=20, ge=1, le=100)
    template: str = "story_showreel"


class ScriptSave(BaseModel):
    script: dict[str, Any]
    shots: list[dict[str, Any]] | None = None


class NovelCandidateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    genre: str = Field(default="", max_length=30)
    source_text: str = Field(min_length=1)
    rights_status: Literal["unconfirmed", "owned", "authorized"] = "owned"
    source_url: str = ""
    tags: str = ""
    priority: int = Field(default=0, ge=-100, le=100)


class AutoProjectCreate(BaseModel):
    genre: str = ""
    keywords: str = ""
    target_duration: int = Field(default=30, ge=15, le=60)
    budget_limit_cny: float = Field(default=20, ge=1, le=100)


class AutoBatchCreate(BaseModel):
    count: int = Field(default=5, ge=3, le=5)
    genre: str = ""
    keywords: str = ""
    target_duration: int = Field(default=30, ge=15, le=60)
    budget_limit_cny: float = Field(default=20, ge=1, le=100)


class ProjectDecision(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = ""
    next_candidate: bool = False
    genre: str = ""
    keywords: str = ""
    target_duration: int = Field(default=30, ge=15, le=60)
    budget_limit_cny: float = Field(default=20, ge=1, le=100)


class ConfirmGenerate(BaseModel):
    confirmed: bool = False


class DoubaoPlanCreate(BaseModel):
    target_duration: int = Field(default=50, ge=50, le=60)


class SoundActionRequest(BaseModel):
    force: bool = False


class ManualAssetCreate(BaseModel):
    shot_id: str
    filename: str
    kind: Literal["image", "video"] = "video"
    license: str = ""
    author: str = ""
    source_url: str = ""


class PublishedUpdate(BaseModel):
    published_url: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)


class RadarStatusUpdate(BaseModel):
    status: Literal["unread", "saved", "trying", "tried", "ignored"]


class LeadCreate(BaseModel):
    post_id: int | None = None
    platform: str = ""
    nickname: str = ""
    need_type: str = ""
    budget_range: str = ""
    stage: str = "new"
    qualified: bool = False
    next_action: str = ""
    notes: str = ""


def _project_or_404(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health(deep: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ark_configured": config.ark_ready(),
        "seedream_model": config.seedream_model(),
        "seedance_model": config.seedance_model(),
        "pexels_configured": config.pexels_ready(),
        "pixabay_configured": config.pixabay_ready(),
        "freesound_configured": bool(config.freesound_api_key()),
        "sound_providers": sound.provider_status(check_remote=False),
        "ffmpeg": config.ffmpeg_executable(),
        "mcp_source_root": str(config.mcp_source_root()),
        "mcp_source_exists": config.mcp_source_root().is_dir(),
        "kling_ignored": True,
        "github_token_configured": bool(os.getenv("GITHUB_TOKEN")),
        "radar": db.radar_dashboard(),
        "ai_short_drama_skill": {
            "installed": config.ai_short_drama_skill_dir().is_dir(),
            "path": str(config.ai_short_drama_skill_dir()),
        },
    }
    if deep:
        try:
            result["jimeng"] = await JimengMCPClient().health()
        except Exception as exc:
            result["jimeng"] = {"ok": False, "error": str(exc)}
    return result


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    return db.list_projects()


@app.post("/api/projects")
def create_project(payload: ProjectCreate) -> dict[str, Any]:
    return db.create_project(
        title=payload.title,
        genre=payload.genre,
        source_text=payload.source_text,
        rights_status=payload.rights_status,
        template=payload.template,
        target_duration=payload.target_duration,
        budget_limit_cny=payload.budget_limit_cny,
    )


@app.get("/api/novels")
def list_novels(status: str | None = None) -> list[dict[str, Any]]:
    return db.list_novel_candidates(status)


@app.post("/api/novels")
def create_novel(payload: NovelCandidateCreate) -> dict[str, Any]:
    return db.add_novel_candidate(
        title=payload.title,
        genre=payload.genre,
        source_text=payload.source_text,
        rights_status=payload.rights_status,
        source_url=payload.source_url,
        tags=payload.tags,
        priority=payload.priority,
    )


@app.post("/api/novels/{candidate_id}/project")
def create_project_from_novel(candidate_id: str, payload: AutoProjectCreate) -> dict[str, Any]:
    try:
        return novel.create_project_from_candidate(
            candidate_id,
            target_duration=payload.target_duration,
            budget_limit_cny=payload.budget_limit_cny,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/auto")
def auto_project(payload: AutoProjectCreate) -> dict[str, Any]:
    try:
        return novel.auto_create_project(
            genre=payload.genre,
            keywords=payload.keywords,
            target_duration=payload.target_duration,
            budget_limit_cny=payload.budget_limit_cny,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/auto-batch")
async def auto_batch(payload: AutoBatchCreate) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    warnings: list[str] = []
    service = stock.StockService()
    for _ in range(payload.count):
        try:
            project = novel.auto_create_project(
                genre=payload.genre,
                keywords=payload.keywords,
                target_duration=payload.target_duration,
                budget_limit_cny=payload.budget_limit_cny,
            )
        except Exception as exc:
            warnings.append(str(exc))
            break
        search = await service.search_images_for_project(project["id"], project.get("shots") or [], per_shot=1)
        warnings.extend(search.get("warnings") or [])
        created.append(db.get_project(project["id"]) or project)
    return {"projects": created, "warnings": warnings}


@app.post("/api/projects/{project_id}/decision")
def decide_project(project_id: str, payload: ProjectDecision) -> dict[str, Any]:
    try:
        return novel.decide_project(
            project_id,
            decision=payload.decision,
            reason=payload.reason,
            next_candidate=payload.next_candidate,
            genre=payload.genre,
            keywords=payload.keywords,
            target_duration=payload.target_duration,
            budget_limit_cny=payload.budget_limit_cny,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return _project_or_404(project_id)


@app.post("/api/projects/{project_id}/script/auto")
def auto_script(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    script = templates.generate_story_script(
        str(project.get("title") or ""),
        str(project.get("genre") or ""),
        str(project.get("source_text") or ""),
        int(project.get("target_duration") or 30),
    )
    return db.update_project(project_id, script=script, shots=script["shots"], status="script_ready") or {}


@app.post("/api/projects/{project_id}/script")
def save_script(project_id: str, payload: ScriptSave) -> dict[str, Any]:
    _project_or_404(project_id)
    script = templates.normalize_script(payload.script)
    shots = payload.shots if payload.shots is not None else script.get("shots")
    script["shots"] = shots
    return db.update_project(project_id, script=script, shots=shots, status="script_ready") or {}


@app.post("/api/projects/{project_id}/asset-search")
async def asset_search(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    try:
        return await stock.StockService().search_for_project(project_id, project.get("shots") or [])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/manual-assets")
def manual_assets() -> list[dict[str, Any]]:
    folder = config.assets_dir() / "manual"
    result = []
    for path in sorted(folder.iterdir() if folder.exists() else []):
        if path.is_file():
            result.append({"filename": path.name, "path": str(path.resolve()), "size": path.stat().st_size})
    return result


@app.post("/api/projects/{project_id}/assets/manual")
def add_manual_asset(project_id: str, payload: ManualAssetCreate) -> dict[str, Any]:
    _project_or_404(project_id)
    source = config.assets_dir() / "manual" / Path(payload.filename).name
    if not source.is_file():
        raise HTTPException(status_code=404, detail="assets/manual 中没有这个文件")
    if not payload.license.strip():
        raise HTTPException(status_code=400, detail="手动素材必须填写许可证")
    db.add_asset(
        project_id, payload.shot_id, payload.kind, "manual", str(source),
        source_url=payload.source_url, author=payload.author, license=payload.license,
        downloaded_at=db.now_iso(), sha256=_sha256(source), selected=True,
    )
    return _project_or_404(project_id)


@app.post("/api/projects/{project_id}/assets/{asset_id}/select")
def select_asset(project_id: str, asset_id: int, shot_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    db.select_asset(project_id, shot_id, asset_id)
    return _project_or_404(project_id)


@app.post("/api/projects/{project_id}/generate/dry-run")
def generate_dry_run(project_id: str) -> dict[str, Any]:
    try:
        return generation.dry_run(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/generate/confirm")
async def generate_confirm(project_id: str, payload: ConfirmGenerate) -> dict[str, Any]:
    try:
        return await generation.confirm_generation(project_id, confirmed=payload.confirmed)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/sound/status")
def sound_status(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return sound.status(project_id, check_remote=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/sound/plan")
def sound_plan(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return sound.build_plan(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/sound/generate")
def sound_generate(project_id: str, payload: SoundActionRequest) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return sound.generate_assets(project_id, force=payload.force)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/sound/render")
def sound_render(project_id: str, payload: SoundActionRequest) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return sound.render_scene_video(project_id, force=payload.force)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/doubao/plan")
def doubao_plan(project_id: str, payload: DoubaoPlanCreate) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return doubao.build_batch(project_id, target_duration=payload.target_duration)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/doubao/status")
def doubao_status(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return doubao.status(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/doubao/import")
def doubao_import(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return doubao.import_segments(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/doubao/render")
def doubao_render(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    try:
        return doubao.render_batch(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/render")
def render(project_id: str) -> dict[str, Any]:
    try:
        return media.render_project(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/package")
def package_endpoint(project_id: str) -> dict[str, Any]:
    try:
        return package.package_project(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/video")
def project_video(project_id: str) -> FileResponse:
    project = _project_or_404(project_id)
    path = Path(project.get("video_path") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="视频尚未渲染")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/projects/{project_id}/cover/{platform}")
def project_cover(project_id: str, platform: str) -> FileResponse:
    project = _project_or_404(project_id)
    name = "cover_douyin.jpg" if platform == "douyin" else "cover_xhs.jpg"
    path = Path(project.get("folder") or "") / "publish" / name
    if not path.is_file():
        path = Path(project.get("folder") or "") / "render" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="封面尚未生成")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/queue")
def queue() -> dict[str, Any]:
    return {"projects": db.list_projects(), "posts": db.list_posts(), "dashboard": db.dashboard()}


@app.post("/api/posts/{post_id}/published")
def published(post_id: int, payload: PublishedUpdate) -> dict[str, Any]:
    result = db.mark_published(post_id, payload.published_url, payload.metrics)
    if not result:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    return result


@app.get("/api/leads")
def leads() -> list[dict[str, Any]]:
    return db.list_leads()


@app.post("/api/leads")
def create_lead(payload: LeadCreate) -> dict[str, Any]:
    lead_id = db.add_lead(**payload.model_dump())
    return {"id": lead_id, "lead": next((item for item in db.list_leads() if item["id"] == lead_id), None)}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    return db.dashboard()


@app.get("/api/radar/dashboard")
def radar_dashboard(
    status: str | None = None,
    item_type: str | None = None,
    min_score: float = 50,
    limit: int = 200,
) -> dict[str, Any]:
    stats = db.radar_dashboard()
    items = db.list_radar_items(status=status, item_type=item_type, min_score=min_score, limit=limit)
    update_items = db.list_radar_items(item_type="news", min_score=0, limit=50)
    update_items.extend(db.list_radar_items(item_type="update", min_score=0, limit=50))
    update_items.sort(key=lambda item: item.get("last_seen_at") or "", reverse=True)
    latest = stats.get("latest_run") or {}
    return {
        "stats": stats,
        "items": items,
        "updates": update_items,
        "shortlist": db.list_radar_curation(datetime.now().astimezone().date().isoformat()),
        "installs": db.list_radar_installs(limit=20),
        "last_errors": latest.get("errors") or [],
        "rate_limit": latest.get("rate_limit") or {},
    }


@app.post("/api/radar/scan")
async def radar_scan() -> dict[str, Any]:
    try:
        with radar.scan_lock():
            return await radar.scan_now(generate_report=True, notify=False, auto_install=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/radar/curate")
def radar_curate() -> dict[str, Any]:
    try:
        with radar.scan_lock():
            return radar_curation.auto_curate(auto_install=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/api/radar/items/{item_id}/status")
def radar_item_status(item_id: int, payload: RadarStatusUpdate) -> dict[str, Any]:
    item = db.update_radar_item_status(item_id, payload.status)
    if not item:
        raise HTTPException(status_code=404, detail="雷达项目不存在")
    return item


@app.get("/api/radar/report/latest")
def radar_report_latest(format: Literal["html", "md"] = "html") -> FileResponse:
    suffix = "html" if format == "html" else "md"
    reports = sorted(config.radar_reports_dir().glob(f"*.{suffix}"), reverse=True)
    if not reports:
        raise HTTPException(status_code=404, detail="还没有生成雷达日报")
    media_type = "text/html; charset=utf-8" if suffix == "html" else "text/markdown; charset=utf-8"
    return FileResponse(reports[0], media_type=media_type)


@app.get("/api/radar/report/{report_date}")
def radar_report(report_date: str, format: Literal["html", "md"] = "html") -> FileResponse:
    try:
        datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日报日期格式应为 YYYY-MM-DD") from exc
    suffix = "html" if format == "html" else "md"
    path = config.radar_reports_dir() / f"{report_date}.{suffix}"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="该日期的雷达日报不存在")
    media_type = "text/html; charset=utf-8" if suffix == "html" else "text/markdown; charset=utf-8"
    return FileResponse(path, media_type=media_type)
