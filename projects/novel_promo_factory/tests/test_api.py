from fastapi.testclient import TestClient

from app import sound
from app.main import app


def test_api_create_and_auto_script(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    with TestClient(app) as client:
        response = client.post("/api/projects", json={
            "title": "接口测试",
            "genre": "校园",
            "source_text": "她走进教室。桌上放着一封信。窗外突然下起雨。",
            "rights_status": "owned",
            "target_duration": 30,
            "budget_limit_cny": 20,
        })
        assert response.status_code == 200
        project = response.json()
        response = client.post(f"/api/projects/{project['id']}/script/auto")
        assert response.status_code == 200
        assert len(response.json()["shots"]) >= 6
        response = client.post(f"/api/projects/{project['id']}/generate/dry-run")
        assert response.status_code == 200
        assert "total_cny" in response.json()

def test_sound_plan_api(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("PUBLISH_VIDEO_DIR", str(tmp_path / "publish_videos"))
    monkeypatch.setattr(sound, "provider_status", lambda **kwargs: {
        "freesound": {"configured": False, "available": False},
        "ace_step": {"configured": True, "available": False},
        "melotts": {"configured": True, "available": False},
        "edge_tts": {"configured": True, "available": True},
        "local_synth": {"configured": True, "available": True},
    })
    with TestClient(app) as client:
        project = client.post("/api/projects", json={
            "title": "声音接口测试",
            "genre": "悬疑",
            "source_text": "地铁里突然响起广播。",
            "rights_status": "owned",
            "target_duration": 15,
            "budget_limit_cny": 20,
        }).json()
        assert client.post(f"/api/projects/{project['id']}/script/auto").status_code == 200
        response = client.post(f"/api/projects/{project['id']}/sound/plan")
        assert response.status_code == 200
        assert response.json()["planned"] is True
        assert client.get(f"/api/projects/{project['id']}/sound/status").status_code == 200


def test_workspace_landing_and_skill_status(tmp_path, monkeypatch):
    skill_root = tmp_path / "skills"
    (skill_root / "ai-short-drama").mkdir(parents=True)
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(skill_root))
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))

    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "AI 短剧工作台" in page.text
        assert "每日视频项目" in page.text
        assert "GitHub 情报" in page.text
        assert "豆包制作 Skill" in page.text

        health = client.get("/api/health")
        assert health.status_code == 200
        skill = health.json()["ai_short_drama_skill"]
        assert skill["installed"] is True
        assert skill["path"].endswith("ai-short-drama")
