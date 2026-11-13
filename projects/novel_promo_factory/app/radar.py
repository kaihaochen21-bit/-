from __future__ import annotations

import hashlib
import html as html_lib
import math
import os
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from . import config, db


CORE_DRAMA_TERMS = (
    "ai短剧", "ai 短剧", "ai漫剧", "ai 漫剧", "短剧", "漫剧", "short drama",
    "short-drama", "microdrama", "micro drama", "comic drama", "ai film",
    "ai movie", "ai video",
)
CAPABILITY_TERMS = (
    "storyboard", "分镜", "剧本", "script", "角色一致性", "character consistency",
    "prompt", "提示词", "seedance", "kling", "可灵", "即梦", "veo", "sora",
    "comfyui", "text-to-video", "image-to-video", "视频生成", "视频工作流",
    "agent skill", "agent skills", "skill", "工作流", "workflow", "ffmpeg",
    "配音", "voice", "字幕", "subtitle", "剪辑", "editing",
)
COST_TERMS = (
    "open source", "open-source", "开源", "self-host", "self hosted", "本地部署",
    "local-first", "本地优先", "free", "免费", "no api", "无需 api", "免费素材",
    "ffmpeg", "edge tts", "本地模型", "offline", "离线",
)
BLOCK_TERMS = (
    "torrent", "bt下载", "破解", "盗版", "porn", "nsfw", "uncensored", "成人内容",
    "第三方客户端", "third-party client", "影视聚合", "盗链", "破解版",
)
GENERIC_NOISE_TERMS = (
    "awesome mac", "macos software", "react starter", "firebase starter",
    "qbit", "qbittorrent", "torrent client", "seed project",
)
REPO_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("skill", ("skill", "技能包", "agent skills", "codex skill", "claude skill")),
    ("prompt", ("prompt", "提示词", "prompt library")),
    ("workflow", ("workflow", "工作流", "comfyui", "pipeline", "流水线")),
    ("platform", ("平台", "platform", "studio", "一站式", "剧本到成片", "script-to-video")),
    ("awesome", ("awesome", "curated list", "精选", "教程", "tutorial")),
    ("asset-tool", ("素材", "asset", "字幕", "subtitle", "配音", "voice", "剪辑", "editing")),
)


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _haystack(repo: dict[str, Any], extra_text: str = "") -> str:
    topics = repo.get("topics") or []
    if isinstance(topics, str):
        topics = [topics]
    return " ".join(
        [
            str(repo.get("full_name") or ""),
            str(repo.get("description") or ""),
            " ".join(str(item) for item in topics),
            extra_text or "",
        ]
    ).lower()


def is_blocked_repository(repo: dict[str, Any], extra_text: str = "") -> bool:
    text = _haystack(repo, extra_text)
    return any(term in text for term in BLOCK_TERMS)


def is_relevant_repository(repo: dict[str, Any], extra_text: str = "") -> bool:
    text = _haystack(repo, extra_text)
    if any(term in text for term in BLOCK_TERMS):
        return False
    if any(term in text for term in GENERIC_NOISE_TERMS):
        return False
    if any(term in text for term in CORE_DRAMA_TERMS):
        return True
    capability_hits = {term for term in CAPABILITY_TERMS if term in text}
    return len(capability_hits) >= 2


def detect_repository_type(repo: dict[str, Any], extra_text: str = "") -> str:
    text = _haystack(repo, extra_text)
    scored = [(sum(1 for term in terms if term in text), index, repo_type) for index, (repo_type, terms) in enumerate(REPO_TYPES)]
    best = max(scored, key=lambda item: (item[0], -item[1]))
    return best[2] if best[0] > 0 else "other"


def _relevance_score(repo: dict[str, Any], extra_text: str) -> int:
    if not is_relevant_repository(repo, extra_text):
        return 0
    text = _haystack(repo, extra_text)
    score = 20 if any(term in text for term in CORE_DRAMA_TERMS) else 8
    capability_hits = sum(1 for term in CAPABILITY_TERMS if term in text)
    score += min(12, capability_hits * 3)
    cost_hits = sum(1 for term in COST_TERMS if term in text)
    score += min(8, cost_hits * 2)
    return min(40, score)


def _growth_metrics(previous: dict[str, Any] | None, current_stars: int, now: datetime) -> dict[str, Any]:
    if not previous:
        return {
            "growth_baseline": True,
            "star_delta_24h": None,
            "star_growth_pct_24h": None,
            "growth_score": 0,
            "growth_status": "baseline",
        }
    captured = _parse_dt(previous.get("captured_at"))
    if captured is None:
        return {
            "growth_baseline": True,
            "star_delta_24h": None,
            "star_growth_pct_24h": None,
            "growth_score": 0,
            "growth_status": "invalid_snapshot",
        }
    hours = (now - captured).total_seconds() / 3600
    if hours < 12 or hours > 36:
        return {
            "growth_baseline": False,
            "star_delta_24h": None,
            "star_growth_pct_24h": None,
            "growth_score": 0,
            "growth_status": "insufficient_interval",
        }
    previous_stars = max(0, int(previous.get("stars") or 0))
    delta = int(current_stars) - previous_stars
    normalized_delta = int(round(delta * 24 / hours))
    pct = (normalized_delta / previous_stars * 100) if previous_stars > 0 else None
    growth_score = 0.0
    if normalized_delta > 0:
        growth_score += min(15.0, math.log2(normalized_delta + 1) * 3)
        if pct is not None:
            growth_score += min(10.0, max(0.0, pct) * 1.5)
        if previous_stars < 10:
            growth_score = min(growth_score, 4.0)
    return {
        "growth_baseline": False,
        "star_delta_24h": normalized_delta,
        "star_growth_pct_24h": round(pct, 2) if pct is not None else None,
        "growth_score": round(growth_score, 1),
        "growth_status": "ok",
    }


def _freshness_score(repo: dict[str, Any], now: datetime) -> int:
    pushed = _parse_dt(repo.get("pushed_at"))
    if pushed is None:
        return 0
    age_days = max(0.0, (now - pushed).total_seconds() / 86400)
    if age_days <= 7:
        return 15
    if age_days <= 30:
        return 10
    if age_days <= 90:
        return 4
    return 0


def _credibility_score(repo: dict[str, Any], readme: str) -> int:
    score = 0
    license_info = repo.get("license") or {}
    spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else ""
    if spdx and spdx not in {"NOASSERTION", "NONE"}:
        score += 3
    if int(repo.get("forks_count") or 0) >= 5:
        score += 1
    if len(repo.get("topics") or []) >= 3:
        score += 1
    if len(readme) >= 500:
        score += 2
    if len(str(repo.get("description") or "")) >= 80:
        score += 1
    lower = readme.lower()
    if any(token in lower for token in ("pytest", "npm test", "ci", "github actions", "test suite")):
        score += 2
    return min(10, score)


def _cost_score(repo: dict[str, Any], text: str) -> int:
    lower = text.lower()
    score = 0
    license_info = repo.get("license") or {}
    spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else ""
    if spdx and spdx not in {"NOASSERTION", "NONE"}:
        score += 4
    score += min(6, sum(2 for term in COST_TERMS if term in lower))
    return min(10, score)


def _risk_flags(repo: dict[str, Any], now: datetime) -> list[str]:
    flags: list[str] = []
    license_info = repo.get("license") or {}
    spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else ""
    if not spdx or spdx in {"NOASSERTION", "NONE"}:
        flags.append("许可证不明确")
    if repo.get("archived"):
        flags.append("仓库已归档")
    created = _parse_dt(repo.get("created_at"))
    if created and (now - created).days <= 7 and int(repo.get("stargazers_count") or 0) >= 1000:
        flags.append("新仓库暴涨，需复核")
    if int(repo.get("stargazers_count") or 0) >= 1000 and int(repo.get("forks_count") or 0) < 5:
        flags.append("Star/Fork 比例异常")
    return flags


def recommendation_for_score(total_score: float) -> str:
    if total_score >= 75:
        return "priority"
    if total_score >= 60:
        return "watch"
    return "low"


def score_repository(
    repo: dict[str, Any],
    readme: str,
    previous_snapshot: dict[str, Any] | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    extra_text = readme or ""
    relevant = is_relevant_repository(repo, extra_text)
    relevance = _relevance_score(repo, extra_text)
    growth = _growth_metrics(previous_snapshot, int(repo.get("stargazers_count") or 0), now)
    freshness = _freshness_score(repo, now)
    credibility = _credibility_score(repo, readme)
    cost = _cost_score(repo, _haystack(repo, extra_text))
    total = round(relevance + growth["growth_score"] + freshness + credibility + cost, 1) if relevant else 0.0
    repo_type = detect_repository_type(repo, extra_text)
    tags = [repo_type]
    lower = _haystack(repo, extra_text)
    for term, label in (
        ("seedance", "Seedance"), ("kling", "Kling"), ("可灵", "Kling"),
        ("comfyui", "ComfyUI"), ("本地部署", "本地部署"), ("开源", "开源"),
        ("分镜", "分镜"), ("角色一致性", "角色一致性"), ("skill", "Skill"),
        ("ffmpeg", "FFmpeg"), ("免费", "免费"),
    ):
        if term in lower and label not in tags:
            tags.append(label)
    return {
        **growth,
        "relevant": relevant,
        "blocked": is_blocked_repository(repo, extra_text),
        "relevance_score": relevance,
        "freshness_score": freshness,
        "credibility_score": credibility,
        "cost_score": cost,
        "total_score": total,
        "repo_type": repo_type,
        "tags": tags,
        "risk_flags": _risk_flags(repo, now),
        "recommendation": recommendation_for_score(total),
    }

GITHUB_QUERIES = (
    "topic:ai-short-drama stars:>3",
    "topic:ai-drama stars:>3",
    "topic:short-drama stars:>3",
    '"AI短剧" in:name,description,readme',
    '"AI漫剧" in:name,description,readme',
    '"Seedance" OR "Kling" OR "ComfyUI" storyboard in:name,description,readme stars:>10',
)


async def fetch_github_repositories(
    client: httpx.AsyncClient,
    *,
    token: str = "",
    queries: list[str] | tuple[str, ...] = GITHUB_QUERIES,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Short-Drama-Radar/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    rate_limit: dict[str, Any] = {}
    for query in queries:
        try:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": 30},
                headers=headers,
            )
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            if remaining is not None:
                rate_limit = {"remaining": int(remaining), "reset": reset or ""}
            if response.status_code in {403, 429}:
                message = ""
                try:
                    message = str((response.json() or {}).get("message") or "")
                except Exception:
                    message = response.text[:200]
                errors.append(f"GitHub 搜索受限 {response.status_code}: {message or query}")
                if rate_limit.get("remaining") == 0:
                    break
                continue
            response.raise_for_status()
            for item in (response.json() or {}).get("items") or []:
                full_name = str(item.get("full_name") or "")
                if full_name:
                    repos[full_name] = item
        except Exception as exc:
            errors.append(f"GitHub 搜索失败 [{query}]: {type(exc).__name__}: {exc}")
    return list(repos.values()), errors, rate_limit


def _plain_text(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _text_is_relevant(text: str) -> bool:
    lower = text.lower()
    if any(term in lower for term in CORE_DRAMA_TERMS):
        return True
    return sum(1 for term in CAPABILITY_TERMS if term in lower) >= 2


def _parse_feed_time(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except Exception:
            return text


def _news_is_relevant(text: str) -> bool:
    lower = text.lower()
    news_terms = (
        "video", "short drama", "storyboard", "image generation", "sora", "veo",
        "kling", "seedance", "film", "movie", "multimodal", "voice", "audio",
        "creative workflow", "prompt", "visual",
    )
    return any(term in lower for term in news_terms)


def parse_feed(
    xml_text: str,
    *,
    source_name: str,
    now: datetime | None = None,
    max_age_days: int = 45,
) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    nodes = root.findall(".//item")
    if not nodes:
        nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "entry"]
    result: list[dict[str, Any]] = []
    for node in nodes:
        values: dict[str, str] = {}
        for child in list(node):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag in {"title", "link", "description", "summary", "content", "pubDate", "published", "updated", "id"}:
                if tag == "link" and not (child.text or "").strip():
                    values[tag] = child.attrib.get("href", "")
                else:
                    values[tag] = child.text or ""
        title = _plain_text(values.get("title"))
        summary = _plain_text(values.get("description") or values.get("summary") or values.get("content"))
        url = values.get("link") or values.get("id") or ""
        full_text = f"{title} {summary}"
        if not title or not url or not _news_is_relevant(full_text) or not _text_is_relevant(full_text):
            continue
        published_at = _parse_feed_time(values.get("pubDate") or values.get("published") or values.get("updated"))
        published_dt = _parse_dt(published_at)
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=max_age_days)
        if published_dt and published_dt < cutoff:
            continue
        result.append(
            {
                "source_name": source_name,
                "external_id": url,
                "title": title,
                "url": url,
                "summary": summary[:800],
                "published_at": published_at,
            }
        )
    return result


def page_content_fingerprint(html_text: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html_text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<meta[^>]+(?:buildId|build-id)[^>]*>", " ", text, flags=re.I)
    text = _plain_text(text)
    text = re.sub(r"\b[0-9a-f]{16,}\b", " ", text, flags=re.I)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _item_growth_label(item: dict[str, Any]) -> str:
    scores = item.get("scores") or {}
    if item.get("growth_baseline") or scores.get("growth_baseline"):
        return "增长基线建立中"
    delta = item.get("star_delta_24h", scores.get("star_delta_24h"))
    if delta is None:
        return "增长待确认"
    sign = "+" if int(delta) >= 0 else ""
    return f"24h Star {sign}{int(delta)}"


def _item_tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags") or []
    return [str(tag) for tag in tags if str(tag).strip()]


def build_daily_report(
    report_date: str,
    *,
    repos: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> str:
    repos = sorted(repos, key=lambda item: float(item.get("total_score") or 0), reverse=True)
    top_repos = repos[:5]
    cost_repos = [
        item for item in repos
        if any(tag in {"开源", "本地部署", "免费", "FFmpeg"} for tag in _item_tags(item))
    ][:5]
    method_repos = [
        item for item in repos
        if item.get("repo_type") in {"skill", "prompt", "workflow"} or any(tag in {"Skill", "分镜", "角色一致性"} for tag in _item_tags(item))
    ][:5]
    lines = [
        f"# AI 短剧情报日报 · {report_date}",
        "",
        "> 自动规则评估，不等同于人工评测或付费模型结论。Star 历史从本程序首次快照开始积累。",
        "",
        "## 今日高增长与高相关项目",
        "",
    ]
    if top_repos:
        for index, item in enumerate(top_repos, start=1):
            score = float(item.get("total_score") or 0)
            tags = " / ".join(_item_tags(item)) or "未分类"
            license_name = item.get("license_name") or "未明确"
            lines.extend(
                [
                    f"{index}. [{item.get('title', '未命名项目')}]({item.get('url', '')})",
                    f"   - 评分：{score:.1f}；{_item_growth_label(item)}；标签：{tags}；许可证：{license_name}",
                    f"   - 摘要：{(item.get('summary', '') or '暂无摘要')[:240]}",
                ]
            )
            risks = item.get("risk_flags") or []
            if risks:
                lines.append(f"   - 风险：{'；'.join(str(risk) for risk in risks)}")
    else:
        lines.append("- 今天还没有合格项目；等待下一次扫描。")
    lines.extend(["", "## 降本工具", ""])
    if cost_repos:
        for item in cost_repos:
            lines.append(f"- [{item.get('title', '')}]({item.get('url', '')})：{item.get('summary', '')[:160]}")
    else:
        lines.append("- 暂未发现新的明确降本工具。")
    lines.extend(["", "## Skill / 方法", ""])
    if method_repos:
        for item in method_repos:
            lines.append(f"- [{item.get('title', '')}]({item.get('url', '')})：{item.get('summary', '')[:160]}")
    else:
        lines.append("- 暂未发现新的高相关 Skill 或工作流。")
    lines.extend(["", "## 官方与行业动态", ""])
    if updates:
        for item in updates[:10]:
            lines.append(f"- [{item.get('title', '')}]({item.get('url', '')})：{item.get('summary', '')[:180]}")
    else:
        lines.append("- 暂无符合 AI 短剧/AI 视频相关性的官方更新。")
    lines.extend(["", "## 今日建议试用", ""])
    if top_repos:
        suggestion = top_repos[0]
        lines.extend(
            [
                f"建议先查看 [{suggestion.get('title', '')}]({suggestion.get('url', '')})。",
                "",
                "- 先确认许可证、依赖和是否需要付费 API。",
                "- 在隔离目录查看 README/SKILL.md，不直接运行来源不明的安装脚本。",
                "- 若需要付费模型，先估算单次试玩成本并设置上限。",
            ]
        )
    else:
        lines.append("- 暂无建议；等待更多快照后再判断。")
    lines.extend(["", "## 运行说明", "", "- 本报告不自动安装任何第三方 Skill，不登录平台，不调用付费生成 API。", ""])
    return "\n".join(lines)
OFFICIAL_FEEDS = (
    {"key": "openai-news", "name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
)

PAGE_WATCHERS = (
    {"key": "kling-release", "name": "Kling Release Notes", "url": "https://klingai.com/global/release-notes"},
    {"key": "runway-changelog", "name": "Runway Changelog", "url": "https://runway.com/changelog"},
    {"key": "minimax-news", "name": "MiniMax News", "url": "https://www.minimax.io/news"},
    {"key": "volcengine-ark", "name": "火山方舟产品页", "url": "https://www.volcengine.com/product/ark"},
)


def _readme_excerpt(text: str, limit: int = 420) -> str:
    clean = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    clean = re.sub(r"^\s{0,3}#{1,6}\s*", "", clean, flags=re.M)
    clean = re.sub(r"[*_>`~]+", " ", clean)
    clean = _plain_text(clean)
    return clean[:limit]


def build_repository_summary(description: str, readme: str, limit: int = 500) -> str:
    clean_description = _plain_text(description or "")
    if len(clean_description) >= 40:
        return clean_description[:limit]
    excerpt = _readme_excerpt(readme, limit=max(80, limit - len(clean_description) - 1))
    return "；".join(piece for piece in (clean_description, excerpt) if piece)[:limit]


async def fetch_repository_readme(client: httpx.AsyncClient, repo: dict[str, Any]) -> str:
    full_name = str(repo.get("full_name") or "")
    branch = str(repo.get("default_branch") or "main")
    if not full_name:
        return ""
    base = f"https://raw.githubusercontent.com/{full_name}/{branch}"
    chunks: list[str] = []
    try:
        response = await client.get(f"{base}/README.md")
        if response.status_code == 200:
            chunks.append(response.text[:30000])
    except Exception:
        pass
    skill_like = detect_repository_type(repo, "\n".join(chunks)) == "skill"
    if not chunks or skill_like:
        try:
            response = await client.get(f"{base}/SKILL.md")
            if response.status_code == 200:
                chunks.append(response.text[:30000])
        except Exception:
            pass
    return "\n\n".join(chunks)


async def _fetch_feed_updates(client: httpx.AsyncClient, errors: list[str]) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for feed in OFFICIAL_FEEDS:
        try:
            response = await client.get(feed["url"])
            response.raise_for_status()
            parsed = parse_feed(response.text, source_name=feed["name"])
            updates.extend(parsed)
            db.update_radar_source_state(
                feed["key"], source_name=feed["name"], source_type="rss",
                fingerprint=hashlib.sha256(response.content).hexdigest(),
                metadata={"url": feed["url"], "parsed": len(parsed)},
            )
        except Exception as exc:
            message = f"{feed['name']} 读取失败: {type(exc).__name__}: {exc}"
            errors.append(message)
            db.update_radar_source_state(
                feed["key"], source_name=feed["name"], source_type="rss",
                last_error=message, metadata={"url": feed["url"]},
            )
    return updates


async def _fetch_page_changes(client: httpx.AsyncClient, errors: list[str], now: datetime) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for watcher in PAGE_WATCHERS:
        try:
            response = await client.get(watcher["url"], follow_redirects=True)
            response.raise_for_status()
            fingerprint = page_content_fingerprint(response.text)
            previous = db.get_radar_source_state(watcher["key"])
            if previous and previous.get("fingerprint") and previous["fingerprint"] != fingerprint:
                updates.append(
                    {
                        "source_name": watcher["name"],
                        "external_id": f"{watcher['key']}:{fingerprint}",
                        "title": f"{watcher['name']} 页面有更新",
                        "url": watcher["url"],
                        "summary": "检测到官方页面内容变化。自动指纹只能确认“有变化”，请打开原始页面核对具体发布内容。",
                        "published_at": now.isoformat(),
                    }
                )
            db.update_radar_source_state(
                watcher["key"], source_name=watcher["name"], source_type="html",
                fingerprint=fingerprint, metadata={"url": watcher["url"]},
            )
        except Exception as exc:
            message = f"{watcher['name']} 读取失败: {type(exc).__name__}: {exc}"
            errors.append(message)
            db.update_radar_source_state(
                watcher["key"], source_name=watcher["name"], source_type="html",
                last_error=message, metadata={"url": watcher["url"]},
            )
    return updates


def _markdown_inline(text: str) -> str:
    escaped = html_lib.escape(text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', escaped)


def markdown_to_html(markdown_text: str, *, title: str) -> str:
    lines = markdown_text.splitlines()
    body: list[str] = []
    in_list = False
    for line in lines:
        if line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_markdown_inline(line[2:])}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if line.startswith("# "):
            body.append(f"<h1>{_markdown_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{_markdown_inline(line[3:])}</h2>")
        elif line.startswith("> "):
            body.append(f"<blockquote>{_markdown_inline(line[2:])}</blockquote>")
        elif re.match(r"^\d+\. ", line):
            body.append(f"<p class=\"ordered\">{_markdown_inline(line)}</p>")
        elif line.strip().startswith("- "):
            body.append(f"<p class=\"detail\">{_markdown_inline(line.strip()[2:])}</p>")
        elif line.strip():
            body.append(f"<p>{_markdown_inline(line)}</p>")
    if in_list:
        body.append("</ul>")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_lib.escape(title)}</title>
<style>
body{{margin:0;background:#0b0d12;color:#eef1f7;font-family:"Microsoft YaHei",system-ui,sans-serif;line-height:1.7}}
main{{max-width:900px;margin:0 auto;padding:40px 24px}}a{{color:#8da8ff}}h1,h2{{line-height:1.3}}h2{{margin-top:32px;border-bottom:1px solid #293141;padding-bottom:8px}}
blockquote{{margin:16px 0;padding:12px 16px;background:#151a24;border-left:3px solid #59d6b0;color:#b7c2d5}}.ordered,.detail{{margin:6px 0 6px 18px;color:#cbd3e1}}
</style></head><body><main>{''.join(body)}</main></body></html>"""


def write_daily_report(report_date: str, markdown_text: str) -> tuple[Path, Path]:
    reports = config.radar_reports_dir()
    reports.mkdir(parents=True, exist_ok=True)
    markdown_path = reports / f"{report_date}.md"
    html_path = reports / f"{report_date}.html"
    markdown_path.write_text(markdown_text, encoding="utf-8")
    html_path.write_text(
        markdown_to_html(markdown_text, title=f"AI 短剧情报日报 · {report_date}"),
        encoding="utf-8",
    )
    return markdown_path, html_path


def send_windows_notification(title: str, message: str) -> None:
    if os.name != "nt" or os.getenv("RADAR_DISABLE_NOTIFY") == "1":
        return
    script = config.PROJECT_ROOT / "radar_notify.ps1"
    if not script.is_file():
        return
    try:
        subprocess.Popen(
            [
                "powershell", "-NoProfile", "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass", "-File", str(script),
                "-Title", title, "-Message", message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return


def prune_old_updates(*, now: datetime | None = None, max_age_days: int = 45) -> int:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=max_age_days)
    removed = 0
    for item in db.list_radar_items(min_score=0, limit=500):
        if item.get("item_type") not in {"news", "update"}:
            continue
        published = _parse_dt(item.get("published_at"))
        if published and published < cutoff:
            db.delete_radar_item(int(item["id"]))
            removed += 1
    return removed


async def scan_now(
    *,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
    generate_report: bool = True,
    notify: bool = False,
) -> dict[str, Any]:
    local_now = (now or datetime.now().astimezone()).astimezone()
    now = local_now.astimezone(timezone.utc)
    config.ensure_dirs()
    db.init_db()
    run_id = db.start_radar_run()
    errors: list[str] = []
    new_item_ids: list[int] = []
    new_items = 0
    found = 0
    rate_limit: dict[str, Any] = {}
    own_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=True)
    try:
        repos, github_errors, rate_limit = await fetch_github_repositories(
            client, token=os.getenv("GITHUB_TOKEN", "")
        )
        errors.extend(github_errors)
        for repo in repos[:30]:
            full_name = str(repo.get("full_name") or "")
            if not is_relevant_repository(repo):
                continue
            readme = await fetch_repository_readme(client, repo)
            if is_blocked_repository(repo, readme):
                continue
            previous = db.nearest_radar_snapshot(full_name, now)
            scores = score_repository(repo, readme, previous, now)
            if not scores["relevant"]:
                continue
            existing = db.get_radar_item_by_external("repo", full_name)
            metrics = {
                "stars": int(repo.get("stargazers_count") or 0),
                "forks": int(repo.get("forks_count") or 0),
                "watchers": int(repo.get("subscribers_count") or 0),
                "open_issues": int(repo.get("open_issues_count") or 0),
                "pushed_at": str(repo.get("pushed_at") or ""),
            }
            db.add_radar_snapshot(full_name, now.isoformat(), metrics)
            license_info = repo.get("license") or {}
            license_name = license_info.get("spdx_id") or "" if isinstance(license_info, dict) else ""
            description = str(repo.get("description") or "").strip()
            summary = build_repository_summary(description, readme)
            item = db.upsert_radar_item(
                item_type="repo",
                source_name="GitHub",
                external_id=full_name,
                title=full_name,
                url=str(repo.get("html_url") or f"https://github.com/{full_name}"),
                summary=summary[:1000],
                published_at=str(repo.get("created_at") or ""),
                metrics=metrics,
                tags=scores["tags"],
                scores=scores,
                risk_flags=scores["risk_flags"],
                license_name=str(license_name),
            )
            found += 1
            if not existing:
                new_items += 1
                new_item_ids.append(int(item["id"]))

        official_updates = await _fetch_feed_updates(client, errors)
        official_updates.extend(await _fetch_page_changes(client, errors, now))
        prune_old_updates(now=now, max_age_days=45)
        for update in official_updates:
            item_type = "news" if update.get("source_name") == "OpenAI News" else "update"
            existing = db.get_radar_item_by_external(item_type, update["external_id"])
            item = db.upsert_radar_item(
                item_type=item_type,
                source_name=update["source_name"],
                external_id=update["external_id"],
                title=update["title"],
                url=update["url"],
                summary=update["summary"],
                published_at=update.get("published_at", ""),
                tags=["官方动态"],
                scores={"total_score": 0, "relevance_score": 20},
            )
            found += 1
            if not existing:
                new_items += 1
                new_item_ids.append(int(item["id"]))

        report_path = ""
        report_html_path = ""
        if generate_report:
            report_date = local_now.date().isoformat()
            all_items = db.list_radar_items(min_score=0, limit=500)
            repo_items = [item for item in all_items if item["item_type"] == "repo"]
            update_items = [item for item in all_items if item["item_type"] != "repo"]
            report = build_daily_report(report_date, repos=repo_items, updates=update_items)
            markdown_path, html_path = write_daily_report(report_date, report)
            report_path = str(markdown_path)
            report_html_path = str(html_path)

        if notify:
            priority = [
                db.get_radar_item(item_id) for item_id in new_item_ids
                if (db.get_radar_item(item_id) or {}).get("total_score", 0) >= 75
            ]
            priority = [item for item in priority if item]
            if priority:
                send_windows_notification(
                    "AI 短剧雷达有新发现",
                    f"发现 {len(priority)} 个 75 分以上新项目，可打开内容工厂查看。",
                )
                db.mark_radar_items_notified([int(item["id"]) for item in priority])

        status = "partial" if errors else "ok"
        db.finish_radar_run(
            run_id, status=status, items_found=found, new_items=new_items,
            errors=errors, rate_limit=rate_limit,
        )
        return {
            "run_id": run_id,
            "status": status,
            "items_found": found,
            "new_items": new_items,
            "errors": errors,
            "rate_limit": rate_limit,
            "report_path": report_path,
            "report_html_path": report_html_path,
        }
    except Exception as exc:
        errors.append(f"扫描失败: {type(exc).__name__}: {exc}")
        db.finish_radar_run(
            run_id, status="failed", items_found=found, new_items=new_items,
            errors=errors, rate_limit=rate_limit,
        )
        raise
    finally:
        if own_client and client is not None:
            await client.aclose()


@contextmanager
def scan_lock():
    config.ensure_dirs()
    lock_path = config.radar_data_dir() / "scan.lock"
    if lock_path.exists():
        remove_stale = False
        try:
            age = datetime.now(timezone.utc).timestamp() - lock_path.stat().st_mtime
            if age > 1800:
                remove_stale = True
            else:
                pid_text = lock_path.read_text(encoding="ascii").strip()
                if pid_text:
                    pid = int(pid_text)
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        remove_stale = True
                else:
                    remove_stale = True
        except (OSError, ValueError):
            remove_stale = True
        if remove_stale:
            try:
                lock_path.unlink()
            except OSError:
                pass
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("雷达扫描正在运行，请稍后重试") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass