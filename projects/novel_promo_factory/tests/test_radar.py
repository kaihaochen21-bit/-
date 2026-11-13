from datetime import datetime, timedelta, timezone

from app import db, radar


def make_repo(**overrides):
    data = {
        "full_name": "example/drama-skill",
        "html_url": "https://github.com/example/drama-skill",
        "description": "开源 AI 短剧 Skill，包含分镜、角色一致性与 Seedance 提示词工作流",
        "topics": ["ai-short-drama", "storyboard", "seedance", "agent-skills"],
        "stargazers_count": 120,
        "forks_count": 18,
        "subscribers_count": 5,
        "open_issues_count": 2,
        "created_at": "2026-08-01T00:00:00Z",
        "pushed_at": "2026-11-12T00:00:00Z",
        "license": {"spdx_id": "MIT"},
        "archived": False,
    }
    data.update(overrides)
    return data


def test_first_snapshot_is_baseline_without_fake_growth():
    now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
    result = radar.score_repository(make_repo(), "本地部署，免费开源，包含分镜和角色一致性", None, now)

    assert result["growth_baseline"] is True
    assert result["star_delta_24h"] is None
    assert result["star_growth_pct_24h"] is None
    assert result["growth_score"] == 0


def test_relevant_fast_growing_repo_beats_unrelated_stale_repo():
    now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
    previous = {"stars": 1000, "forks": 100, "captured_at": (now - timedelta(hours=24)).isoformat()}
    growing = make_repo(stargazers_count=1300, forks_count=145)
    growing_score = radar.score_repository(growing, "开源，本地部署，剧本、分镜、角色一致性和视频提示词", previous, now)

    stale = make_repo(
        full_name="example/awesome-mac",
        html_url="https://github.com/example/awesome-mac",
        description="Awesome macOS software list",
        topics=["awesome-list", "macos"],
        stargazers_count=130000,
        forks_count=10000,
        pushed_at="2025-01-01T00:00:00Z",
    )
    stale_previous = {"stars": 129900, "forks": 10000, "captured_at": (now - timedelta(hours=24)).isoformat()}
    stale_score = radar.score_repository(stale, "A curated list of macOS apps", stale_previous, now)

    assert radar.is_relevant_repository(stale, "A curated list of macOS apps") is False
    assert growing_score["total_score"] > stale_score["total_score"]
    assert growing_score["star_delta_24h"] == 300
    assert growing_score["growth_baseline"] is False


def test_blocklist_filters_piracy_and_torrent_noise():
    repo = make_repo(
        full_name="example/hongguo-torrent-client",
        description="红果短剧第三方客户端 torrent 下载 破解",
        topics=["ai-drama", "torrent"],
    )
    assert radar.is_blocked_repository(repo, "免费下载，绕过会员") is True


def test_repository_type_detects_skill_and_platform():
    skill = make_repo(description="AI 短剧 Agent Skill 技能包", topics=["agent-skills"])
    platform = make_repo(description="开源 AI 短剧制作平台，剧本到成片", topics=["short-drama"])
    assert radar.detect_repository_type(skill, "") == "skill"
    assert radar.detect_repository_type(platform, "") == "platform"


def test_repository_upsert_preserves_user_status(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()

    first = db.upsert_radar_item(
        item_type="repo",
        source_name="GitHub",
        external_id="example/drama-skill",
        title="example/drama-skill",
        url="https://github.com/example/drama-skill",
        summary="first",
        published_at="2026-08-01T00:00:00Z",
        metrics={"stars": 100},
        tags=["skill"],
        scores={"total": 61},
        risk_flags=[],
        license_name="MIT",
    )
    db.update_radar_item_status(first["id"], "trying")
    second = db.upsert_radar_item(
        item_type="repo",
        source_name="GitHub",
        external_id="example/drama-skill",
        title="example/drama-skill",
        url="https://github.com/example/drama-skill",
        summary="updated",
        published_at="2026-08-01T00:00:00Z",
        metrics={"stars": 150},
        tags=["skill"],
        scores={"total": 72},
        risk_flags=[],
        license_name="MIT",
    )

    assert second["id"] == first["id"]
    assert second["status"] == "trying"
    assert second["summary"] == "updated"
    assert second["metrics"]["stars"] == 150


def test_github_search_returns_partial_results_on_rate_limit():
    import asyncio
    import httpx

    calls = {"n": 0}

    async def handler(request: httpx.Request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={"total_count": 1, "items": [make_repo()]},
                headers={"X-RateLimit-Remaining": "8", "X-RateLimit-Reset": "1763020000"},
            )
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1763020000"},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await radar.fetch_github_repositories(client, queries=["q1", "q2"])

    repos, errors, rate_limit = asyncio.run(run())
    assert len(repos) == 1
    assert repos[0]["full_name"] == "example/drama-skill"
    assert errors and "403" in errors[0]
    assert rate_limit["remaining"] == 0


def test_parse_feed_extracts_relevant_news_items():
    xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>New AI video model</title><link>https://example.com/video</link>
      <description><![CDATA[Better short drama video generation]]></description>
      <pubDate>Thu, 12 Nov 2026 20:00:00 GMT</pubDate></item>
      <item><title>Business update</title><link>https://example.com/business</link>
      <description>Customer story</description></item>
    </channel></rss>"""
    items = radar.parse_feed(xml, source_name="Test Feed")
    assert len(items) == 1
    assert items[0]["title"] == "New AI video model"
    assert "short drama" in items[0]["summary"].lower()


def test_page_fingerprint_ignores_build_id_but_detects_content_change():
    first = '<html><meta name="buildId" content="1"><main>Kling 3.0 release</main></html>'
    second = '<html><meta name="buildId" content="2"><main>Kling 3.0 release</main></html>'
    third = '<html><meta name="buildId" content="2"><main>Kling 3.1 release</main></html>'
    assert radar.page_content_fingerprint(first) == radar.page_content_fingerprint(second)
    assert radar.page_content_fingerprint(first) != radar.page_content_fingerprint(third)


def test_daily_report_contains_required_sections_and_baseline_label():
    report = radar.build_daily_report(
        "2026-11-13",
        repos=[
            {
                "title": "example/drama-skill",
                "url": "https://github.com/example/drama-skill",
                "summary": "开源短剧 Skill",
                "total_score": 81,
                "scores": {"star_delta_24h": None, "growth_baseline": True},
                "tags": ["Skill", "开源"],
                "license_name": "MIT",
                "risk_flags": [],
            }
        ],
        updates=[],
    )
    assert "# AI 短剧情报日报 · 2026-11-13" in report
    assert "增长基线建立中" in report
    assert "降本工具" in report
    assert "Skill / 方法" in report
    assert "今日建议试用" in report


def test_scan_now_persists_repo_official_update_and_daily_report(tmp_path, monkeypatch):
    import asyncio
    import httpx

    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()

    async def handler(request: httpx.Request):
        host = request.url.host
        path = request.url.path
        if host == "api.github.com" and path == "/search/repositories":
            return httpx.Response(200, json={"total_count": 1, "items": [make_repo()]})
        if host == "raw.githubusercontent.com":
            return httpx.Response(200, text="开源本地部署。包含分镜、角色一致性、Seedance 提示词。pytest 测试。")
        if host == "openai.com":
            return httpx.Response(
                200,
                text="""<rss><channel><item>
                <title>New short drama video model</title>
                <link>https://example.com/news/video</link>
                <description>AI video and storyboard update</description>
                <pubDate>Thu, 12 Nov 2026 20:00:00 GMT</pubDate>
                </item></channel></rss>""",
            )
        return httpx.Response(200, text="<html><main>release page</main></html>")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await radar.scan_now(
                client=client,
                now=datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc),
                generate_report=True,
                notify=False,
            )

    result = asyncio.run(run())
    items = db.list_radar_items(min_score=0)
    report_path = tmp_path / "data" / "radar" / "reports" / "2026-11-13.md"

    assert result["status"] == "ok"
    assert any(item["item_type"] == "repo" for item in items)
    assert any(item["item_type"] == "news" for item in items)
    assert report_path.is_file()
    assert "example/drama-skill" in report_path.read_text(encoding="utf-8")


def test_radar_api_scan_status_dashboard_and_report(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("RADAR_DISABLE_NOTIFY", "1")

    async def fake_scan(**kwargs):
        return {"run_id": 1, "status": "ok", "items_found": 1, "new_items": 1, "errors": []}

    monkeypatch.setattr(radar, "scan_now", fake_scan)
    with TestClient(app) as client:
        scan = client.post("/api/radar/scan")
        assert scan.status_code == 200
        assert scan.json()["status"] == "ok"

        item = db.upsert_radar_item(
            item_type="repo",
            source_name="GitHub",
            external_id="example/drama-skill",
            title="example/drama-skill",
            url="https://github.com/example/drama-skill",
            summary="开源短剧 Skill",
            published_at="2026-08-01T00:00:00Z",
            metrics={"stars": 100},
            tags=["Skill"],
            scores={"total_score": 78, "relevance_score": 35, "growth_score": 10},
            license_name="MIT",
        )
        dashboard = client.get("/api/radar/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["stats"]["unread"] == 1

        changed = client.post(f"/api/radar/items/{item['id']}/status", json={"status": "trying"})
        assert changed.status_code == 200
        assert changed.json()["status"] == "trying"

        report_md, report_html = radar.write_daily_report("2026-11-13", "# AI 短剧情报日报 · 2026-11-13\n")
        latest = client.get("/api/radar/report/latest?format=md")
        assert latest.status_code == 200
        assert "AI 短剧情报日报" in latest.text

        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["radar"]["unread"] == 0


def test_radar_cli_scheduled_scan_enables_report_and_notification(tmp_path, monkeypatch):
    from app import radar_cli

    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("RADAR_DISABLE_NOTIFY", "1")
    calls = {}

    async def fake_scan(**kwargs):
        calls.update(kwargs)
        return {"status": "ok", "new_items": 0, "items_found": 1, "errors": []}

    monkeypatch.setattr(radar, "scan_now", fake_scan)
    result = radar_cli.main(["scan", "--scheduled"])
    assert result == 0
    assert calls["generate_report"] is True
    assert calls["notify"] is True


def test_parse_feed_filters_old_news_and_generic_workflow_noise():
    xml = """<rss><channel>
      <item><title>DALL-E 2: Extending creativity</title><link>https://example.com/old</link>
      <description>Image generation workflows from 2022</description><pubDate>Thu, 11 Aug 2022 00:00:00 GMT</pubDate></item>
      <item><title>Using skills</title><link>https://example.com/skills</link>
      <description>Generic reusable workflows for agents</description><pubDate>Thu, 12 Nov 2026 20:00:00 GMT</pubDate></item>
      <item><title>Sora short film workflow</title><link>https://example.com/sora</link>
      <description>New AI video and storyboard generation workflow</description><pubDate>Thu, 12 Nov 2026 20:00:00 GMT</pubDate></item>
    </channel></rss>"""
    items = radar.parse_feed(xml, source_name="Test Feed", now=datetime(2026, 11, 13, tzinfo=timezone.utc))
    assert [item["title"] for item in items] == ["Sora short film workflow"]


def test_prune_old_updates_keeps_recent_official_items(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()
    old = db.upsert_radar_item(
        item_type="news", source_name="OpenAI News", external_id="old", title="Old",
        url="https://example.com/old", published_at="2022-08-11T00:00:00+00:00",
    )
    recent = db.upsert_radar_item(
        item_type="news", source_name="OpenAI News", external_id="recent", title="Recent",
        url="https://example.com/recent", published_at="2026-11-12T00:00:00+00:00",
    )
    radar.prune_old_updates(now=datetime(2026, 11, 13, tzinfo=timezone.utc), max_age_days=45)
    remaining = db.list_radar_items(min_score=0)
    assert [item["id"] for item in remaining] == [recent["id"]]


def test_readme_excerpt_removes_markdown_badges_and_links():
    text = "# 项目\n[![badge](https://img.test/b.svg)](https://example.com)\n[文档](https://example.com/docs) 开源短剧工作流"
    excerpt = radar._readme_excerpt(text)
    assert "https://" not in excerpt
    assert "![badge]" not in excerpt
    assert "开源短剧工作流" in excerpt


def test_repo_summary_prefers_clean_description_over_noisy_readme():
    description = "开源 AI 短剧制作平台，支持剧本、分镜、角色一致性、视频生成和本地部署。" * 2
    readme = "<p align=center><img src=badge></p> " + "长 README 内容" * 100
    summary = radar.build_repository_summary(description, readme)
    assert summary.startswith("开源 AI 短剧制作平台")
    assert "<img" not in summary
    assert len(summary) <= 500


def test_scan_notification_is_sent_once_for_same_priority_item(tmp_path, monkeypatch):
    import asyncio
    import httpx

    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    db.init_db()
    notifications = []
    monkeypatch.setattr(radar, "send_windows_notification", lambda title, message: notifications.append((title, message)))
    now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
    db.add_radar_snapshot(
        "example/drama-skill",
        (now - timedelta(hours=24)).isoformat(),
        {"stars": 20, "forks": 1, "watchers": 0, "open_issues": 0, "pushed_at": "2026-11-12T00:00:00Z"},
    )

    async def handler(request: httpx.Request):
        if request.url.host == "api.github.com":
            return httpx.Response(200, json={"total_count": 1, "items": [make_repo()]})
        if request.url.host == "raw.githubusercontent.com":
            return httpx.Response(200, text="开源本地部署，分镜、角色一致性、Seedance、pytest 测试。" * 20)
        if request.url.host == "openai.com":
            return httpx.Response(200, text="<rss><channel></channel></rss>")
        return httpx.Response(200, text="<html><main>stable page</main></html>")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await radar.scan_now(client=client, now=now, generate_report=True, notify=True)
            await radar.scan_now(client=client, now=now + timedelta(hours=4), generate_report=True, notify=True)

    asyncio.run(run())
    assert len(notifications) == 1


def test_fetch_repository_readme_includes_skill_md_for_skill_repo():
    import asyncio
    import httpx

    requested = []

    async def handler(request: httpx.Request):
        requested.append(request.url.path)
        if request.url.path.endswith("README.md"):
            return httpx.Response(200, text="Agent Skill 技能包")
        return httpx.Response(200, text="SKILL workflow instructions")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await radar.fetch_repository_readme(client, make_repo())

    content = asyncio.run(run())
    assert "SKILL workflow instructions" in content
    assert any(path.endswith("SKILL.md") for path in requested)


def test_scan_lock_recovers_from_dead_process(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVEL_PROMO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NOVEL_PROMO_CONTENT_DIR", str(tmp_path / "content"))
    monkeypatch.setenv("NOVEL_PROMO_ASSETS_DIR", str(tmp_path / "assets"))
    lock_path = tmp_path / "data" / "radar" / "scan.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("999999", encoding="ascii")
    with radar.scan_lock():
        assert lock_path.is_file()
    assert not lock_path.exists()


def test_growth_percentage_uses_normalized_24h_delta_for_12h_snapshot():
    now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
    previous = {"stars": 100, "captured_at": (now - timedelta(hours=12)).isoformat()}
    result = radar._growth_metrics(previous, current_stars=220, now=now)
    assert result["star_delta_24h"] == 240
    assert result["star_growth_pct_24h"] == 240.0


def test_growth_percentage_uses_normalized_24h_delta_for_36h_snapshot():
    now = datetime(2026, 11, 13, 8, 30, tzinfo=timezone.utc)
    previous = {"stars": 100, "captured_at": (now - timedelta(hours=36)).isoformat()}
    result = radar._growth_metrics(previous, current_stars=220, now=now)
    assert result["star_delta_24h"] == 80
    assert result["star_growth_pct_24h"] == 80.0
