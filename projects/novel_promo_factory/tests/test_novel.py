import asyncio

import pytest

from app import config, db, generation, novel


def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()


def test_auto_select_reject_and_next(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    first = db.add_novel_candidate("第一本", "悬疑", "她推开门。房间里没有人。", rights_status="owned", priority=10)
    second = db.add_novel_candidate("第二本", "悬疑", "雨夜，他终于收到那封信。", rights_status="owned", priority=5)
    project = novel.auto_create_project(genre="悬疑")
    assert project["decision"] == "pending"
    assert project["status"] == "pending_approval"
    assert project["novel_id"] == first["id"]
    assert project["shots"]
    assert db.get_novel_candidate(first["id"])["status"] == "in_review"

    result = novel.decide_project(project["id"], decision="reject", next_candidate=True, genre="悬疑")
    assert result["next_project"]["id"] != project["id"]
    assert result["next_project"]["novel_id"] == second["id"]
    assert db.get_novel_candidate(first["id"])["status"] == "rejected"

    approved = novel.decide_project(result["next_project"]["id"], decision="approve")
    assert approved["project"]["decision"] == "approved"
    assert db.get_novel_candidate(second["id"])["status"] == "used"


def test_manual_candidate_project_and_pending_gate(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    candidate = db.add_novel_candidate("手动选择", "古风", "月光落在旧城墙上。", rights_status="authorized")
    project = novel.create_project_from_candidate(candidate["id"])
    assert project["decision"] == "pending"
    assert project["novel_id"] == candidate["id"]

    monkeypatch.setattr(config, "ark_ready", lambda: True)
    with pytest.raises(generation.GenerationError, match="接受这个项目"):
        asyncio.run(generation.confirm_generation(project["id"], confirmed=True))

def test_auto_batch_api(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    for index in range(3):
        db.add_novel_candidate(f"批量候选{index}", "悬疑", f"候选正文{index}。她推开门。", rights_status="owned", priority=10-index)
    async def fake_search(self, project_id, shots, *, per_shot=1):
        return {"downloaded": 0, "warnings": []}
    from app import stock
    monkeypatch.setattr(stock.StockService, "search_images_for_project", fake_search)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        response = client.post("/api/projects/auto-batch", json={"count": 3, "genre": "悬疑", "target_duration": 30, "budget_limit_cny": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 3
        assert all(project["decision"] == "pending" for project in data["projects"])
