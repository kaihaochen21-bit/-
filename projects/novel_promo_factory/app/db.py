from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
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
            """
        )


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("script_json", "shots_json", "metrics_json", "metadata_json"):
        if key in result and isinstance(result[key], str):
            try:
                result[key.removesuffix("_json")] = json.loads(result[key])
            except json.JSONDecodeError:
                result[key.removesuffix("_json")] = {} if key != "shots_json" else []
    return result


def create_project(
    title: str,
    genre: str,
    source_text: str,
    rights_status: str = "unconfirmed",
    template: str = "story_showreel",
    target_duration: int = 30,
    budget_limit_cny: float = 20,
) -> dict[str, Any]:
    project_id = uuid.uuid4().hex[:12]
    folder = config.content_dir() / project_id
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO projects (id,title,genre,source_text,rights_status,template,target_duration,budget_limit_cny,status,folder,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (project_id, title.strip(), genre.strip(), source_text.strip(), rights_status, template, target_duration, budget_limit_cny, "draft", str(folder), stamp, stamp),
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


def dashboard() -> dict[str, Any]:
    with connect() as conn:
        projects = conn.execute("SELECT COUNT(*) AS n FROM projects").fetchone()["n"]
        posts = conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
        published = conn.execute("SELECT COUNT(*) AS n FROM posts WHERE status='published'").fetchone()["n"]
        leads = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        qualified = conn.execute("SELECT COUNT(*) AS n FROM leads WHERE qualified=1").fetchone()["n"]
    return {
        "projects": projects,
        "posts": posts,
        "published": published,
        "leads": leads,
        "qualified_leads": qualified,
        "month_spend_cny": month_spend(),
    }
