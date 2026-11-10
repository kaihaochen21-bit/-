from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import db
from .media import make_covers


def _safe_copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"文件不存在：{source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _selected_assets(project: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for shot in project.get("shots") or []:
        candidates = [asset for asset in project.get("assets") or [] if asset.get("shot_id") == shot.get("id")]
        selected = next((asset for asset in candidates if asset.get("selected")), candidates[0] if candidates else None)
        if selected:
            result.append(selected)
    return result


def package_project(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise ValueError("项目不存在")
    video = Path(project.get("video_path") or "")
    if not video.is_file():
        raise ValueError("还没有可打包的视频，请先渲染")
    publish = Path(project["folder"]) / "publish"
    publish.mkdir(parents=True, exist_ok=True)
    _safe_copy(video, publish / "master_9x16.mp4")
    covers = []
    for name in ("cover_douyin.jpg", "cover_xhs.jpg"):
        candidate = Path(project["folder"]) / "render" / name
        if candidate.is_file():
            _safe_copy(candidate, publish / name)
            covers.append(str((publish / name).resolve()))
    if len(covers) != 2:
        generated = make_covers(project, Path(project["folder"]) / "render")
        for source in generated:
            _safe_copy(source, publish / source.name)
        covers = [str((publish / Path(path).name).resolve()) for path in generated]
    srt = Path(project["folder"]) / "render" / "subtitles.srt"
    if srt.is_file():
        _safe_copy(srt, publish / "subtitles.srt")

    title = str(project.get("title") or "AI 小说推文")
    script = project.get("script") or {}
    hooks = script.get("hooks") or ["一条小说，三分钟讲完。"]
    hook = str(hooks[0])
    caption_douyin = f"{title}\n{hook}\n\n#AI小说推文 #AI漫剧 #小说推文制作 #AI视频\nAI生成内容，已标注合成。"
    caption_xhs = (
        f"{title}\n\n{hook}\n\n"
        "这条视频用 Seedream + Seedance 制作，适合小说作者、网文工作室做章节宣传和账号内容。\n"
        "如果你也想把小说做成 15–30 秒竖屏推文视频，可以看主页或私信我。\n\n"
        "#AI小说推文 #AI漫剧 #小说推文制作 #AI视频制作 #网文作者\n"
        "AI生成内容，已标注合成。"
    )
    (publish / "caption_douyin.txt").write_text(caption_douyin, encoding="utf-8")
    (publish / "caption_xhs.txt").write_text(caption_xhs, encoding="utf-8")

    assets = _selected_assets(project)
    for asset in assets:
        if str(asset.get("provider")) in {"pexels", "pixabay"} and not asset.get("license"):
            raise ValueError(f"素材缺少许可证，不能打包：{asset.get('path')}")
    sources = [
        {
            "path": asset.get("path"),
            "provider": asset.get("provider"),
            "source_url": asset.get("source_url"),
            "author": asset.get("author"),
            "license": asset.get("license"),
            "sha256": asset.get("sha256"),
        }
        for asset in assets
    ]
    (publish / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")

    costs = project.get("costs") or []
    generations = [
        {
            "kind": item.get("kind"),
            "provider": item.get("provider"),
            "model": item.get("model"),
            "task_id": item.get("task_id"),
            "status": item.get("status"),
            "output_path": item.get("output_path"),
            "estimated_cny": item.get("estimated_cny"),
            "actual_cny": item.get("actual_cny"),
        }
        for item in costs
    ]
    ai_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "title": title,
        "ai_disclosure": "本视频包含 AI 生成/合成内容",
        "generations": generations,
        "assets": sources,
    }
    (publish / "ai_manifest.json").write_text(json.dumps(ai_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    checklist = """# 发布清单

- [ ] 已在发布前人工审核视频、封面、标题和话题
- [ ] 已确认 AI 生成标识存在
- [ ] 已确认素材来源和许可证记录
- [ ] 已上传 `master_9x16.mp4`
- [ ] 已选择对应平台封面
- [ ] 已复制平台文案
- [ ] 已在官方创作中心人工点击发布
- [ ] 已回填发布链接和数据

## 官方创作中心

- 抖音：https://creator.douyin.com/
- 小红书：https://creator.xiaohongshu.com/

本程序不会保存平台密码、Cookie，也不会自动登录或自动点击发布。
"""
    (publish / "publish_checklist.md").write_text(checklist, encoding="utf-8")

    existing = db.list_posts(project_id)
    post_ids: list[int] = []
    if not existing:
        post_ids.append(db.create_post(project_id, "douyin", title, caption_douyin, str((publish / "master_9x16.mp4").resolve()), str((publish / "cover_douyin.jpg").resolve())))
        post_ids.append(db.create_post(project_id, "xiaohongshu", title, caption_xhs, str((publish / "master_9x16.mp4").resolve()), str((publish / "cover_xhs.jpg").resolve())))
    else:
        post_ids = [int(item["id"]) for item in existing]

    db.update_project(project_id, package_dir=str(publish.resolve()), status="packaged")
    return {
        "package_dir": str(publish.resolve()),
        "files": sorted(path.name for path in publish.iterdir() if path.is_file()),
        "post_ids": post_ids,
        "covers": covers,
    }
