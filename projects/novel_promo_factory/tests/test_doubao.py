import json
from pathlib import Path

import pytest

from app import db, doubao, templates


def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()


def make_project() -> dict:
    project = db.create_project(
        title="最后一班地铁",
        genre="悬疑",
        source_text="末班地铁停在一个不存在的站。广播里忽然报出她的名字。",
        rights_status="owned",
        target_duration=30,
        decision="pending",
        status="pending_approval",
    )
    script = templates.generate_story_script("最后一班地铁", "悬疑", project["source_text"], 30)
    db.update_project(project["id"], script=script, shots=script["shots"])
    return db.get_project(project["id"])


def test_build_batch_is_five_by_ten_and_backs_up_original(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()

    result = doubao.build_batch(project["id"])

    assert result["plan"]["shot_count"] == 5
    assert result["plan"]["duration_per_shot"] == 10
    assert result["plan"]["target_duration"] == 50
    assert len(result["project"]["shots"]) == 5
    assert all(shot["duration"] == 10 for shot in result["project"]["shots"])
    assert result["project"]["target_duration"] == 50
    assert result["project"]["decision"] == "approved"
    backup = Path(result["backup_path"])
    assert backup.is_file()
    assert '"target_duration": 30' in backup.read_text(encoding="utf-8")


def test_build_batch_rejects_unconfirmed_rights(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = db.create_project(
        title="未授权项目",
        genre="悬疑",
        source_text="测试文本",
        rights_status="unconfirmed",
        target_duration=30,
    )
    with pytest.raises(doubao.DoubaoBatchError, match="自有或已授权"):
        doubao.build_batch(project["id"])


def test_import_requires_all_five_and_links_selected_assets(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()
    doubao.build_batch(project["id"])
    paths = doubao.expected_segment_paths(project["id"])

    def fake_probe(path: Path):
        return {
            "path": str(path.resolve()),
            "name": path.name,
            "size": path.stat().st_size,
            "duration": 10.0,
            "width": 720,
            "height": 1280,
            "has_audio": True,
        }

    monkeypatch.setattr(doubao, "_probe_video", fake_probe)
    for path in paths[:4]:
        path.write_bytes(b"fake-mp4-video")

    with pytest.raises(doubao.DoubaoBatchError, match="shot-05.mp4"):
        doubao.import_segments(project["id"])

    paths[4].write_bytes(b"fake-mp4-video")
    result = doubao.import_segments(project["id"])
    assert result["imported"] == 5
    assert result["status"]["ready_to_render"] is True
    fresh = db.get_project(project["id"])
    doubao_assets = [asset for asset in fresh["assets"] if asset["provider"] == "doubao"]
    assert len(doubao_assets) == 5
    assert all(asset["selected"] for asset in doubao_assets)
    assert {asset["shot_id"] for asset in doubao_assets} == {f"shot-{i:02d}" for i in range(1, 6)}


def test_original_bgm_is_generated(tmp_path):
    path = tmp_path / "bgm.wav"
    doubao.generate_original_bgm(path, duration=1.0)
    assert path.is_file()
    assert path.stat().st_size > 100_000
    assert (tmp_path / "bgm.json").is_file()


def test_import_accepts_local_fallback_sidecar_without_mislabeling_it(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()
    doubao.build_batch(project["id"])
    paths = doubao.expected_segment_paths(project["id"])

    def fake_probe(path: Path):
        return {
            "path": str(path.resolve()),
            "name": path.name,
            "size": path.stat().st_size,
            "duration": 10.0,
            "width": 720,
            "height": 1280,
            "has_audio": True,
        }

    monkeypatch.setattr(doubao, "_probe_video", fake_probe)
    for path in paths:
        path.write_bytes(b"fake-mp4-video")
    paths[4].with_suffix(".source.json").write_text(
        json.dumps(
            {
                "provider": "local_fallback",
                "author": "本地后期",
                "license": "Original / generated locally",
                "note": "豆包免费额度不足，使用 shot-04 画面与声音生成标题化收尾镜头",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = doubao.import_segments(project["id"])

    assert result["status"]["ready_to_render"] is True
    selected = [asset for asset in db.get_project(project["id"])["assets"] if asset["selected"]]
    assert len(selected) == 5
    assert sum(asset["provider"] == "doubao" for asset in selected) == 4
    fallback = next(asset for asset in selected if asset["shot_id"] == "shot-05")
    assert fallback["provider"] == "local_fallback"
    assert fallback["author"] == "本地后期"

def test_build_dream_store_sixty_second_batch(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = db.create_project(
        title="会替人做梦的便利店",
        genre="奇幻",
        source_text="凌晨便利店能替人做梦，女孩买了一瓶重逢。",
        rights_status="owned",
        target_duration=30,
    )
    result = doubao.build_batch(project["id"], target_duration=60)

    assert result["plan"]["shot_count"] == 6
    assert result["plan"]["target_duration"] == 60
    assert len(result["project"]["shots"]) == 6
    assert all(shot["duration"] == 10 for shot in result["project"]["shots"])
    assert "便利店" in result["plan"]["title"]
    assert "非CGI" in result["plan"]["shots"][0]["seedance_prompt"]
    assert "冷绿烟雾" in result["plan"]["shots"][0]["seedance_prompt"]
    assert len(doubao.expected_segment_paths(project["id"])) == 6


def test_build_handoff_pilot_uses_project_shots_without_overwriting(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()
    before = db.get_project(project["id"])
    result = doubao.build_handoff(project["id"], pilot=True)
    after = db.get_project(project["id"])

    assert result["mode"] == "pilot"
    assert result["shot_count"] == 1
    assert result["estimated_quota_units"] == 2
    assert Path(result["handoff_path"]).is_file()
    assert Path(result["prompts_path"]).is_file()
    assert "shot-01.mp4" in result["output_path"]
    assert result["prompt"]
    assert after["shots"] == before["shots"]
    status = doubao.status(project["id"])
    assert status["handoff"]["prepared"] is True
    assert status["handoff"]["shot_count"] == 1


def test_import_handoff_pilot_links_first_shot(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()
    result = doubao.build_handoff(project["id"], pilot=True)
    output = Path(result["output_path"])
    output.write_bytes(b"fake-mp4-video")

    def fake_probe(path: Path):
        return {
            "path": str(path.resolve()),
            "name": path.name,
            "size": path.stat().st_size,
            "duration": 10.0,
            "width": 720,
            "height": 1280,
            "has_audio": True,
        }

    monkeypatch.setattr(doubao, "_probe_video", fake_probe)
    imported = doubao.import_handoff(project["id"])
    assert imported["imported"] == 1
    fresh = db.get_project(project["id"])
    doubao_assets = [asset for asset in fresh["assets"] if asset["provider"] == "doubao"]
    assert len(doubao_assets) == 1
    assert doubao_assets[0]["shot_id"] == "shot-01"
    assert bool(doubao_assets[0]["selected"]) is True
