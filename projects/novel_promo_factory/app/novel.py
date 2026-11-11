from __future__ import annotations

from typing import Any

from . import db, templates


class NovelSelectionError(RuntimeError):
    pass


def create_project_from_candidate(
    candidate_id: str,
    *,
    target_duration: int = 30,
    budget_limit_cny: float = 20,
) -> dict[str, Any]:
    candidate = db.get_novel_candidate(candidate_id)
    if not candidate:
        raise NovelSelectionError("小说候选不存在")
    if candidate.get("rights_status") not in {"owned", "authorized"}:
        raise NovelSelectionError("候选小说需要先标记为自有或已授权")
    if candidate.get("status") != "available":
        raise NovelSelectionError(f"候选小说当前状态不能创建项目：{candidate.get('status')}")
    project = db.create_project(
        title=str(candidate.get("title") or ""),
        genre=str(candidate.get("genre") or ""),
        source_text=str(candidate.get("source_text") or ""),
        rights_status=str(candidate.get("rights_status") or "unconfirmed"),
        target_duration=target_duration,
        budget_limit_cny=budget_limit_cny,
        novel_id=candidate_id,
        decision="pending",
        status="pending_approval",
    )
    script = templates.generate_story_script(
        str(project.get("title") or ""),
        str(project.get("genre") or ""),
        str(project.get("source_text") or ""),
        target_duration,
    )
    db.update_project(project["id"], script=script, shots=script["shots"], status="pending_approval")
    db.update_novel_candidate(candidate_id, status="in_review")
    return db.get_project(project["id"]) or {}


def auto_create_project(
    *,
    genre: str = "",
    keywords: str = "",
    target_duration: int = 30,
    budget_limit_cny: float = 20,
) -> dict[str, Any]:
    candidate = db.select_next_novel_candidate(genre=genre, keywords=keywords)
    if not candidate:
        raise NovelSelectionError("候选池里没有可用的、已授权的小说；请先添加候选或调整筛选条件")
    return create_project_from_candidate(
        str(candidate["id"]),
        target_duration=target_duration,
        budget_limit_cny=budget_limit_cny,
    )


def decide_project(
    project_id: str,
    *,
    decision: str,
    reason: str = "",
    next_candidate: bool = False,
    genre: str = "",
    keywords: str = "",
    target_duration: int = 30,
    budget_limit_cny: float = 20,
) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise NovelSelectionError("项目不存在")
    if decision not in {"approve", "reject"}:
        raise NovelSelectionError("decision 必须是 approve 或 reject")
    novel_id = str(project.get("novel_id") or "")
    if decision == "approve":
        project = db.update_project(project_id, decision="approved", status="approved", rejection_reason="")
        if novel_id:
            candidate = db.get_novel_candidate(novel_id)
            if candidate:
                db.update_novel_candidate(novel_id, status="used", used_count=int(candidate.get("used_count") or 0) + 1)
        return {"decision": "approved", "project": project, "next_project": None}
    project = db.update_project(project_id, decision="rejected", status="rejected", rejection_reason=reason)
    if novel_id:
        db.update_novel_candidate(novel_id, status="rejected")
    next_project = None
    if next_candidate:
        try:
            next_project = auto_create_project(
                genre=genre,
                keywords=keywords,
                target_duration=target_duration,
                budget_limit_cny=budget_limit_cny,
            )
        except NovelSelectionError:
            next_project = None
    return {"decision": "rejected", "project": project, "next_project": next_project}
