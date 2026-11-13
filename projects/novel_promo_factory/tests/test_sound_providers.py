from pathlib import Path
import json as jsonlib

from app import config, db, media, sound


def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()


def make_project():
    return db.create_project(
        title="声音 Provider 测试",
        genre="悬疑",
        source_text="地铁广播突然响起。",
        rights_status="owned",
        target_duration=15,
        decision="approved",
    )



class FakeResponse:
    def __init__(self, status_code=200, data=None, content=b""):
        self.status_code = status_code
        self._data = data
        self.content = content

    def json(self):
        return self._data


def test_freesound_download_filters_cc0(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("FREESOUND_API_KEY", "test-key")
    calls = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if "search" in url:
                return FakeResponse(data={"results": [
                    {"id": 1, "name": "subway", "license": "Attribution Noncommercial", "username": "bad", "duration": 5, "url": "https://freesound.org/s/1/", "previews": {"preview-hq-mp3": "https://bad"}},
                    {"id": 2, "name": "subway cc0", "license": "Creative Commons 0", "username": "good", "duration": 6, "url": "https://freesound.org/s/2/", "previews": {"preview-hq-mp3": "https://good"}},
                ]})
            return FakeResponse(content=b"mp3-data" * 100)

    monkeypatch.setattr(sound.httpx, "Client", FakeClient)
    result = sound._freesound_download("subway", tmp_path, "sfx")
    assert result["license"] == "Creative Commons 0"
    assert result["author"] == "good"
    assert Path(result["path"]).is_file()
    assert calls[0][1]["params"]["token"] == "test-key"


def test_ace_step_client_submits_and_downloads(tmp_path, monkeypatch):
    output = tmp_path / "ace.wav"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.post_count = 0
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, url, **kwargs):
            self.post_count += 1
            if url.endswith("/release_task"):
                return FakeResponse(data={"data": {"task_id": "task-1"}})
            return FakeResponse(data={"data": [{"task_id": "task-1", "status": 1, "result": jsonlib.dumps([{"file": "/v1/audio?path=test.wav"}])}]})
        def get(self, url, **kwargs):
            return FakeResponse(content=b"RIFF" + b"0" * 800)

    monkeypatch.setattr(sound.httpx, "Client", FakeClient)
    monkeypatch.setattr(sound.time, "sleep", lambda _: None)
    result = sound._ace_step_generate("suspense instrumental", tmp_path, "ace", 10)
    assert result["provider"] == "ace_step"
    assert result["task_id"] == "task-1"
    assert Path(result["path"]).read_bytes().startswith(b"RIFF")


def test_melotts_client_writes_wav(tmp_path, monkeypatch):
    output = tmp_path / "voice.wav"
    monkeypatch.setattr(sound.httpx, "post", lambda *args, **kwargs: FakeResponse(content=b"RIFF" + b"1" * 800))
    result = sound._melotts_generate("测试旁白", output, language="ZH", speaker="ZH", speed=1.0)
    assert result["provider"] == "melotts"
    assert output.is_file()
    assert output.read_bytes().startswith(b"RIFF")
