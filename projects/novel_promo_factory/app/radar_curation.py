from __future__ import annotations

import re
import shutil
import stat
import subprocess
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config, db


ALLOWED_LICENSES = {
    "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "CC0-1.0", "ISC", "MPL-2.0", "AGPL-3.0", "GPL-3.0",
}
TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv",
}
ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
}
EXECUTABLE_EXTENSIONS = {
    ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".ps1", ".bat", ".cmd",
    ".sh", ".bash", ".zsh", ".exe", ".dll", ".jar", ".msi", ".bin", ".com",
    ".vbs", ".rb", ".pl", ".php", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
}
SUSPICIOUS_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"exfiltrat",
    r"upload\s+.*\.env",
    r"webhook\s+https?://",
    r"rm\s+-rf\s+/(?:\s|$)",
    r"format\s+[a-z]:",
)
TYPE_PRIORITY = {"skill": 8, "prompt": 7, "workflow": 6, "platform": 5, "asset-tool": 4, "awesome": 1}


def _local_today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _install_date(value: Any) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed.astimezone().date().isoformat()
    except ValueError:
        return ""


def _repo_type(item: dict[str, Any]) -> str:
    scores = item.get("scores") or {}
    value = str(scores.get("repo_type") or "")
    if value:
        return value
    known = {"skill", "prompt", "workflow", "platform", "awesome", "asset-tool"}
    for tag in item.get("tags") or []:
        if tag in known:
            return str(tag)
    return "other"


def is_skill_candidate(item: dict[str, Any]) -> bool:
    if item.get("item_type") != "repo" or _repo_type(item) == "awesome":
        return False
    if _repo_type(item) in {"skill", "prompt"}:
        return True
    return any(str(tag).lower() == "skill" for tag in (item.get("tags") or []))


def _reason_for_item(item: dict[str, Any]) -> str:
    scores = item.get("scores") or {}
    tags = {str(tag) for tag in item.get("tags") or []}
    reasons: list[str] = []
    if float(item.get("total_score") or 0) >= 75:
        reasons.append("高分优先")
    delta = scores.get("star_delta_24h")
    if delta is not None and float(delta) > 0:
        reasons.append(f"24h Star +{int(delta)}")
    if tags & {"开源", "本地部署", "免费"}:
        reasons.append("降本潜力")
    if "Skill" in tags or _repo_type(item) in {"skill", "prompt"}:
        reasons.append("可自动评估 Skill")
    if _repo_type(item) in {"workflow", "platform"}:
        reasons.append("可直接借鉴的工作流")
    return "；".join(reasons[:3]) or "高相关候选"


def select_daily_shortlist(items: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    eligible = [
        item for item in items
        if item.get("item_type") == "repo"
        and item.get("status") != "ignored"
        and float(item.get("total_score") or 0) >= 60
        and (item.get("scores") or {}).get("relevant", True)
    ]
    eligible.sort(
        key=lambda item: (
            float(item.get("total_score") or 0),
            TYPE_PRIORITY.get(_repo_type(item), 0),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    used_types: set[str] = set()
    for item in eligible:
        repo_type = _repo_type(item)
        if repo_type in used_types:
            continue
        selected.append(item)
        used_types.add(repo_type)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        selected_ids = {int(item["id"]) for item in selected}
        for item in eligible:
            if int(item["id"]) in selected_ids:
                continue
            selected.append(item)
            if len(selected) >= limit:
                break
    result: list[dict[str, Any]] = []
    for item in selected[:limit]:
        copy = dict(item)
        copy["curation_reason"] = _reason_for_item(item)
        result.append(copy)
    return result


def _read_frontmatter_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8", errors="replace")[:4000]
    match = re.search(r"(?m)^name:\s*[\"']?([a-z0-9][a-z0-9-]*)[\"']?\s*$", text)
    return match.group(1) if match else ""


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or f"radar-skill-{uuid.uuid4().hex[:8]}"


def assess_skill_source(
    source_root: Path,
    *,
    repo: dict[str, Any],
    license_name: str,
    total_score: float,
) -> dict[str, Any]:
    full_name = str(repo.get("full_name") or repo.get("title") or "unknown/repo")
    skill_file = source_root / "SKILL.md"
    base = {
        "status": "blocked",
        "reason": "",
        "skill_name": "",
        "files_count": 0,
        "source_commit": "",
        "executable_files": [],
        "suspicious_files": [],
    }
    if license_name not in ALLOWED_LICENSES:
        base["reason"] = f"许可证 {license_name or '未明确'} 不在自动安装白名单"
        return base
    if float(total_score) < 70:
        base["reason"] = "项目评分低于 70，未达到自动安装阈值"
        return base
    if not skill_file.is_file():
        base["reason"] = "仓库根目录没有 SKILL.md，不符合 Skill 自动安装结构"
        return base
    skill_name = safe_slug(_read_frontmatter_name(skill_file) or full_name.split("/")[-1])
    executable_files: list[str] = []
    suspicious_files: list[str] = []
    files_count = 0
    total_bytes = 0
    for path in source_root.rglob("*"):
        if path.is_symlink():
            base["reason"] = "检测到符号链接，禁止自动安装"
            return base
        if not path.is_file() or ".git" in path.parts:
            continue
        files_count += 1
        total_bytes += path.stat().st_size
        if files_count > 250 or total_bytes > 10 * 1024 * 1024:
            base["reason"] = "文件数量或体积超过自动安装上限"
            return base
        suffix = path.suffix.lower()
        if path.name in {"LICENSE", "NOTICE", "COPYING", ".gitignore"}:
            continue
        if suffix in EXECUTABLE_EXTENSIONS:
            executable_files.append(str(path.relative_to(source_root)).replace("\\", "/"))
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            if any(re.search(pattern, lower, flags=re.I | re.S) for pattern in SUSPICIOUS_PATTERNS):
                suspicious_files.append(str(path.relative_to(source_root)).replace("\\", "/"))
            continue
        if suffix not in TEXT_EXTENSIONS | ASSET_EXTENSIONS:
            executable_files.append(str(path.relative_to(source_root)).replace("\\", "/"))
            continue
        if suffix in TEXT_EXTENSIONS:
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            if any(re.search(pattern, lower, flags=re.I | re.S) for pattern in SUSPICIOUS_PATTERNS):
                suspicious_files.append(str(path.relative_to(source_root)).replace("\\", "/"))
    base.update(
        {
            "skill_name": skill_name,
            "files_count": files_count,
            "executable_files": executable_files,
            "suspicious_files": suspicious_files,
        }
    )
    if suspicious_files:
        base["reason"] = "检测到可能的敏感数据外传或危险命令模式"
        return base
    if executable_files:
        base["status"] = "auto_install"
        base["reason"] = f"包含 {len(executable_files)} 个脚本或辅助文件，静态危险模式检查通过；自动安装但不执行"
        return base
    base["status"] = "auto_install"
    base["reason"] = "纯文本 Skill，许可证、文件类型和内容检查通过"
    return base


def _copy_safe_tree(source_root: Path, target: Path) -> int:
    copied = 0
    for path in source_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.is_symlink():
            continue
        suffix = path.suffix.lower()
        if suffix not in TEXT_EXTENSIONS | ASSET_EXTENSIONS and path.name not in {"LICENSE", "NOTICE"}:
            continue
        relative = path.relative_to(source_root)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied += 1
    return copied


def _copy_full_tree(source_root: Path, target: Path) -> int:
    copied = 0
    for path in source_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.is_symlink():
            continue
        relative = path.relative_to(source_root)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied += 1
    return copied


def install_skill_directory(
    source_root: Path,
    skills_root: Path,
    skill_name: str,
    *,
    include_scripts: bool = False,
) -> dict[str, Any]:
    skills_root.mkdir(parents=True, exist_ok=True)
    target = skills_root / safe_slug(skill_name)
    if target.exists():
        return {"status": "collision", "path": str(target), "reason": "同名 Skill 已存在，未覆盖"}
    temporary = skills_root / f".radar-install-{uuid.uuid4().hex}"
    try:
        files_count = _copy_full_tree(source_root, temporary) if include_scripts else _copy_safe_tree(source_root, temporary)
        if not (temporary / "SKILL.md").is_file():
            raise ValueError("复制后缺少 SKILL.md")
        if include_scripts:
            (temporary / "RADAR_INSTALL_NOTICE.md").write_text(
                "# 雷达自动安装说明\n\n"
                "- 本项目由 AI 短剧情报雷达自动安装。\n"
                "- 安装过程只复制文件，未执行仓库脚本。\n"
                "- Skill 被调用时如需运行脚本，请先检查来源、依赖和权限。\n",
                encoding="utf-8",
            )
        temporary.replace(target)
        return {"status": "installed", "path": str(target), "files_count": files_count, "reason": "已通过静态审查并安装"}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

def quarantine_skill_directory(
    source_root: Path,
    quarantine_root: Path,
    repo_full_name: str,
    assessment: dict[str, Any],
) -> dict[str, Any]:
    quarantine_root.mkdir(parents=True, exist_ok=True)
    target = quarantine_root / safe_slug(repo_full_name) / uuid.uuid4().hex[:8]
    if target.exists():
        return {"status": "collision", "path": str(target), "reason": "隔离目录已存在"}
    shutil.copytree(source_root, target, ignore=shutil.ignore_patterns(".git"))
    review = (
        "# 雷达自动隔离说明\n\n"
        f"- 仓库：{repo_full_name}\n"
        f"- 状态：{assessment.get('status')}\n"
        f"- 原因：{assessment.get('reason')}\n"
        f"- 可执行文件：{', '.join(assessment.get('executable_files') or []) or '无'}\n"
        "- 本目录不会自动注册为 Codex Skill，也未执行其中任何脚本。\n"
    )
    (target / "RADAR_REVIEW.md").write_text(review, encoding="utf-8")
    return {"status": "quarantined", "path": str(target), "files_count": assessment.get("files_count", 0), "reason": assessment.get("reason", "")}


def extract_repository_zip(archive_path: Path, target_root: Path) -> Path:
    target_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > 250:
            raise ValueError("ZIP 文件数量超过自动安装上限")
        if sum(max(0, member.file_size) for member in members) > 25 * 1024 * 1024:
            raise ValueError("ZIP 解压后体积超过 25MB 自动安装上限")
        extracted_bytes = 0
        for member in members:
            mode = (member.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ValueError(f"ZIP 包含不允许的符号链接：{member.filename}")
            name = member.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"ZIP 包含不安全路径：{member.filename}")
            destination = target_root.joinpath(*path.parts)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    extracted_bytes += len(chunk)
                    if extracted_bytes > 25 * 1024 * 1024:
                        raise ValueError("ZIP 实际解压体积超过 25MB 自动安装上限")
                    output.write(chunk)
    children = [item for item in target_root.iterdir() if item.is_dir()]
    if len(children) == 1:
        return children[0]
    return target_root


def materialize_repository(repo: dict[str, Any], target_root: Path) -> Path:
    full_name = str(repo.get("title") or repo.get("full_name") or "")
    if not full_name or "/" not in full_name:
        raise ValueError("缺少 GitHub 仓库名")
    target_root.mkdir(parents=True, exist_ok=True)
    archive_path = target_root / "repository.zip"
    request = Request(
        f"https://codeload.github.com/{full_name}/zip/HEAD",
        headers={"User-Agent": "AI-Short-Drama-Radar/1.0"},
    )
    max_bytes = 25 * 1024 * 1024
    total = 0
    try:
        with urlopen(request, timeout=90) as response, archive_path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("仓库归档超过 25MB 自动安装上限")
                handle.write(chunk)
    except Exception as exc:
        raise RuntimeError(f"GitHub 归档下载失败：{type(exc).__name__}: {exc}") from exc
    return extract_repository_zip(archive_path, target_root / "repo")

def _git_commit(source_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def select_install_candidates(items: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    eligible = [
        item for item in items
        if item.get("status") != "ignored"
        and float(item.get("total_score") or 0) >= 70
        and is_skill_candidate(item)
    ]
    eligible.sort(
        key=lambda item: (
            float(item.get("total_score") or 0),
            TYPE_PRIORITY.get(_repo_type(item), 0),
        ),
        reverse=True,
    )
    return eligible[:limit]


def repository_has_root_skill(repo: dict[str, Any]) -> bool:
    full_name = str(repo.get("title") or repo.get("full_name") or "")
    if not full_name or "/" not in full_name:
        return False
    request = Request(
        f"https://raw.githubusercontent.com/{full_name}/HEAD/SKILL.md",
        headers={"User-Agent": "AI-Short-Drama-Radar/1.0"},
        method="HEAD",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return int(getattr(response, "status", 0)) == 200
    except HTTPError as exc:
        return exc.code != 404 and False
    except (URLError, TimeoutError, OSError):
        return False


def _attempt_skill_item(
    item: dict[str, Any],
    materialize_fn: Callable[[dict[str, Any], Path], Path],
    root_skill_checker: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    if not root_skill_checker(item):
        return {
            "item_id": int(item["id"]),
            "status": "not_installable",
            "path": "",
            "detail": "不是根目录 Skill 包，建议直接打开使用",
        }
    existing = db.get_radar_install_by_repo(str(item.get("title") or ""))
    if existing and existing.get("status") == "installed":
        return {
            "item_id": int(item["id"]),
            "status": "already_installed",
            "path": str(existing.get("install_path") or ""),
            "detail": "该仓库已有自动安装记录",
        }
    try:
        with tempfile.TemporaryDirectory(prefix="radar-curate-") as temp:
            source = materialize_fn(item, Path(temp))
            assessment = assess_skill_source(
                source,
                repo=item,
                license_name=str(item.get("license_name") or ""),
                total_score=float(item.get("total_score") or 0),
            )
            if assessment["status"] == "auto_install":
                result = install_skill_directory(
                    source,
                    config.codex_skills_dir(),
                    assessment["skill_name"],
                    include_scripts=bool(assessment.get("executable_files")),
                )
                detail = f"{result['reason']}；{assessment['reason']}"
            elif assessment["status"] == "quarantine":
                result = quarantine_skill_directory(
                    source,
                    config.radar_quarantine_dir(),
                    str(item.get("title") or ""),
                    assessment,
                )
                detail = result["reason"]
            else:
                return {
                    "item_id": int(item["id"]),
                    "status": "blocked",
                    "path": "",
                    "detail": assessment["reason"],
                }
            db.record_radar_install(
                item_id=int(item["id"]),
                repo_full_name=str(item.get("title") or ""),
                skill_name=assessment["skill_name"],
                install_path=str(result.get("path") or ""),
                source_commit=_git_commit(source),
                license_name=str(item.get("license_name") or ""),
                status=str(result["status"]),
                files_count=int(result.get("files_count") or 0),
                detail=detail,
            )
            return {
                "item_id": int(item["id"]),
                "status": str(result["status"]),
                "path": str(result.get("path") or ""),
                "detail": detail,
            }
    except Exception as exc:
        return {
            "item_id": int(item["id"]),
            "status": "failed",
            "path": "",
            "detail": f"自动处理失败：{type(exc).__name__}: {exc}",
        }


def auto_curate(
    *,
    date: str | None = None,
    auto_install: bool = True,
    materialize_fn: Callable[[dict[str, Any], Path], Path] | None = None,
    root_skill_checker: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    date = date or _local_today()
    items = db.list_radar_items(min_score=0, limit=500)
    shortlist = select_daily_shortlist(items, limit=3)
    materialize_fn = materialize_fn or materialize_repository
    root_skill_checker = root_skill_checker or repository_has_root_skill
    install_budget = 1
    today_installs = [
        record for record in db.list_radar_installs(limit=500)
        if record.get("status") == "installed"
        and _install_date(record.get("installed_at")) == date
    ]
    if today_installs:
        install_budget = 0
    processed: dict[int, dict[str, Any]] = {}
    install_results: list[dict[str, Any]] = []

    if auto_install:
        candidates = select_install_candidates(items, limit=6)
        for candidate in candidates:
            existing = db.get_radar_install_by_repo(str(candidate.get("title") or ""))
            installed_at = str((existing or {}).get("installed_at") or "")
            if existing and existing.get("status") == "installed" and installed_at.startswith(date):
                processed[int(candidate["id"])] = {
                    "item_id": int(candidate["id"]),
                    "status": "already_installed",
                    "path": str(existing.get("install_path") or ""),
                    "detail": "今天已自动安装该 Skill",
                }
                install_budget = 0
                break
        for candidate in candidates:
            if install_budget <= 0:
                break
            result = _attempt_skill_item(candidate, materialize_fn, root_skill_checker)
            processed[int(candidate["id"])] = result
            if result["status"] not in {"recommended"}:
                install_results.append(result)
            if result["status"] in {"installed", "already_installed"}:
                install_budget = 0

    db.clear_radar_curation(date)
    for rank, item in enumerate(shortlist, start=1):
        result = processed.get(int(item["id"]))
        if result is None and auto_install and install_budget > 0 and is_skill_candidate(item):
            result = _attempt_skill_item(item, materialize_fn, root_skill_checker)
            processed[int(item["id"])] = result
            if result["status"] in {"installed", "already_installed"}:
                install_budget = 0
            install_results.append(result)
        if result is None:
            existing = db.get_radar_install_by_repo(str(item.get("title") or ""))
            if existing and existing.get("status") == "installed":
                result = {
                    "item_id": int(item["id"]),
                    "status": "already_installed",
                    "path": str(existing.get("install_path") or ""),
                    "detail": "该仓库已有自动安装记录",
                }
            else:
                result = {
                    "item_id": int(item["id"]),
                    "status": "recommended",
                    "path": "",
                    "detail": "建议打开原链接查看",
                }
        db.upsert_radar_curation(
            curation_date=date,
            item_id=int(item["id"]),
            rank=rank,
            reason=str(item.get("curation_reason") or ""),
            install_status=str(result["status"]),
            install_path=str(result.get("path") or ""),
            install_detail=str(result.get("detail") or ""),
        )

    stored = db.list_radar_curation(date)
    return {
        "date": date,
        "shortlist": stored,
        "install_results": install_results,
        "auto_installed": sum(1 for result in install_results if result["status"] == "installed"),
        "quarantined": sum(1 for result in install_results if result["status"] == "quarantined"),
    }