from pathlib import Path

import pytest

from app import config, db, media, sound


def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("PUBLISH_VIDEO_DIR", str(tmp_path / "publish_videos"))
    db.init_db()


def make_project(*, with_video: bool = False) -> dict:
    project = db.create_project(
        title="声音测试",
        genre="悬疑",
        source_text="地铁车厢里突然响起广播。她听到自己的名字。",
        rights_status="owned",
        target_duration=2,
        decision="approved",
    )
    shots = [
        {"id": "shot-01", "duration": 2.0, "title": "广播", "narration": "广播突然响起。", "visual": "地铁车厢里只有她一个人。", "audio": "列车低频、广播失真、心跳"},
    ]
    fields = {"shots": shots, "script": {"shots": shots}, "status": "script_ready"}
    if with_video:
        video = Path(project["folder"]) / "base.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        media._run([
            config.ffmpeg_executable(), "-y", "-f", "lavfi", "-i", "color=c=black:s=320x568:d=2",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video),
        ], cwd=video.parent)
        fields["video_path"] = str(video)
    return db.update_project(project["id"], **fields) or project


def fake_provider_status(*, check_remote: bool = True):
    return {
        "freesound": {"configured": False, "available": False},
        "ace_step": {"configured": True, "available": False},
        "melotts": {"configured": True, "available": False},
        "edge_tts": {"configured": True, "available": True},
        "local_synth": {"configured": True, "available": True},
    }


def test_build_plan_assigns_voice_music_and_sfx_per_shot(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project()
    monkeypatch.setattr(sound, "provider_status", fake_provider_status)

    result = sound.build_plan(project["id"])

    assert result["planned"] is True
    assert result["shot_count"] == 1
    shot = result["plan"]["shots"][0]
    assert shot["audio_plan"]["voice"]["provider"] == "melotts"
    assert shot["audio_plan"]["music"]["provider"] == "ace_step"
    assert shot["audio_plan"]["sfx"][0]["query"] == "subway train interior ambience"
    assert shot["audio_plan"]["start"] == 0
    assert shot["audio_plan"]["end"] == 2


def test_generate_and_mix_with_local_fallbacks(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    project = make_project(with_video=True)
    monkeypatch.setattr(sound, "provider_status", fake_provider_status)
    sound.build_plan(project["id"])

    def fake_voice(text, output, duration, *, voice, rate):
        sound._silence(output, duration)
        return {"provider": "edge_tts", "path": str(output.resolve()), "license": "test", "voice": voice}, None

    monkeypatch.setattr(sound, "_edge_voice", fake_voice)
    monkeypatch.setattr(sound, "_melotts_generate", lambda *args, **kwargs: (_ for _ in ()).throw(sound.SoundError("offline")))
    monkeypatch.setattr(sound, "_ace_step_generate", lambda *args, **kwargs: (_ for _ in ()).throw(sound.SoundError("offline")))
    monkeypatch.setattr(sound, "_freesound_download", lambda *args, **kwargs: (_ for _ in ()).throw(sound.SoundError("offline")))

    generated = sound.generate_assets(project["id"])
    entry = generated["status"]["manifest"]["shots"][0]
    assert entry["voice_provider"] == "edge_tts"
    assert entry["music_provider"] == "local_synth"
    assert entry["sfx"][0]["provider"] == "local_synth"
    assert Path(entry["voice_path"]).is_file()
    assert Path(entry["music_path"]).is_file()

    rendered = sound.render_scene_video(project["id"])
    assert Path(rendered["video_path"]).is_file()
    assert Path(rendered["published_path"]).is_file()
    assert rendered["published_sha256"]
    rendered_again = sound.render_scene_video(project["id"])
    assert Path(rendered_again["video_path"]).is_file()
    assert rendered_again["published_sha256"]
