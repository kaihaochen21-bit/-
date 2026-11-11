from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import config, db
from .jimeng_client import JimengMCPClient


class GenerationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _selected_asset(project: dict[str, Any], shot_id: str) -> dict[str, Any] | None:
    candidates = [asset for asset in project.get("assets") or [] if asset.get("shot_id") == shot_id]
    for asset in candidates:
        if asset.get("selected"):
            return asset
    return candidates[0] if candidates else None


def estimate_project(project: dict[str, Any]) -> dict[str, Any]:
    shots = project.get("shots") or []
    seedream_count = 0
    seedance_seconds = 0.0
    seedance_count = 0
    fallbacks: list[str] = []
    for shot in shots:
        selected = _selected_asset(project, str(shot.get("id")))
        kind = str(shot.get("kind") or "seedream")
        if kind == "stock" and not selected:
            seedream_count += 1
            fallbacks.append(str(shot.get("id")))
        elif kind == "seedream":
            seedream_count += 1
        elif kind == "seedance":
            seedance_count += 1
            seedance_seconds += max(5.0, float(shot.get("duration", 5)))
    total = seedream_count * config.price_seedream() + seedance_seconds * config.price_seedance()
    total = round(total, 2)
    per_limit = float(project.get("budget_limit_cny") or config.per_video_limit())
    return {
        "seedream_count": seedream_count,
        "seedance_count": seedance_count,
        "seedance_seconds": seedance_seconds,
        "total_cny": total,
        "per_video_limit_cny": per_limit,
        "monthly_limit_cny": config.monthly_limit(),
        "month_spend_cny": db.month_spend(),
        "within_per_video_limit": total <= per_limit,
        "within_monthly_limit": db.month_spend() + total <= config.monthly_limit(),
        "stock_fallbacks": fallbacks,
    }


def dry_run(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise GenerationError("项目不存在")
    if project.get("rights_status") not in {"owned", "authorized"}:
        raise GenerationError("请先确认文本为自有或已授权")
    estimate = estimate_project(project)
    db.update_project(project_id, estimated_cost_cny=estimate["total_cny"], status="cost_ready")
    db.add_cost(project_id, "estimate", "jimeng", model=config.seedream_model(), status="estimated", estimated_cny=estimate["total_cny"])
    estimate["project"] = db.get_project(project_id)
    return estimate


async def confirm_generation(project_id: str, *, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        raise GenerationError("必须明确确认后才能调用付费 API")
    if not config.ark_ready():
        raise GenerationError("未配置 ARK_API_KEY，不能调用即梦")
    project = db.get_project(project_id)
    if not project:
        raise GenerationError("项目不存在")
    if project.get("decision") == "pending":
        raise GenerationError("请先在项目审核区接受这个项目，再调用付费生成")
    if project.get("rights_status") not in {"owned", "authorized"}:
        raise GenerationError("请先确认文本为自有或已授权")
    estimate = estimate_project(project)
    if not estimate["within_per_video_limit"]:
        raise GenerationError(f"单条预计成本 {estimate['total_cny']} 元，超过 {estimate['per_video_limit_cny']} 元上限")
    if not estimate["within_monthly_limit"]:
        raise GenerationError(f"本月已花费 {estimate['month_spend_cny']} 元，再加本次预计会超过 {estimate['monthly_limit_cny']} 元上限")
    shots = project.get("shots") or []
    client = JimengMCPClient()
    health = await client.health()
    if not health.get("ok"):
        raise GenerationError(f"即梦健康检查失败：{health}")
    warnings: list[str] = []
    generated: list[dict[str, Any]] = []
    actual_total = 0.0
    generated_root = Path(project["folder"]) / "generated"
    generated_root.mkdir(parents=True, exist_ok=True)
    for index, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("id") or f"shot-{index:02d}")
        selected = _selected_asset(project, shot_id)
        kind = str(shot.get("kind") or "seedream")
        if kind == "stock" and selected:
            continue
        output_dir = generated_root / shot_id
        output_dir.mkdir(parents=True, exist_ok=True)
        if kind in {"seedream", "stock"}:
            prompt = str(shot.get("seedream_prompt") or shot.get("visual") or "电影感小说场景")
            result = await client.generate_image(
                prompt,
                str(output_dir),
                filename_prefix=f"{shot_id}-seedream",
                model_name=config.seedream_model(),
                aspect_ratio="9:16",
                n=1,
                watermark=False,
            )
            images = result.get("images") or []
            if not images:
                raise GenerationError(f"{shot_id} Seedream 没有返回图片：{result}")
            path = Path(images[0]["local_path"])
            db.add_asset(
                project_id, shot_id, "image", "seedream", str(path),
                license="AI Generated", author="Seedream", downloaded_at=db.now_iso(),
                sha256=_sha256(path), width=int(images[0].get("width") or 0), height=int(images[0].get("height") or 0),
                duration=0, selected=True,
            )
            actual_total += config.price_seedream()
            db.add_cost(project_id, "image", "seedream", model=config.seedream_model(), status="success", prompt=prompt, output_path=str(path), estimated_cny=config.price_seedream(), actual_cny=config.price_seedream())
            generated.append({"shot_id": shot_id, "kind": "seedream", "path": str(path)})
        elif kind == "seedance":
            prompt = str(shot.get("seedance_prompt") or shot.get("visual") or "镜头缓慢推进，电影感")
            task = await client.create_video_task(
                prompt,
                model_name=config.seedance_model(),
                resolution="720p",
                ratio="9:16",
                duration=int(max(5, min(15, round(float(shot.get("duration", 5)))))),
                generate_audio=False,
                watermark=False,
            )
            task_id = str(task.get("task_id") or "")
            if not task_id:
                raise GenerationError(f"{shot_id} Seedance 没有返回 task_id：{task}")
            result = await client.wait_video(task_id, str(output_dir), filename_prefix=f"{shot_id}-seedance")
            path = Path(result["local_path"])
            db.add_asset(
                project_id, shot_id, "video", "seedance", str(path),
                license="AI Generated", author="Seedance", downloaded_at=db.now_iso(),
                sha256=_sha256(path), width=720, height=1280,
                duration=float(max(5, round(float(shot.get("duration", 5))))), selected=True,
            )
            actual_total += max(5.0, float(shot.get("duration", 5))) * config.price_seedance()
            db.add_cost(project_id, "video", "seedance", model=config.seedance_model(), task_id=task_id, status="success", prompt=prompt, output_path=str(path), estimated_cny=max(5.0, float(shot.get("duration", 5))) * config.price_seedance(), actual_cny=max(5.0, float(shot.get("duration", 5))) * config.price_seedance())
            generated.append({"shot_id": shot_id, "kind": "seedance", "task_id": task_id, "path": str(path)})
        else:
            warnings.append(f"{shot_id} 类型未知，已跳过")
    actual_total = round(actual_total, 2)
    db.update_project(project_id, actual_cost_cny=actual_total, status="generated")
    return {"generated": generated, "warnings": warnings, "actual_cost_cny": actual_total, "project": db.get_project(project_id)}
