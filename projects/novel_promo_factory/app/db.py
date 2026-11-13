from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from . import config


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL DEFAULT '',
                rights_status TEXT NOT NULL DEFAULT 'unconfirmed',
                template TEXT NOT NULL DEFAULT 'story_showreel',
                target_duration INTEGER NOT NULL DEFAULT 30,
                budget_limit_cny REAL NOT NULL DEFAULT 20,
                status TEXT NOT NULL DEFAULT 'draft',
                folder TEXT NOT NULL,
                script_json TEXT NOT NULL DEFAULT '{}',
                shots_json TEXT NOT NULL DEFAULT '[]',
                video_path TEXT NOT NULL DEFAULT '',
                package_dir TEXT NOT NULL DEFAULT '',
                estimated_cost_cny REAL NOT NULL DEFAULT 0,
                actual_cost_cny REAL NOT NULL DEFAULT 0,
                novel_id TEXT NOT NULL DEFAULT '',
                decision TEXT NOT NULL DEFAULT 'approved',
                rejection_reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                shot_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                provider TEXT NOT NULL,
                path TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                license TEXT NOT NULL DEFAULT '',
                downloaded_at TEXT NOT NULL,
                sha256 TEXT NOT NULL DEFAULT '',
                width INTEGER NOT NULL DEFAULT 0,
                height INTEGER NOT NULL DEFAULT 0,
                duration REAL NOT NULL DEFAULT 0,
                selected INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                task_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'estimated',
                prompt TEXT NOT NULL DEFAULT '',
                output_path TEXT NOT NULL DEFAULT '',
                estimated_cny REAL NOT NULL DEFAULT 0,
                actual_cny REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                caption TEXT NOT NULL DEFAULT '',
                video_path TEXT NOT NULL DEFAULT '',
                cover_path TEXT NOT NULL DEFAULT '',
                published_url TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                metrics_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'ready',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                platform TEXT NOT NULL DEFAULT '',
                nickname TEXT NOT NULL DEFAULT '',
                need_type TEXT NOT NULL DEFAULT '',
                budget_range TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'new',
                qualified INTEGER NOT NULL DEFAULT 0,
                next_action TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS novel_candidates (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL DEFAULT '',
                rights_status TEXT NOT NULL DEFAULT 'unconfirmed',
                source_url TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'available',
                used_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(conn, "projects", "novel_id", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "projects", "decision", "TEXT NOT NULL DEFAULT 'approved'")
        _ensure_column(conn, "projects", "rejection_reason", "TEXT NOT NULL DEFAULT ''")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS radar_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                discovered_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                metrics_json TEXT NOT NULL DEFAULT '{}',
                tags_json TEXT NOT NULL DEFAULT '[]',
                scores_json TEXT NOT NULL DEFAULT '{}',
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                license_name TEXT NOT NULL DEFAULT '',
                recommendation TEXT NOT NULL DEFAULT '',
                total_score REAL NOT NULL DEFAULT 0,
                relevance_score REAL NOT NULL DEFAULT 0,
                growth_score REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'unread',
                notified_at TEXT NOT NULL DEFAULT '',
                read_at TEXT NOT NULL DEFAULT '',
                UNIQUE(item_type, external_id)
            );

            CREATE TABLE IF NOT EXISTS radar_repo_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                stars INTEGER NOT NULL DEFAULT 0,
                forks INTEGER NOT NULL DEFAULT 0,
                watchers INTEGER NOT NULL DEFAULT 0,
                open_issues INTEGER NOT NULL DEFAULT 0,
                pushed_at TEXT NOT NULL DEFAULT '',
                UNIQUE(full_name, captured_at)
            );

            CREATE TABLE IF NOT EXISTS radar_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'running',
                items_found INTEGER NOT NULL DEFAULT 0,
                new_items INTEGER NOT NULL DEFAULT 0,
                errors_json TEXT NOT NULL DEFAULT '[]',
                rate_limit_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS radar_source_state (
                source_key TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                last_checked_at TEXT NOT NULL DEFAULT '',
                fingerprint TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_radar_items_score ON radar_items(total_score DESC);
            CREATE INDEX IF NOT EXISTS idx_radar_items_status ON radar_items(status);
            CREATE INDEX IF NOT EXISTS idx_radar_snapshots_repo ON radar_repo_snapshots(full_name, captured_at DESC);
            """
        )


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("script_json", "shots_json", "metrics_json", "metadata_json", "tags_json", "scores_json", "risk_flags_json"):
        if key in result and isinstance(result[key], str):
            try:
                result[key.removesuffix("_json")] = json.loads(result[key])
            except json.JSONDecodeError:
                result[key.removesuffix("_json")] = [] if key in {"shots_json", "tags_json", "risk_flags_json"} else {}
    return result


def create_project(
    title: str,
    genre: str,
    source_text: str,
    rights_status: str = "unconfirmed",
    template: str = "story_showreel",
    target_duration: int = 30,
    budget_limit_cny: float = 20,
    novel_id: str = "",
    decision: str = "approved",
    status: str = "draft",
) -> dict[str, Any]:
    project_id = uuid.uuid4().hex[:12]
    folder = config.content_dir() / project_id
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO projects (id,title,genre,source_text,rights_status,template,target_duration,budget_limit_cny,status,folder,novel_id,decision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (project_id, title.strip(), genre.strip(), source_text.strip(), rights_status, template, target_duration, budget_limit_cny, status, str(folder), novel_id, decision, stamp, stamp),
        )
    return get_project(project_id) or {}


def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return [_dict(row) for row in rows if row is not None]


def get_project(project_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    project = _dict(row)
    if project:
        project["assets"] = list_assets(project_id)
        project["posts"] = list_posts(project_id)
        project["costs"] = list_costs(project_id)
    return project


def update_project(project_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "title", "genre", "source_text", "rights_status", "template",
        "target_duration", "budget_limit_cny", "status", "script", "shots",
        "video_path", "package_dir", "estimated_cost_cny", "actual_cost_cny",
        "novel_id", "decision", "rejection_reason",
    }
    values: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "script":
            values["script_json"] = json.dumps(value, ensure_ascii=False)
        elif key == "shots":
            values["shots_json"] = json.dumps(value, ensure_ascii=False)
        else:
            values[key] = value
    if values:
        values["updated_at"] = now_iso()
        assignments = ", ".join(f"{key}=?" for key in values)
        with connect() as conn:
            conn.execute(f"UPDATE projects SET {assignments} WHERE id=?", (*values.values(), project_id))
    return get_project(project_id)


def add_asset(project_id: str, shot_id: str, kind: str, provider: str, path: str, **metadata: Any) -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO assets (project_id,shot_id,kind,provider,path,source_url,author,license,downloaded_at,sha256,width,height,duration,selected,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                project_id, shot_id, kind, provider, str(Path(path).resolve()),
                metadata.get("source_url", ""), metadata.get("author", ""), metadata.get("license", ""),
                metadata.get("downloaded_at") or now_iso(), metadata.get("sha256", ""),
                int(metadata.get("width", 0)), int(metadata.get("height", 0)), float(metadata.get("duration", 0)),
                1 if metadata.get("selected") else 0, json.dumps(metadata, ensure_ascii=False),
            ),
        )
        return int(cursor.lastrowid)


def list_assets(project_id: str, shot_id: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM assets WHERE project_id=?"
    args: list[Any] = [project_id]
    if shot_id:
        query += " AND shot_id=?"
        args.append(shot_id)
    query += " ORDER BY selected DESC, id ASC"
    with connect() as conn:
        rows = conn.execute(query, args).fetchall()
    return [_dict(row) for row in rows if row is not None]


def select_asset(project_id: str, shot_id: str, asset_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE assets SET selected=0 WHERE project_id=? AND shot_id=?", (project_id, shot_id))
        conn.execute("UPDATE assets SET selected=1 WHERE id=? AND project_id=?", (asset_id, project_id))


def add_cost(project_id: str, kind: str, provider: str, **data: Any) -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO costs (project_id,kind,provider,model,task_id,status,prompt,output_path,estimated_cny,actual_cny,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                project_id, kind, provider, data.get("model", ""), data.get("task_id", ""),
                data.get("status", "estimated"), data.get("prompt", ""), data.get("output_path", ""),
                float(data.get("estimated_cny", 0)), float(data.get("actual_cny", 0)), now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def list_costs(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM costs WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
    return [_dict(row) for row in rows if row is not None]


def month_spend() -> float:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    with connect() as conn:
        row = conn.execute("SELECT COALESCE(SUM(actual_cny),0) AS total FROM costs WHERE actual_cny>0 AND substr(created_at,1,7)=?", (month,)).fetchone()
    return float(row["total"] if row else 0)


def create_post(project_id: str, platform: str, title: str, caption: str, video_path: str = "", cover_path: str = "") -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO posts (project_id,platform,title,caption,video_path,cover_path,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (project_id, platform, title, caption, video_path, cover_path, "ready", now_iso()),
        )
        return int(cursor.lastrowid)


def list_posts(project_id: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM posts WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return [_dict(row) for row in rows if row is not None]


def mark_published(post_id: int, published_url: str, metrics: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        conn.execute(
            "UPDATE posts SET published_url=?, published_at=?, metrics_json=?, status='published' WHERE id=?",
            (published_url, now_iso(), json.dumps(metrics or {}, ensure_ascii=False), post_id),
        )
        row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    return _dict(row)


def add_lead(**data: Any) -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO leads (post_id,platform,nickname,need_type,budget_range,stage,qualified,next_action,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                data.get("post_id"), data.get("platform", ""), data.get("nickname", ""), data.get("need_type", ""),
                data.get("budget_range", ""), data.get("stage", "new"), 1 if data.get("qualified") else 0,
                data.get("next_action", ""), data.get("notes", ""), now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def list_leads() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [_dict(row) for row in rows if row is not None]


def add_novel_candidate(
    title: str,
    genre: str,
    source_text: str,
    rights_status: str = "unconfirmed",
    source_url: str = "",
    tags: str = "",
    priority: int = 0,
) -> dict[str, Any]:
    candidate_id = uuid.uuid4().hex[:12]
    stamp = now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO novel_candidates (id,title,genre,source_text,rights_status,source_url,tags,priority,status,used_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (candidate_id, title.strip(), genre.strip(), source_text.strip(), rights_status, source_url.strip(), tags.strip(), int(priority), "available", 0, stamp, stamp),
        )
    return get_novel_candidate(candidate_id) or {}


def get_novel_candidate(candidate_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM novel_candidates WHERE id=?", (candidate_id,)).fetchone()
    return _dict(row)


def list_novel_candidates(status: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM novel_candidates WHERE status=? ORDER BY priority DESC, id ASC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM novel_candidates ORDER BY status ASC, priority DESC, id ASC").fetchall()
    return [_dict(row) for row in rows if row is not None]


def update_novel_candidate(candidate_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {"title", "genre", "source_text", "rights_status", "source_url", "tags", "priority", "status", "used_count"}
    values = {key: value for key, value in fields.items() if key in allowed}
    if values:
        values["updated_at"] = now_iso()
        assignments = ", ".join(f"{key}=?" for key in values)
        with connect() as conn:
            conn.execute(f"UPDATE novel_candidates SET {assignments} WHERE id=?", (*values.values(), candidate_id))
    return get_novel_candidate(candidate_id)


def select_next_novel_candidate(*, genre: str = "", keywords: str = "") -> dict[str, Any] | None:
    candidates = [item for item in list_novel_candidates("available") if item.get("rights_status") in {"owned", "authorized"}]
    if not candidates:
        return None
    genre = genre.strip()
    keyword_list = [piece.strip().lower() for piece in keywords.replace("，", ",").split(",") if piece.strip()]

    def score(item: dict[str, Any]) -> int:
        value = int(item.get("priority") or 0) * 10 - int(item.get("used_count") or 0) * 20
        if genre and item.get("genre") == genre:
            value += 100
        haystack = f"{item.get('title', '')} {item.get('genre', '')} {item.get('tags', '')} {item.get('source_text', '')}".lower()
        value += sum(25 for keyword in keyword_list if keyword in haystack)
        return value

    return max(candidates, key=score)


def dashboard() -> dict[str, Any]:
    with connect() as conn:
        projects = conn.execute("SELECT COUNT(*) AS n FROM projects").fetchone()["n"]
        posts = conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
        published = conn.execute("SELECT COUNT(*) AS n FROM posts WHERE status='published'").fetchone()["n"]
        leads = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        qualified = conn.execute("SELECT COUNT(*) AS n FROM leads WHERE qualified=1").fetchone()["n"]
        novels = conn.execute("SELECT COUNT(*) AS n FROM novel_candidates WHERE status='available'").fetchone()["n"]
    return {
        "projects": projects,
        "available_novels": novels,
        "posts": posts,
        "published": published,
        "leads": leads,
        "qualified_leads": qualified,
        "month_spend_cny": month_spend(),
    }


def upsert_radar_item(
    *,
    item_type: str,
    source_name: str,
    external_id: str,
    title: str,
    url: str,
    summary: str = "",
    published_at: str = "",
    metrics: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    scores: dict[str, Any] | None = None,
    risk_flags: list[str] | None = None,
    license_name: str = "",
) -> dict[str, Any]:
    stamp = now_iso()
    metrics = metrics or {}
    tags = tags or []
    scores = scores or {}
    risk_flags = risk_flags or []
    total_score = float(scores.get("total_score", scores.get("total", 0)) or 0)
    relevance_score = float(scores.get("relevance_score", 0) or 0)
    growth_score = float(scores.get("growth_score", 0) or 0)
    recommendation = str(scores.get("recommendation", "") or "")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO radar_items (
                item_type,source_name,external_id,title,url,summary,published_at,
                discovered_at,last_seen_at,metrics_json,tags_json,scores_json,
                risk_flags_json,license_name,recommendation,total_score,
                relevance_score,growth_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(item_type, external_id) DO UPDATE SET
                source_name=excluded.source_name,
                title=excluded.title,
                url=excluded.url,
                summary=excluded.summary,
                published_at=excluded.published_at,
                last_seen_at=excluded.last_seen_at,
                metrics_json=excluded.metrics_json,
                tags_json=excluded.tags_json,
                scores_json=excluded.scores_json,
                risk_flags_json=excluded.risk_flags_json,
                license_name=excluded.license_name,
                recommendation=excluded.recommendation,
                total_score=excluded.total_score,
                relevance_score=excluded.relevance_score,
                growth_score=excluded.growth_score
            """,
            (
                item_type, source_name, external_id, title, url, summary, published_at,
                stamp, stamp, json.dumps(metrics, ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False), json.dumps(scores, ensure_ascii=False),
                json.dumps(risk_flags, ensure_ascii=False), license_name,
                recommendation, total_score, relevance_score, growth_score,
            ),
        )
        row = conn.execute(
            "SELECT * FROM radar_items WHERE item_type=? AND external_id=?",
            (item_type, external_id),
        ).fetchone()
    return _dict(row) or {}


def get_radar_item(item_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM radar_items WHERE id=?", (item_id,)).fetchone()
    return _dict(row)


def list_radar_items(
    *,
    status: str | None = None,
    item_type: str | None = None,
    min_score: float = 0,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses = ["total_score>=?"]
    args: list[Any] = [float(min_score)]
    if status:
        clauses.append("status=?")
        args.append(status)
    if item_type:
        clauses.append("item_type=?")
        args.append(item_type)
    args.append(max(1, min(500, int(limit))))
    query = (
        "SELECT * FROM radar_items WHERE "
        + " AND ".join(clauses)
        + " ORDER BY total_score DESC, last_seen_at DESC LIMIT ?"
    )
    with connect() as conn:
        rows = conn.execute(query, args).fetchall()
    return [_dict(row) for row in rows if row is not None]


def update_radar_item_status(item_id: int, status: str) -> dict[str, Any] | None:
    if status not in {"unread", "saved", "trying", "tried", "ignored"}:
        raise ValueError("无效的雷达项目状态")
    read_at = "" if status == "unread" else now_iso()
    with connect() as conn:
        conn.execute("UPDATE radar_items SET status=?, read_at=? WHERE id=?", (status, read_at, item_id))
    return get_radar_item(item_id)


def mark_radar_items_notified(item_ids: list[int]) -> None:
    if not item_ids:
        return
    placeholders = ",".join("?" for _ in item_ids)
    with connect() as conn:
        conn.execute(
            f"UPDATE radar_items SET notified_at=? WHERE id IN ({placeholders})",
            (now_iso(), *item_ids),
        )


def list_unnotified_priority_items(min_score: float = 75) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM radar_items WHERE total_score>=? AND notified_at='' AND status!='ignored' ORDER BY total_score DESC",
            (float(min_score),),
        ).fetchall()
    return [_dict(row) for row in rows if row is not None]


def add_radar_snapshot(full_name: str, captured_at: str, metrics: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO radar_repo_snapshots (full_name,captured_at,stars,forks,watchers,open_issues,pushed_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(full_name, captured_at) DO UPDATE SET
                stars=excluded.stars, forks=excluded.forks, watchers=excluded.watchers,
                open_issues=excluded.open_issues, pushed_at=excluded.pushed_at
            """,
            (
                full_name,
                captured_at,
                int(metrics.get("stars") or 0),
                int(metrics.get("forks") or 0),
                int(metrics.get("watchers") or 0),
                int(metrics.get("open_issues") or 0),
                str(metrics.get("pushed_at") or ""),
            ),
        )


def nearest_radar_snapshot(
    full_name: str,
    target: datetime,
    *,
    min_hours: float = 12,
    max_hours: float = 36,
) -> dict[str, Any] | None:
    start = (target - timedelta(hours=max_hours)).isoformat()
    end = (target - timedelta(hours=min_hours)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM radar_repo_snapshots WHERE full_name=? AND captured_at BETWEEN ? AND ?",
            (full_name, start, end),
        ).fetchall()
    candidates = [_dict(row) for row in rows if row is not None]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: abs(
            (target - datetime.fromisoformat(str(item["captured_at"]))).total_seconds()
        ),
    )


def start_radar_run() -> int:
    stamp = now_iso()
    with connect() as conn:
        conn.execute(
            "UPDATE radar_runs SET status='interrupted', completed_at=? WHERE status='running'",
            (stamp,),
        )
        cursor = conn.execute("INSERT INTO radar_runs (started_at,status) VALUES (?,?)", (stamp, "running"))
        return int(cursor.lastrowid)


def finish_radar_run(
    run_id: int,
    *,
    status: str,
    items_found: int,
    new_items: int,
    errors: list[str] | None = None,
    rate_limit: dict[str, Any] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE radar_runs SET completed_at=?,status=?,items_found=?,new_items=?,errors_json=?,rate_limit_json=? WHERE id=?",
            (
                now_iso(), status, int(items_found), int(new_items),
                json.dumps(errors or [], ensure_ascii=False),
                json.dumps(rate_limit or {}, ensure_ascii=False), run_id,
            ),
        )


def latest_radar_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM radar_runs ORDER BY id DESC LIMIT 1").fetchone()
    return _dict(row)


def get_radar_source_state(source_key: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM radar_source_state WHERE source_key=?", (source_key,)).fetchone()
    return _dict(row)


def update_radar_source_state(
    source_key: str,
    *,
    source_name: str,
    source_type: str,
    fingerprint: str = "",
    last_error: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO radar_source_state (source_key,source_name,source_type,last_checked_at,fingerprint,last_error,metadata_json)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(source_key) DO UPDATE SET
                source_name=excluded.source_name, source_type=excluded.source_type,
                last_checked_at=excluded.last_checked_at, fingerprint=excluded.fingerprint,
                last_error=excluded.last_error, metadata_json=excluded.metadata_json
            """,
            (
                source_key, source_name, source_type, now_iso(), fingerprint,
                last_error, json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )


def radar_dashboard() -> dict[str, Any]:
    local_now = datetime.now().astimezone()
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
    utc_start = local_start.astimezone(timezone.utc).isoformat()
    utc_end = (local_start + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    with connect() as conn:
        unread = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE status='unread'").fetchone()["n"]
        priority = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE total_score>=75 AND status!='ignored'").fetchone()["n"]
        new_today = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE discovered_at>=? AND discovered_at<?", (utc_start, utc_end)).fetchone()["n"]
        repos = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE item_type='repo'").fetchone()["n"]
        updates = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE item_type!='repo'").fetchone()["n"]
        trying = conn.execute("SELECT COUNT(*) AS n FROM radar_items WHERE status='trying'").fetchone()["n"]
    return {
        "unread": unread,
        "priority": priority,
        "new_today": new_today,
        "repos": repos,
        "updates": updates,
        "trying": trying,
        "latest_run": latest_radar_run(),
    }


def get_radar_item_by_external(item_type: str, external_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM radar_items WHERE item_type=? AND external_id=?",
            (item_type, external_id),
        ).fetchone()
    return _dict(row)


def delete_radar_item(item_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM radar_items WHERE id=?", (item_id,))
