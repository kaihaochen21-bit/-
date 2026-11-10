"""Local, deterministic script templates. No external LLM API is used."""
from __future__ import annotations

import re
from typing import Any

from . import config

GENRE_KEYWORDS: dict[str, list[str]] = {
    "甜宠": ["rainy city night", "warm window light", "romantic silhouette", "cafe interior"],
    "悬疑": ["foggy street", "old corridor", "dim lamp", "mysterious shadow"],
    "古风": ["ancient courtyard", "moonlit roof", "silk curtain", "misty mountain"],
    "逆袭": ["city skyline", "office window", "fast train", "determined silhouette"],
    "校园": ["school corridor", "sunlit classroom", "summer trees", "bicycle wheel"],
}

DEFAULT_KEYWORDS = ["cinematic city", "rain window", "night street", "moody interior"]


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?；;])\s*|\n+", text.strip())
    result = [piece.strip(" \t\r\n") for piece in pieces if piece.strip()]
    if result:
        return result
    return [text.strip()] if text.strip() else ["一个被隐藏的秘密即将揭开。"]


def _fit_sentences(sentences: list[str], count: int) -> list[str]:
    if not sentences:
        sentences = ["故事从一个意外开始。", "真相逐渐浮出水面。", "命运在最后一刻反转。"]
    result: list[str] = []
    for index in range(count):
        result.append(sentences[min(index, len(sentences) - 1)])
    return result


def generate_story_script(title: str, genre: str, source_text: str, target_duration: int = 30) -> dict[str, Any]:
    sentences = split_sentences(source_text)
    hook_source = sentences[0] if sentences else title
    hooks = [
        f"她以为一切都结束了，直到{title}真正开始。",
        f"所有人都劝她离开，只有他知道：{hook_source[:30]}",
        f"三分钟后，你会重新理解“{title}”这两个字。",
    ]
    durations = [3.5, 3.5, 4.0, 4.0, 4.0, 4.0, 4.0, 3.0]
    scale = max(0.6, min(1.8, float(target_duration) / sum(durations)))
    durations = [round(value * scale, 2) for value in durations]
    narration = _fit_sentences(sentences, len(durations))
    kinds = ["stock", "stock", "seedream", "seedance", "stock", "seedream", "seedance", "seedream"]
    keywords = GENRE_KEYWORDS.get(genre, DEFAULT_KEYWORDS)
    shots: list[dict[str, Any]] = []
    for index, (duration, text, kind) in enumerate(zip(durations, narration, kinds), start=1):
        shot_id = f"shot-{index:02d}"
        keyword = keywords[(index - 1) % len(keywords)]
        visual = f"{genre or '小说'}氛围镜头 {index}：{text[:36]}"
        shots.append(
            {
                "id": shot_id,
                "duration": duration,
                "kind": kind,
                "narration": text,
                "visual": visual,
                "keywords": [keyword, genre or "story", "cinematic"],
                "seedream_prompt": f"9:16竖屏，{genre or '小说'}题材，{visual}，电影感，统一色调，无文字，无水印",
                "seedance_prompt": f"9:16竖屏，{visual}，镜头缓慢推进，人物动作自然，电影感，无文字，无水印",
            }
        )
    script = {
        "title": title.strip() or "未命名项目",
        "genre": genre.strip(),
        "hooks": hooks,
        "beats": [
            {"label": "钩子", "text": hooks[0]},
            {"label": "冲突", "text": narration[1] if len(narration) > 1 else narration[0]},
            {"label": "反转", "text": narration[3] if len(narration) > 3 else narration[-1]},
            {"label": "悬念", "text": narration[5] if len(narration) > 5 else narration[-1]},
            {"label": "CTA", "text": "需要同款小说推文制作，可以看主页。"},
        ],
        "narration": "".join(narration),
        "shots": shots,
    }
    return normalize_script(script)


def normalize_script(script: dict[str, Any]) -> dict[str, Any]:
    shots = list(script.get("shots") or [])
    if len(shots) < 6:
        raise ValueError("分镜至少需要 6 个镜头")
    shots = shots[:10]
    seedance_seen = 0
    for index, shot in enumerate(shots, start=1):
        shot.setdefault("id", f"shot-{index:02d}")
        shot["duration"] = max(1.0, min(12.0, float(shot.get("duration", 4))))
        kind = str(shot.get("kind") or "stock")
        if kind == "seedance":
            seedance_seen += 1
            if seedance_seen > config.max_seedance_shots():
                shot["kind"] = "seedream"
                kind = "seedream"
        if kind not in {"stock", "seedream", "seedance"}:
            shot["kind"] = "seedream"
        shot.setdefault("narration", "")
        shot.setdefault("visual", "")
        shot.setdefault("keywords", [])
        shot.setdefault("seedream_prompt", shot.get("visual", ""))
        shot.setdefault("seedance_prompt", shot.get("visual", ""))
    script["shots"] = shots
    return script


def estimate_script_cost(script: dict[str, Any]) -> dict[str, Any]:
    shots = script.get("shots") or []
    seedream_count = sum(1 for shot in shots if shot.get("kind") == "seedream")
    seedance_shots = [shot for shot in shots if shot.get("kind") == "seedance"]
    seedance_seconds = sum(max(5.0, float(shot.get("duration", 5))) for shot in seedance_shots)
    seedream_cost = seedream_count * config.price_seedream()
    seedance_cost = seedance_seconds * config.price_seedance()
    total = round(seedream_cost + seedance_cost, 2)
    return {
        "seedream_count": seedream_count,
        "seedance_count": len(seedance_shots),
        "seedance_seconds": seedance_seconds,
        "seedream_cost_cny": round(seedream_cost, 2),
        "seedance_cost_cny": round(seedance_cost, 2),
        "total_cny": total,
        "within_per_video_limit": total <= config.per_video_limit(),
        "per_video_limit_cny": config.per_video_limit(),
    }
