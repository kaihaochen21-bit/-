from fastapi.testclient import TestClient

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
