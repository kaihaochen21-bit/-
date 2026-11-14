from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, db, media

MODEL_NAME = "Seedance 2.0 Mini"
ASPECT_RATIO = "9:16"
GENERATION_RESOLUTION = "720p"
FINAL_WIDTH = 1080
FINAL_HEIGHT = 1920
FINAL_FPS = 30
SHOT_COUNT = 5
SHOT_DURATION = 10.0
TARGET_DURATION = SHOT_COUNT * SHOT_DURATION
FREE_DAILY_QUOTA_UNITS = 10
ESTIMATED_UNITS_PER_10S = 2

SHOT_BLUEPRINTS = [
    {
        "title": "不存在的站",
        "narration": "末班地铁驶入一个不存在的站。她冲进车厢，车门关上，站牌变成一片空白。",
        "visual": "深夜旧式地铁站，冷绿色灯管闪烁。年轻女主人公从空站台冲向末班车，车门在她身后关闭，车窗外只剩纯黑。",
        "audio": "地铁进站的低频轰鸣、车门闭合声、远处模糊广播，不要清楚的人声。",
    },
    {
        "title": "广播叫出她的名字",
        "narration": "车厢里只剩她一个人。广播突然报出她的名字。她回头，看见一个沉默的陌生男人。",
        "visual": "同一节老式地铁车厢，女主独自站在冷绿色灯光下。她听到广播后惊恐回头，对面座位出现一个穿深色大衣、沉默不动的陌生男人。",
        "audio": "列车行驶的低频震动、突然失真的广播提示音，不要清楚的人声。",
    },
    {
        "title": "明天的报纸",
        "narration": "男人递来一张明天的报纸。头条写着她今晚失踪。她的呼吸停住了。",
        "visual": "陌生男人隔着过道把一张折叠报纸递给她。女主迟疑接过并展开，报纸版面清晰可见但文字自然模糊，镜头缓慢推近她骤然僵住的脸。",
        "audio": "纸张摩擦、列车节奏、极轻的心跳声。",
    },
    {
        "title": "透明的手",
        "narration": "她看向车窗倒影，座位是空的。低头时，她的手正一寸寸变得透明。",
        "visual": "女主看向漆黑车窗，玻璃倒影里她身后的座位空无一人。她缓慢低头，自己的手指从指尖开始变得半透明，皮肤边缘出现冷白色微光。",
        "audio": "低频耳鸣逐渐增强、非常轻的电流噼啪声。",
    },
    {
        "title": "写着她的名字",
        "narration": "列车停在没有灯光的废弃站台。男人消失，车门打开，站牌上竟写着她的名字。",
        "visual": "列车停在废弃站台，灯光一盏盏熄灭。陌生男人的座位已经空了，车门缓慢打开，远处站牌上浮现她的名字。最后画面在站牌与女主之间切近，留悬念。",
        "audio": "刹车声、灯光熄灭的电流声、车门开启声，最后一秒突然安静。",
    },
]

STYLE_PREFIX = (
    "电影级悬疑短剧，竖屏9:16，720p，写实电影摄影，老式地铁车厢，冷绿色荧光灯，"
    "金属扶手，车窗外纯黑，浅景深，轻微胶片颗粒，统一冷青绿色调。"
    "保持同一位25岁左右中国女性主角：黑色长外套、齐肩直黑发、苍白肤色、克制惊恐的表演。"
)
NEGATIVE = "画面中不要出现可读文字、字幕、水印、logo、真实品牌标识；不要换脸，不要多人拥挤，不要卡通风格。"


DREAM_SHOT_BLUEPRINTS = [
    {
        "title": "凌晨的便利店",
        "narration": "凌晨两点，巷口的便利店又亮了。林夏攥着奶奶的旧照片，推门走了进去。",
        "visual": "凌晨的旧居民区巷口，小雨刚停，地面有真实积水反光。一家老式便利店亮着偏暖的白色灯管，门头文字自然虚焦。24岁中国女性林夏穿米色长风衣、深色直筒裤、黑色帆布托特包，低马尾，脸色疲惫，从画面右侧走到店门口并推门进入。固定偏侧机位，轻微跟移，保持真实肤色和衣服褶皱。",
        "audio": "夜晚街道远处车声、鞋底踩过浅水的脚步声、便利店门铃轻响。",
    },
    {
        "title": "只卖一瓶",
        "narration": "店员把一瓶温热的琥珀色饮料推过来：重逢只卖一瓶，别买第二瓶。",
        "visual": "同一家便利店的旧收银台，米白瓷砖和木质货架，货架包装文字全部自然虚焦。55岁中国男性店员穿灰色长袖和深蓝围裙，动作缓慢，把一只短玻璃瓶装的琥珀色饮料推到柜台中央。林夏从画面左侧伸手拿瓶，另一只手捏着一张磨损的旧照片。50毫米镜头，过肩中景，不拍夸张表情，不出现魔法光效。",
        "audio": "冰柜低频嗡鸣、玻璃瓶底摩擦柜台、收银机轻响。",
    },
    {
        "title": "热汤",
        "narration": "回家后，她看见去世三年的奶奶正坐在餐桌边，把一碗热汤推到她面前。",
        "visual": "中国城市老式小户型餐厅，暖黄色吊灯，桌面有使用痕迹。72岁中国女性奶奶短发银灰，穿深绿色针织开衫，戴细金边眼镜。林夏站在门口愣住，奶奶坐在桌边，把一碗冒热气的汤缓慢推向前。固定广角中景，真实室内生活质感，轻微手持呼吸感，不出现鬼魂光晕或漂浮效果。",
        "audio": "老式挂钟滴答、瓷碗碰桌、汤匙轻响、窗外很远的城市底噪。",
    },
    {
        "title": "第二瓶",
        "narration": "奶奶轻轻按住空瓶：第二瓶不是让你再见我，是让我再留住你。该醒了。",
        "visual": "同一张旧餐桌，林夏坐在奶奶对面，两人距离很近。奶奶一只手轻轻按住桌上的空玻璃瓶，另一只手覆在林夏手背上，眼神平静而不舍。林夏眼眶发红但没有夸张哭泣。桌面暖灯，背景保持生活杂物。35毫米镜头，双人中景，表演克制，真实泪光，无特效。",
        "audio": "压低的环境声、布料摩擦、一次很轻的呼吸。",
    },
    {
        "title": "三年前的收据",
        "narration": "林夏惊醒，桌上没有人。碗还热着，下面压着一张三年前的收据和奶奶的照片。",
        "visual": "清晨偏冷的光从旧窗帘缝里照进同一个小餐厅。林夏从餐桌边猛地坐直，对面椅子空着，汤碗仍冒少量热气。她移开碗，露出一张自然虚焦的旧收据和一张奶奶年轻时在便利店门口的照片。固定近中景，真实晨光、灰尘和旧桌面纹理，不出现镜头炫光。",
        "audio": "清晨鸟声很远、椅子木腿轻响、纸张被拿起的声音。",
    },
    {
        "title": "她昨天也来过",
        "narration": "第二瓶上贴着奶奶的照片。店员说：她三年前买过。昨夜，是她在做梦。林夏没有买，只把旧照片留在柜台上。",
        "visual": "回到同一家便利店，仍是从前那个柜台和同一名灰衣店员。柜台上放着第二只琥珀色玻璃瓶，瓶身用橡皮筋绑着奶奶的小照片。林夏看清照片后没有伸手，只把自己的旧照片轻轻放下，把第二瓶推回柜台，转身走出画面。店员没有追，低头看着照片。固定机位缓慢拉远，暖白灯管真实闪烁一次，结尾停在空柜台。",
        "audio": "门铃、玻璃瓶轻碰、脚步离开、灯管短暂电流声，最后安静。",
    },
]

DREAM_STYLE_PREFIX = (
    "写实中国都市奇幻短片，竖屏9:16，720p，真实电影摄影，非广告感，非CGI。"
    "同一女主角林夏：24岁中国女性，低马尾黑发，米色长风衣，深色直筒裤，黑色帆布托特包，素颜疲惫。"
    "镜头保持自然皮肤纹理、真实衣物褶皱和手部结构，轻微手持呼吸感，单一连续动作，不切内部镜头。"
)
DREAM_NEGATIVE = (
    "全程无字幕、无水印、无logo、无可读品牌文字；不要冷绿烟雾、蓝色魔法光、粒子、传送门、"
    "夸张慢动作、CGI质感、换脸、手指畸形、多人拥挤、卡通风格。"
)


class DoubaoBatchError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise DoubaoBatchError("项目不存在")
    return project


def _batch_dir(project: dict[str, Any]) -> Path:
    return Path(project["folder"]) / "doubao_batch"


def _segments_dir(project: dict[str, Any]) -> Path:
    return _batch_dir(project) / "segments"


def expected_segment_paths(project_id: str) -> list[Path]:
    project = _project(project_id)
    folder = _segments_dir(project)
    plan = _load_plan(project)
    count = int(plan.get("shot_count") or SHOT_COUNT) if plan else SHOT_COUNT
    return [folder / f"shot-{index:02d}.mp4" for index in range(1, count + 1)]


def _load_plan(project: dict[str, Any]) -> dict[str, Any] | None:
    path = _batch_dir(project) / "plan.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _prompt_for(index: int, shot: dict[str, Any], *, style_prefix: str, negative: str) -> str:
    return (
        f"{style_prefix}第{index}个连续镜头，时长10秒，不要内部切镜。{shot['visual']}"
        f"动作顺序清楚，主体动作自然连贯。环境声：{shot['audio']}{negative}"
    )


def _batch_profile(project: dict[str, Any], target_duration: int) -> dict[str, Any]:
    title = str(project.get("title") or "")
    if target_duration == 60 and "便利店" in title:
        return {
            "blueprints": DREAM_SHOT_BLUEPRINTS,
            "style_prefix": DREAM_STYLE_PREFIX,
            "negative": DREAM_NEGATIVE,
            "genre": "都市奇幻",
            "hooks": [
                "凌晨两点，巷口的便利店又亮了。",
                "重逢只卖一瓶，别买第二瓶。",
                "她看见去世三年的奶奶坐在餐桌边。",
            ],
            "beats": [
                {"label": "钩子", "text": "林夏带着奶奶的旧照片进入凌晨便利店。"},
                {"label": "规则", "text": "店员给她一瓶重逢饮料，提醒别买第二瓶。"},
                {"label": "反转", "text": "她在梦中见到去世三年的奶奶。"},
                {"label": "警示", "text": "奶奶说第二瓶会让她把林夏留在梦里。"},
                {"label": "发现", "text": "醒来后留下的是三年前的收据和照片。"},
                {"label": "结尾", "text": "第二瓶贴着奶奶的照片，昨夜真正做梦的是奶奶。"},
            ],
            "quota_units": 12,
            "daily_seconds": 60,
            "safe_name": "dream_store",
        }
    if target_duration == 50:
        return {
            "blueprints": SHOT_BLUEPRINTS,
            "style_prefix": STYLE_PREFIX,
            "negative": NEGATIVE,
            "genre": "悬疑",
            "hooks": [
                "末班地铁停在一个不存在的站。",
                "广播里忽然报出她的名字。",
                "明天的报纸，写着今晚的失踪。",
            ],
            "beats": [
                {"label": "钩子", "text": "末班地铁驶入不存在的站。"},
                {"label": "冲突", "text": "广播叫出她的名字，陌生男人出现。"},
                {"label": "反转", "text": "报纸头条写着她今晚失踪。"},
                {"label": "悬念", "text": "她的手正在透明化。"},
                {"label": "结尾", "text": "废弃站台写着她的名字。"},
            ],
            "quota_units": 10,
            "daily_seconds": 50,
            "safe_name": "last_train",
        }
    raise DoubaoBatchError("豆包任务目前支持 50 秒或便利店项目 60 秒方案")


def build_batch(project_id: str, *, target_duration: int = 50) -> dict[str, Any]:
    project = _project(project_id)
    if project.get("rights_status") not in {"owned", "authorized"}:
        raise DoubaoBatchError("请先确认文本为自有或已授权")
    profile = _batch_profile(project, int(target_duration))
    blueprints = profile["blueprints"]
    shot_count = len(blueprints)
    total_duration = shot_count * SHOT_DURATION
    batch_dir = _batch_dir(project)
    segments_dir = _segments_dir(project)
    segments_dir.mkdir(parents=True, exist_ok=True)

    backup_path = batch_dir / "original_before_doubao.json"
    if not backup_path.exists():
        backup = {
            "created_at": _now_iso(),
            "target_duration": project.get("target_duration"),
            "status": project.get("status"),
            "decision": project.get("decision"),
            "script": project.get("script") or {},
            "shots": project.get("shots") or [],
        }
        backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")

    shots: list[dict[str, Any]] = []
    prompts: list[str] = []
    for index, blueprint in enumerate(blueprints, start=1):
        shot = {
            "id": f"shot-{index:02d}",
            "duration": SHOT_DURATION,
            "kind": "seedance",
            "title": blueprint["title"],
            "narration": blueprint["narration"],
            "visual": blueprint["visual"],
            "audio": blueprint["audio"],
            "keywords": ["realistic", "short-drama", "cinematic", "vertical", profile["safe_name"]],
        }
        shot["seedance_prompt"] = _prompt_for(
            index,
            shot,
            style_prefix=profile["style_prefix"],
            negative=profile["negative"],
        )
        shot["segment_path"] = str((segments_dir / f"shot-{index:02d}.mp4").resolve())
        shots.append(shot)
        prompts.append(f"镜头 {index}：{blueprint['title']}\n{shot['seedance_prompt']}")

    script = {
        "title": project.get("title") or "",
        "genre": project.get("genre") or profile["genre"],
        "hooks": profile["hooks"],
        "beats": profile["beats"],
        "narration": " ".join(shot["narration"] for shot in shots),
        "shots": shots,
        "doubao_batch": True,
    }
    plan = {
        "project_id": project_id,
        "title": project.get("title"),
        "provider": "doubao",
        "model": MODEL_NAME,
        "credential_mode": "豆包桌面端每日免费额度",
        "aspect_ratio": ASPECT_RATIO,
        "generation_resolution": GENERATION_RESOLUTION,
        "final_resolution": f"{FINAL_WIDTH}x{FINAL_HEIGHT}",
        "shot_count": shot_count,
        "duration_per_shot": SHOT_DURATION,
        "target_duration": total_duration,
        "estimated_quota_units": profile["quota_units"],
        "free_daily_quota_units": profile["quota_units"],
        "conservative_daily_seconds": profile["daily_seconds"],
        "quota_note": "官方未公开精确换算；本次按用户指定目标申请免费额度，实际成功条数以豆包客户端为准。",
        "segments_dir": str(segments_dir.resolve()),
        "created_at": _now_iso(),
        "shots": shots,
    }
    (batch_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (batch_dir / "prompts.md").write_text(
        f"# 《{project.get('title') or ''}》豆包 {int(total_duration)} 秒任务包\n\n"
        "模型：Seedance 2.0 Mini\n\n"
        f"生成规格：竖屏 9:16、720p、每个镜头 10 秒、共 {shot_count} 条\n\n"
        + "\n\n---\n\n".join(prompts)
        + f"\n\n保存文件名必须是 shot-01.mp4 到 shot-{shot_count:02d}.mp4。\n",
        encoding="utf-8",
    )

    project = db.update_project(
        project_id,
        target_duration=int(total_duration),
        script=script,
        shots=shots,
        decision="approved",
        rejection_reason="",
        status="doubao_planned",
    ) or project
    if project.get("novel_id"):
        candidate = db.get_novel_candidate(str(project["novel_id"]))
        if candidate and candidate.get("status") != "used":
            db.update_novel_candidate(
                str(project["novel_id"]),
                status="used",
                used_count=int(candidate.get("used_count") or 0) + 1,
            )
    return {
        "ok": True,
        "project": db.get_project(project_id) or project,
        "plan": plan,
        "plan_path": str((batch_dir / "plan.json").resolve()),
        "prompts_path": str((batch_dir / "prompts.md").resolve()),
        "backup_path": str(backup_path.resolve()),
    }


def _probe_video(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DoubaoBatchError(f"缺少片段：{path.name}")
    with path.open("rb") as handle:
        head = handle.read(64)
    if b"ftyp" not in head:
        raise DoubaoBatchError(f"{path.name} 不是有效的 MP4 文件")
    result = subprocess.run(
        [config.ffmpeg_executable(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    text = result.stderr or result.stdout or ""
    if "Video:" not in text:
        raise DoubaoBatchError(f"{path.name} 没有可解码的视频流")
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not duration_match:
        raise DoubaoBatchError(f"无法读取 {path.name} 的时长")
    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size_match = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", text)
    width, height = (int(size_match.group(1)), int(size_match.group(2))) if size_match else (0, 0)
    return {
        "path": str(path.resolve()),
        "name": path.name,
        "size": path.stat().st_size,
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "has_audio": "Audio:" in text,
    }


def status(project_id: str) -> dict[str, Any]:
    project = _project(project_id)
    batch_dir = _batch_dir(project)
    plan_path = batch_dir / "plan.json"
    plan = None
    if plan_path.is_file():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            plan = None
    paths = expected_segment_paths(project_id)
    planned_count = int(plan.get("shot_count") or len(plan.get("shots") or []) or SHOT_COUNT) if plan else len(paths)
    segments: list[dict[str, Any]] = []
    for index, path in enumerate(paths, start=1):
        item: dict[str, Any] = {"shot_id": f"shot-{index:02d}", "path": str(path.resolve()), "exists": path.is_file()}
        if path.is_file():
            try:
                item.update(_probe_video(path))
                item["valid"] = True
            except Exception as exc:
                item["valid"] = False
                item["error"] = str(exc)
        else:
            item["valid"] = False
        segments.append(item)
    valid_segments = [item for item in segments if item.get("valid")]
    imported_assets = [
        asset for asset in project.get("assets") or []
        if asset.get("provider") in {"doubao", "local_fallback"}
        and Path(str(asset.get("path") or "")).is_file()
    ]
    imported_shots = sorted({str(asset.get("shot_id")) for asset in imported_assets})
    missing = [item.get("name") or Path(item["path"]).name for item in segments if not item.get("valid")]
    return {
        "project_id": project_id,
        "title": project.get("title"),
        "planned": plan is not None,
        "plan": plan,
        "plan_path": str(plan_path.resolve()) if plan_path.is_file() else "",
        "prompts_path": str((batch_dir / "prompts.md").resolve()) if (batch_dir / "prompts.md").is_file() else "",
        "segments": segments,
        "valid_count": len(valid_segments),
        "missing": missing,
        "ready_to_import": len(valid_segments) == planned_count,
        "imported_count": len(imported_shots),
        "imported_shots": imported_shots,
        "ready_to_render": len(valid_segments) == planned_count and len(imported_shots) == planned_count,
        "estimated_quota_units": int(plan.get("estimated_quota_units") or planned_count * ESTIMATED_UNITS_PER_10S) if plan else SHOT_COUNT * ESTIMATED_UNITS_PER_10S,
        "free_daily_quota_units": int(plan.get("free_daily_quota_units") or FREE_DAILY_QUOTA_UNITS) if plan else FREE_DAILY_QUOTA_UNITS,
        "quota_note": (plan.get("quota_note") if plan else "官方未公开精确换算，实际成功条数以豆包客户端为准。"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_segments(project_id: str) -> dict[str, Any]:
    project = _project(project_id)
    state = status(project_id)
    if not state["planned"]:
        raise DoubaoBatchError("请先生成豆包任务包")
    if not state["ready_to_import"]:
        raise DoubaoBatchError("片段不完整或无法解码，缺少：" + "、".join(state["missing"]))
    imported = 0
    existing = {(asset.get("provider"), str(Path(asset.get("path") or "").resolve())): asset for asset in project.get("assets") or []}
    for segment in state["segments"]:
        source = Path(segment["path"])
        source_meta = {}
        sidecar = source.with_suffix(".source.json")
        if sidecar.is_file():
            try:
                source_meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                source_meta = {}
        provider = str(source_meta.get("provider") or "doubao")
        author = str(source_meta.get("author") or ("Doubao Seedance 2.0 Mini" if provider == "doubao" else "本地后期"))
        license_name = str(source_meta.get("license") or ("AI Generated" if provider == "doubao" else "Original / generated locally"))
        key = (provider, str(source.resolve()))
        asset = existing.get(key)
        if asset:
            asset_id = int(asset["id"])
        else:
            asset_id = db.add_asset(
                project_id,
                segment["shot_id"],
                "video",
                provider,
                str(source),
                author=author,
                license=license_name,
                downloaded_at=db.now_iso(),
                sha256=_sha256(source),
                width=int(segment.get("width") or 0),
                height=int(segment.get("height") or 0),
                duration=float(segment.get("duration") or 0),
                selected=True,
                metadata={"model": MODEL_NAME if provider == "doubao" else "local_post", "source": source_meta.get("note") or "豆包桌面端每日免费额度", "shot_id": segment["shot_id"]},
            )
            imported += 1
        db.select_asset(project_id, segment["shot_id"], asset_id)
    db.update_project(project_id, status="doubao_imported")
    return {"ok": True, "imported": imported, "project": db.get_project(project_id) or project, "status": status(project_id)}


def _run_ffmpeg(cmd: list[str], *, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-3000:]
        raise DoubaoBatchError(f"FFmpeg 失败：{tail}")


def generate_original_bgm(path: Path, *, duration: float = TARGET_DURATION) -> Path:
    """Generate an original suspense ambience locally; no third-party audio is used."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    total = int(round(duration * sample_rate))
    rng = random.Random(20261113)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for n in range(total):
            t = n / sample_rate
            fade_in = min(1.0, t / 2.0)
            fade_out = min(1.0, max(0.0, (duration - t) / 2.5))
            envelope = fade_in * fade_out
            drone = (
                0.11 * math.sin(2 * math.pi * 55.0 * t + 0.12 * math.sin(2 * math.pi * 0.07 * t))
                + 0.07 * math.sin(2 * math.pi * 82.5 * t + 0.08 * math.sin(2 * math.pi * 0.05 * t))
                + 0.04 * math.sin(2 * math.pi * 110.0 * t)
            )
            beat_phase = (t % 1.35) / 1.35
            pulse = math.exp(-18.0 * beat_phase) * (0.07 + 0.05 * min(1.0, t / duration))
            pulse *= 1.0 if t < duration - 2.0 else max(0.0, (duration - t) / 2.0)
            tick_phase = (t % 0.75) / 0.75
            tick = math.exp(-45.0 * tick_phase) * 0.018
            noise = (rng.random() * 2.0 - 1.0) * 0.006
            rise = (t / duration) ** 2 * 0.035 * math.sin(2 * math.pi * 220.0 * t)
            left = (drone + pulse + tick + noise + rise) * envelope
            right = (drone * 0.92 + pulse * 1.03 + tick * 0.94 + noise + rise * 0.85) * envelope
            for value in (left, right):
                sample = int(max(-1.0, min(1.0, value)) * 32767)
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))
    (path.parent / "bgm.json").write_text(
        json.dumps(
            {
                "title": "最后一班地铁 - 原创悬疑氛围音乐",
                "source": "本地程序生成，未使用第三方素材",
                "duration": duration,
                "sample_rate": sample_rate,
                "license": "Original / generated locally for this project",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _render_clip(source: Path, output: Path, *, duration: float) -> None:
    info = _probe_video(source)
    video_filter = (
        f"scale={FINAL_WIDTH}:{FINAL_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={FINAL_WIDTH}:{FINAL_HEIGHT},fps={FINAL_FPS},format=yuv420p"
    )
    if info.get("has_audio"):
        cmd = [
            config.ffmpeg_executable(), "-y", "-stream_loop", "-1", "-i", str(source), "-t", str(duration),
            "-map", "0:v:0", "-map", "0:a:0", "-vf", video_filter,
            "-af", f"aresample=48000,apad,atrim=0:{duration}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(output),
        ]
    else:
        cmd = [
            config.ffmpeg_executable(), "-y", "-stream_loop", "-1", "-i", str(source),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(duration),
            "-map", "0:v:0", "-map", "1:a:0", "-vf", video_filter,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(output),
        ]
    _run_ffmpeg(cmd, cwd=output.parent)


def _concat_media(paths: list[Path], output: Path, *, audio_only: bool = False) -> None:
    list_file = output.parent / f"{output.stem}-list.txt"
    list_file.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in paths), encoding="utf-8")
    codec_args = ["-c:a", "pcm_s16le"] if audio_only else ["-c", "copy"]
    _run_ffmpeg(
        [config.ffmpeg_executable(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), *codec_args, str(output)],
        cwd=output.parent,
    )


def _normalize_voice(path: Path, output: Path, *, duration: float = SHOT_DURATION) -> None:
    _run_ffmpeg(
        [
            config.ffmpeg_executable(), "-y", "-i", str(path), "-af",
            f"aresample=48000,apad,atrim=0:{duration}",
            "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(output),
        ],
        cwd=output.parent,
    )


def render_batch(project_id: str) -> dict[str, Any]:
    project = _project(project_id)
    state = status(project_id)
    if not state["ready_to_render"]:
        if state["ready_to_import"]:
            import_segments(project_id)
            project = _project(project_id)
            state = status(project_id)
        if not state["ready_to_render"]:
            raise DoubaoBatchError("豆包片段尚未全部导入，当前缺少：" + "、".join(state["missing"]))

    batch_dir = _batch_dir(project)
    work_dir = batch_dir / "render"
    work_dir.mkdir(parents=True, exist_ok=True)
    shots = project.get("shots") or (state.get("plan") or {}).get("shots") or []
    planned_count = int((state.get("plan") or {}).get("shot_count") or len(shots))
    if len(shots) != planned_count:
        raise DoubaoBatchError("项目分镜数量与豆包任务包不一致，请重新准备任务包")
    if len(state["segments"]) != planned_count:
        raise DoubaoBatchError("豆包片段数量与任务包不一致")
    target_duration = sum(max(1.0, float(shot.get("duration", SHOT_DURATION))) for shot in shots)

    warnings: list[str] = []
    clips: list[Path] = []
    voice_parts: list[Path] = []
    for index, (shot, segment) in enumerate(zip(shots, state["segments"]), start=1):
        source = Path(segment["path"])
        shot_duration = max(1.0, float(shot.get("duration", SHOT_DURATION)))
        clip = work_dir / f"clip-{index:02d}.mp4"
        _render_clip(source, clip, duration=shot_duration)
        clips.append(clip)
        raw_voice = work_dir / f"voice-{index:02d}.mp3"
        voice_path, warning = asyncio.run(
            media.synthesize_voice(
                str(shot.get("narration") or ""),
                raw_voice,
                shot_duration,
                voice="zh-CN-XiaoxiaoNeural",
                rate="+3%",
            )
        )
        if warning:
            warnings.append(warning)
        normalized_voice = work_dir / f"voice-{index:02d}.wav"
        _normalize_voice(voice_path, normalized_voice, duration=shot_duration)
        voice_parts.append(normalized_voice)

    native = work_dir / "native-joined.mp4"
    _concat_media(clips, native)
    voice = work_dir / "voice-joined.wav"
    _concat_media(voice_parts, voice, audio_only=True)
    bgm = generate_original_bgm(Path(project["folder"]) / "bgm.wav", duration=target_duration)
    srt_path = work_dir / "subtitles.srt"
    media.write_srt(shots, srt_path)

    stem = "dream_store_60s" if planned_count == 6 else "last_train_50s"
    final = work_dir / f"{stem}_1080x1920.mp4"
    subtitle_filter = (
        "subtitles=subtitles.srt:force_style='FontName=Microsoft YaHei,FontSize=17,"
        "PrimaryColour=&HFFFFFF&,OutlineColour=&H101010&,BorderStyle=1,Outline=2,"
        "Shadow=0,MarginV=92'"
    )
    mix_filter = (
        f"[0:v]{subtitle_filter}[v];"
        "[0:a]volume=0.72[native];"
        f"[1:a]volume=1.15,apad=whole_dur={target_duration}[voice];"
        f"[2:a]volume=0.22,atrim=0:{target_duration}[bg];"
        "[native][voice][bg]amix=inputs=3:duration=longest:normalize=0,"
        "alimiter=limit=0.95,aresample=48000[a]"
    )
    cmd = [
        config.ffmpeg_executable(), "-y", "-i", str(native), "-i", str(voice),
        "-stream_loop", "-1", "-i", str(bgm), "-filter_complex", mix_filter,
        "-map", "[v]", "-map", "[a]", "-t", str(target_duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(final),
    ]
    try:
        _run_ffmpeg(cmd, cwd=work_dir)
    except Exception as exc:
        warnings.append(f"字幕或混音合成失败，尝试无字幕回退：{exc}")
        fallback_filter = (
            "[0:a]volume=0.72[native];"
            f"[1:a]volume=1.15,apad=whole_dur={target_duration}[voice];"
            f"[2:a]volume=0.22,atrim=0:{target_duration}[bg];"
            "[native][voice][bg]amix=inputs=3:duration=longest:normalize=0,"
            "alimiter=limit=0.95,aresample=48000[a]"
        )
        fallback = [
            config.ffmpeg_executable(), "-y", "-i", str(native), "-i", str(voice),
            "-stream_loop", "-1", "-i", str(bgm), "-filter_complex", fallback_filter,
            "-map", "0:v:0", "-map", "[a]", "-t", str(target_duration),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(final),
        ]
        _run_ffmpeg(fallback, cwd=work_dir)

    final_info = _probe_video(final)
    db.update_project(project_id, video_path=str(final.resolve()), status="rendered")
    return {
        "ok": True,
        "video_path": str(final.resolve()),
        "bgm_path": str(bgm.resolve()),
        "subtitles_path": str(srt_path.resolve()),
        "duration": final_info["duration"],
        "width": final_info["width"],
        "height": final_info["height"],
        "has_audio": final_info["has_audio"],
        "warnings": warnings,
    }
