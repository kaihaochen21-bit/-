from app import db, generation, templates


def test_estimate_project_falls_back_missing_stock_to_seedream(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()
    script = templates.generate_story_script("测试", "古风", "第一句。第二句。第三句。")
    project = {"shots": script["shots"], "assets": [], "budget_limit_cny": 20}
    estimate = generation.estimate_project(project)
    assert estimate["stock_fallbacks"]
    assert estimate["seedream_count"] >= 1
    assert "total_cny" in estimate
