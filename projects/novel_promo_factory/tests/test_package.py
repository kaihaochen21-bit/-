import json
from pathlib import Path

from PIL import Image

from app import db, package, templates


def test_package_contains_required_files(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()
    project = db.create_project("打包测试", "悬疑", "她推开门。房间里没有人。", rights_status="owned")
    script = templates.generate_story_script("打包测试", "悬疑", "她推开门。房间里没有人。")
    db.update_project(project["id"], script=script, shots=script["shots"])
    project = db.get_project(project["id"])
    render = Path(project["folder"]) / "render"
    render.mkdir(parents=True, exist_ok=True)
    video = render / "master_9x16.mp4"
    video.write_bytes(b"test-video")
    for name in ("cover_douyin.jpg", "cover_xhs.jpg"):
        Image.new("RGB", (1080, 1920), "#222222").save(render / name)
    db.update_project(project["id"], video_path=str(video))
    result = package.package_project(project["id"])
    publish = Path(result["package_dir"])
    for name in ("master_9x16.mp4", "cover_douyin.jpg", "cover_xhs.jpg", "caption_douyin.txt", "caption_xhs.txt", "ai_manifest.json", "sources.json", "publish_checklist.md"):
        assert (publish / name).is_file(), name
    assert len(result["post_ids"]) == 2
