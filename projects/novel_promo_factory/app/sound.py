from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import shutil
import subprocess
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from . import config, db, media


class SoundError(RuntimeError):
    pass


SFX_RULES = [
    (("地铁", "列车", "subway", "metro", "train"), "subway train interior ambience"),
    (("车门", "door"), "subway door close mechanical"),
    (("广播", "announcement", "public address"), "distorted public address announcement"),
    (("纸", "报纸", "paper"), "paper rustle close"),
    (("心跳", "heartbeat"), "human heartbeat slow"),
    (("电流", "耳鸣", "electric", "buzz"), "electrical buzz low"),
    (("刹车", "brake"), "train brake screech"),
    (("脚步", "footstep"), "footsteps on concrete"),
    (("雨", "rain"), "rain ambience"),
    (("风", "wind"), "wind ambience"),
]

VOICE_MAP = {
    "female_young_calm": "zh-CN-XiaoxiaoNeural",
    "narrator_neutral": "zh-CN-YunxiNeural",
    "male_low": "zh-CN-YunjianNeural",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise SoundError("项目不存在")
    return project


def _sound_dir(project: dict[str, Any]) -> Path:
    return Path(project["folder"]) / "sound"


def _plan_path(project: dict[str, Any]) -> Path:
    return _sound_dir(project) / "plan.json"


def _manifest_path(project: dict[str, Any]) -> Path:
    return _sound_dir(project) / "manifest.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _duration(shot: dict[str, Any]) -> float:
    return max(1.0, float(shot.get("duration", 5)))


def _sfx_queries(shot: dict[str, Any]) -> list[str]:
    text = " ".join(str(shot.get(key) or "") for key in ("title", "visual", "audio", "narration")).lower()
    found: list[str] = []
    for tokens, query in SFX_RULES:
        if any(token.lower() in text for token in tokens) and query not in found:
            found.append(query)
    if not found:
        found.append("cinematic room ambience")
    return found[:2]


def _music_brief(shot: dict[str, Any], index: int) -> str:
    text = f"{shot.get('title', '')} {shot.get('visual', '')} {shot.get('audio', '')}"
    if any(word in text for word in ("追逐", "冲", "紧张", "惊恐", "突然", "急")):
        mood = "urgent restrained tension, pulse increasing"
        bpm = 92
    elif any(word in text for word in ("废弃", "失踪", "空无", "黑暗", "死")):
        mood = "dark suspense, hollow space, fragile dread"
        bpm = 58
    elif any(word in text for word in ("雨", "回忆", "温柔", "暖")):
        mood = "intimate melancholy, soft warm texture"
        bpm = 72
    else:
        mood = "cinematic mystery, cold restrained tension"
        bpm = 64
    return (
        f"Instrumental cinematic score for a vertical suspense short drama, scene {index}. "
        f"{shot.get('title', '')}. {mood}. {bpm} BPM. "
        "Restrained low drone, subtle pulse, metallic texture, clear entrance and ending, no vocals, no lyrics."
    )


def _empty_provider_state() -> dict[str, Any]:
    return {
        "freesound": {
            "configured": bool(config.freesound_api_key()),
            "available": bool(config.freesound_api_key()),
            "license_policy": "CC0" if not config.freesound_allow_cc_by() else "CC0 or CC-BY",
            "role": "环境音与音效",
        },
        "ace_step": {
            "configured": True,
            "available": None,
            "url": config.ace_step_url(),
            "role": "按场景生成背景音乐",
        },
        "melotts": {
            "configured": True,
            "available": None,
            "url": config.melotts_url(),
            "role": "中文/中英混合旁白",
        },
        "edge_tts": {"configured": True, "available": True, "role": "MeloTTS 不可用时的旁白回退"},
        "local_synth": {"configured": True, "available": True, "role": "音乐/音效服务不可用时的本地回退"},
    }


def provider_status(*, check_remote: bool = True) -> dict[str, Any]:
    result = _empty_provider_state()
    if not check_remote:
        return result
    for name, path in (("ace_step", "/health"), ("melotts", "/health")):
        url = str(result[name]["url"]).rstrip("/") + path
        try:
            response = httpx.get(url, timeout=1.0)
            result[name]["available"] = response.status_code == 200
            if response.status_code != 200:
                result[name]["error"] = f"HTTP {response.status_code}"
        except Exception as exc:
            result[name]["available"] = False
            result[name]["error"] = str(exc)[:240]
    return result


def build_plan(project_id: str) -> dict[str, Any]:
    project = _project(project_id)
    shots = project.get("shots") or []
    if not shots:
        raise SoundError("没有分镜，请先生成脚本")
    cursor = 0.0
    planned_shots: list[dict[str, Any]] = []
    for index, source_shot in enumerate(shots, start=1):
        shot = dict(source_shot)
        duration = _duration(shot)
        shot_id = str(shot.get("id") or f"shot-{index:02d}")
        shot["id"] = shot_id
        queries = _sfx_queries(shot)
        voice_style = str(shot.get("voice_style") or "female_young_calm")
        shot["audio_plan"] = {
            "version": 1,
            "start": round(cursor, 3),
            "end": round(cursor + duration, 3),
            "voice": {
                "provider": "melotts",
                "fallback": "edge_tts",
                "voice_id": voice_style,
                "edge_voice": VOICE_MAP.get(voice_style, "zh-CN-XiaoxiaoNeural"),
                "language": "ZH",
                "speaker": config.melotts_speaker(),
                "speed": 0.95,
                "volume_db": 0,
                "text": str(shot.get("narration") or "").strip(),
            },
            "music": {
                "provider": "ace_step",
                "fallback": "local_synth",
                "prompt": _music_brief(shot, index),
                "duration": max(10.0, duration),
                "volume_db": -19,
                "fade_in": 0.4,
                "fade_out": 0.8,
            },
            "sfx": [
                {
                    "provider": "freesound",
                    "fallback": "local_synth",
                    "query": query,
                    "license": "CC0" if not config.freesound_allow_cc_by() else "CC0_OR_BY",
                    "start": round(0.35 + position * 1.2, 3),
                    "volume_db": -13 - position * 2,
                }
                for position, query in enumerate(queries)
            ],
        }
        planned_shots.append(shot)
        cursor += duration
    script = project.get("script") if isinstance(project.get("script"), dict) else {}
    script = dict(script)
    script["shots"] = planned_shots
    plan = {
        "project_id": project_id,
        "title": project.get("title") or "",
        "version": 1,
        "created_at": _now_iso(),
        "total_duration": round(cursor, 3),
        "shots": planned_shots,
        "providers": provider_status(check_remote=False),
    }
    _write_json(_plan_path(project), plan)
    db.update_project(project_id, shots=planned_shots, script=script, status="audio_planned")
    return status(project_id, check_remote=True)


def status(project_id: str, *, check_remote: bool = True) -> dict[str, Any]:
    project = _project(project_id)
    plan = _read_json(_plan_path(project), None)
    manifest = _read_json(_manifest_path(project), {})
    entries = manifest.get("shots") if isinstance(manifest, dict) else []
    entries = entries if isinstance(entries, list) else []
    planned_shots = plan.get("shots") if isinstance(plan, dict) else []
    planned_shots = planned_shots if isinstance(planned_shots, list) else []
    generated_shots = {str(item.get("shot_id")) for item in entries if Path(str(item.get("voice_path") or "")).is_file() and Path(str(item.get("music_path") or "")).is_file()}
    return {
        "project_id": project_id,
        "title": project.get("title"),
        "planned": bool(plan),
        "plan_path": str(_plan_path(project).resolve()) if _plan_path(project).is_file() else "",
        "manifest_path": str(_manifest_path(project).resolve()) if _manifest_path(project).is_file() else "",
        "shot_count": len(planned_shots),
        "generated_count": len(generated_shots),
        "ready_to_generate": bool(plan),
        "ready_to_render": bool(plan) and len(generated_shots) == len(planned_shots),
        "providers": provider_status(check_remote=check_remote),
        "plan": plan,
        "manifest": manifest,
    }


def _run_ffmpeg(cmd: list[str], *, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-3000:]
        raise SoundError(f"FFmpeg 失败：{tail}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _synthesize_music(path: Path, *, duration: float, seed: int, brief: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    total = int(round(duration * sample_rate))
    rng = random.Random(seed)
    tense = any(word in brief.lower() for word in ("urgent", "tension", "suspense", "dread"))
    root = 48.0 + (seed % 5) * 3.0
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for n in range(total):
            t = n / sample_rate
            fade_in = min(1.0, t / 0.5)
            fade_out = min(1.0, max(0.0, (duration - t) / 1.0))
            envelope = fade_in * fade_out
            drone = 0.09 * math.sin(2 * math.pi * root * t)
            drone += 0.045 * math.sin(2 * math.pi * (root * 1.5) * t)
            wobble = 0.018 * math.sin(2 * math.pi * (root * 2.02) * t + 0.25 * math.sin(2 * math.pi * 0.11 * t))
            pulse_rate = 1.15 if tense else 0.72
            phase = (t % pulse_rate) / pulse_rate
            pulse = math.exp(-17.0 * phase) * (0.05 if tense else 0.03)
            noise = (rng.random() * 2.0 - 1.0) * 0.004
            left = (drone + wobble + pulse + noise) * envelope
            right = (drone * 0.94 + wobble * 1.04 + pulse * 0.91 + noise) * envelope
            for value in (left, right):
                sample = int(max(-1.0, min(1.0, value)) * 32767)
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))
    return path


def _synthesize_sfx(path: Path, *, duration: float, seed: int, query: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    total = int(round(duration * sample_rate))
    rng = random.Random(seed)
    q = query.lower()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for n in range(total):
            t = n / sample_rate
            fade = min(1.0, t / 0.12) * min(1.0, max(0.0, (duration - t) / 0.35))
            noise = (rng.random() * 2.0 - 1.0)
            if "heartbeat" in q:
                phase = (t % 0.82) / 0.82
                value = math.exp(-28.0 * phase) * 0.22
            elif "paper" in q:
                value = noise * (0.06 + 0.05 * max(0.0, math.sin(2 * math.pi * 17.0 * t)))
            elif "electrical" in q:
                value = 0.06 * math.sin(2 * math.pi * 120.0 * t) + noise * 0.025
            elif "door" in q:
                phase = (t % 3.2) / 3.2
                value = math.exp(-12.0 * phase) * 0.2 + noise * 0.018
            elif "brake" in q:
                value = 0.08 * math.sin(2 * math.pi * (900.0 - 420.0 * min(1.0, t / duration)) * t) + noise * 0.02
            else:
                value = 0.06 * math.sin(2 * math.pi * 42.0 * t) + noise * 0.025
            value *= fade
            for channel in (value, value * 0.97):
                sample = int(max(-1.0, min(1.0, channel)) * 32767)
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))
    return path


def _normalize_audio(source: Path, output: Path, *, duration: float, loop: bool = False) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [config.ffmpeg_executable(), "-y"]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i", str(source), "-t", str(duration),
        "-af", f"aresample=48000,apad,atrim=0:{duration}",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(output),
    ]
    _run_ffmpeg(cmd, cwd=output.parent)
    return output


def _silence(path: Path, duration: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg([
        config.ffmpeg_executable(), "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(duration), "-c:a", "pcm_s16le", str(path),
    ], cwd=path.parent)
    return path


def _freesound_download(query: str, output_dir: Path, stem: str) -> dict[str, Any]:
    api_key = config.freesound_api_key()
    if not api_key:
        raise SoundError("未配置 FREESOUND_API_KEY")
    allowed = {"Creative Commons 0"}
    if config.freesound_allow_cc_by():
        allowed.add("Attribution")
    params = {
        "query": query,
        "token": api_key,
        "page_size": 8,
        "sort": "score",
        "fields": "id,name,previews,license,username,duration,url",
    }
    if not config.freesound_allow_cc_by():
        params["filter"] = 'license:"Creative Commons 0"'
    try:
        with httpx.Client(timeout=25, follow_redirects=True) as client:
            response = client.get("https://freesound.org/apiv2/search/text/", params=params)
            if response.status_code != 200:
                raise SoundError(f"Freesound 搜索失败：HTTP {response.status_code}")
            results = response.json().get("results") or []
            selected = next((item for item in results if str(item.get("license")) in allowed), None)
            if not selected:
                raise SoundError(f"Freesound 没有找到可用授权素材：{query}")
            previews = selected.get("previews") or {}
            preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
            if not preview_url:
                raise SoundError("Freesound 结果没有可下载预览")
            audio = client.get(preview_url)
            if audio.status_code != 200 or len(audio.content) < 200:
                raise SoundError(f"Freesound 下载失败：HTTP {audio.status_code}")
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{stem}.mp3"
            path.write_bytes(audio.content)
    except httpx.HTTPError as exc:
        raise SoundError(f"Freesound 网络错误：{exc}") from exc
    return {
        "provider": "freesound",
        "path": str(path.resolve()),
        "source_url": selected.get("url") or "",
        "author": selected.get("username") or "",
        "license": selected.get("license") or "",
        "duration": float(selected.get("duration") or 0),
        "name": selected.get("name") or query,
        "sha256": _sha256(path),
    }


def _ace_step_generate(prompt: str, output_dir: Path, stem: str, duration: float) -> dict[str, Any]:
    base_url = config.ace_step_url()
    headers = {"Authorization": f"Bearer {config.ace_step_api_key()}"} if config.ace_step_api_key() else {}
    payload = {
        "prompt": prompt,
        "lyrics": "",
        "thinking": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "audio_duration": max(10.0, min(600.0, duration)),
        "audio_format": "wav",
        "batch_size": 1,
        "inference_steps": 8,
        "model": config.ace_step_model(),
        "use_random_seed": True,
    }
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(f"{base_url}/release_task", json=payload, headers=headers)
            if response.status_code != 200:
                raise SoundError(f"ACE-Step 提交失败：HTTP {response.status_code}")
            body = response.json()
            task_id = str((body.get("data") or {}).get("task_id") or "")
            if not task_id:
                raise SoundError(f"ACE-Step 没有返回 task_id：{body.get('error') or body}")
            deadline = time.time() + config.ace_step_timeout_seconds()
            result_item: dict[str, Any] | None = None
            while time.time() < deadline:
                time.sleep(2.0)
                query = client.post(f"{base_url}/query_result", json={"task_id_list": [task_id]}, headers=headers)
                if query.status_code != 200:
                    continue
                data = query.json().get("data") or []
                item = data[0] if data else None
                if not item:
                    continue
                status_code = int(item.get("status") or 0)
                if status_code == 2:
                    raise SoundError("ACE-Step 音乐生成失败")
                if status_code == 1:
                    result_item = item
                    break
            if result_item is None:
                raise SoundError("ACE-Step 生成超时")
            raw_result = result_item.get("result") or "[]"
            parsed = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            first = parsed[0] if isinstance(parsed, list) and parsed else {}
            file_url = str(first.get("file") or "")
            if not file_url:
                raise SoundError("ACE-Step 结果缺少音频地址")
            download_url = file_url if file_url.startswith("http") else urljoin(base_url + "/", file_url.lstrip("/"))
            audio = client.get(download_url, headers=headers)
            if audio.status_code != 200 or len(audio.content) < 500:
                raise SoundError(f"ACE-Step 音频下载失败：HTTP {audio.status_code}")
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{stem}.wav"
            path.write_bytes(audio.content)
    except httpx.HTTPError as exc:
        raise SoundError(f"ACE-Step 网络错误：{exc}") from exc
    return {
        "provider": "ace_step",
        "path": str(path.resolve()),
        "model": config.ace_step_model(),
        "prompt": prompt,
        "task_id": task_id,
        "license": "MIT (ACE-Step 1.5)",
        "sha256": _sha256(path),
    }


def _melotts_generate(text: str, output: Path, *, language: str, speaker: str, speed: float) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {config.melotts_api_key()}"} if config.melotts_api_key() else {}
    try:
        response = httpx.post(
            f"{config.melotts_url()}/tts",
            json={"text": text, "language": language, "speaker": speaker, "speed": speed},
            headers=headers,
            timeout=180,
        )
    except httpx.HTTPError as exc:
        raise SoundError(f"MeloTTS 网络错误：{exc}") from exc
    if response.status_code != 200 or len(response.content) < 200:
        raise SoundError(f"MeloTTS 生成失败：HTTP {response.status_code}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    return {
        "provider": "melotts",
        "path": str(output.resolve()),
        "license": "MIT",
        "sha256": _sha256(output),
    }


def _edge_voice(text: str, output: Path, duration: float, *, voice: str, rate: str) -> tuple[dict[str, Any], str | None]:
    raw = output.with_suffix('.mp3')
    raw, warning = asyncio.run(media.synthesize_voice(text, raw, duration, voice=voice, rate=rate))
    _normalize_audio(raw, output, duration=duration)
    return {
        "provider": "edge_tts",
        "path": str(output.resolve()),
        "license": "Edge TTS prototype use",
        "voice": voice,
        "sha256": _sha256(output),
    }, warning


def generate_assets(project_id: str, *, force: bool = False) -> dict[str, Any]:
    project = _project(project_id)
    plan = _read_json(_plan_path(project), None)
    if not plan:
        raise SoundError("请先准备场景声音方案")
    root = _sound_dir(project) / "assets"
    voice_dir = root / "voice"
    music_dir = root / "music"
    sfx_dir = root / "sfx"
    for folder in (voice_dir, music_dir, sfx_dir):
        folder.mkdir(parents=True, exist_ok=True)
    old = _read_json(_manifest_path(project), {})
    old_by_shot = {str(item.get("shot_id")): item for item in (old.get("shots") or [])}
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, shot in enumerate(plan.get("shots") or [], start=1):
        shot_id = str(shot.get("id") or f"shot-{index:02d}")
        duration = _duration(shot)
        audio_plan = shot.get("audio_plan") or {}
        previous = old_by_shot.get(shot_id) or {}
        voice_plan = audio_plan.get("voice") or {}
        music_plan = audio_plan.get("music") or {}
        voice_out = voice_dir / f"{shot_id}.wav"
        music_out = music_dir / f"{shot_id}.wav"
        if not force and previous and Path(str(previous.get("voice_path") or "")).is_file():
            voice_info = {"provider": previous.get("voice_provider"), "path": previous.get("voice_path"), "license": previous.get("voice_license") or ""}
        else:
            text = str(voice_plan.get("text") or "").strip()
            if text and voice_plan.get("provider") == "melotts":
                try:
                    info = _melotts_generate(text, voice_out, language=str(voice_plan.get("language") or "ZH"), speaker=str(voice_plan.get("speaker") or "ZH"), speed=float(voice_plan.get("speed") or 1.0))
                    voice_info = info
                except Exception as exc:
                    voice_info, warning = _edge_voice(text, voice_out, duration, voice=str(voice_plan.get("edge_voice") or "zh-CN-XiaoxiaoNeural"), rate="+0%")
                    if warning:
                        warnings.append(f"{shot_id} 旁白：{warning}")
                    warnings.append(f"{shot_id} MeloTTS 回退 Edge TTS：{exc}")
            else:
                voice_info, warning = _edge_voice(text, voice_out, duration, voice=str(voice_plan.get("edge_voice") or "zh-CN-XiaoxiaoNeural"), rate="+0%")
                if warning:
                    warnings.append(f"{shot_id} 旁白：{warning}")
        if not force and previous and Path(str(previous.get("music_path") or "")).is_file():
            music_info = {"provider": previous.get("music_provider"), "path": previous.get("music_path"), "license": previous.get("music_license") or "", "prompt": previous.get("music_prompt") or ""}
        else:
            prompt = str(music_plan.get("prompt") or _music_brief(shot, index))
            try:
                music_info = _ace_step_generate(prompt, music_dir, shot_id, duration)
                _normalize_audio(Path(music_info["path"]), music_out, duration=duration, loop=True)
                music_info["path"] = str(music_out.resolve())
            except Exception as exc:
                raw = music_dir / f"{shot_id}-synth.wav"
                _synthesize_music(raw, duration=duration, seed=20261113 + index, brief=prompt)
                _normalize_audio(raw, music_out, duration=duration, loop=True)
                music_info = {"provider": "local_synth", "path": str(music_out.resolve()), "license": "Original / generated locally", "prompt": prompt}
                warnings.append(f"{shot_id} ACE-Step 回退本地合成音乐：{exc}")
        sfx_infos: list[dict[str, Any]] = []
        for sfx_index, sfx_plan in enumerate(audio_plan.get("sfx") or [], start=1):
            query = str(sfx_plan.get("query") or "cinematic room ambience")
            sfx_base = f"{shot_id}-{sfx_index:02d}"
            sfx_out = sfx_dir / f"{sfx_base}.wav"
            old_sfx = next((item for item in (previous.get("sfx") or []) if int(item.get("index") or 0) == sfx_index), None)
            if not force and old_sfx and Path(str(old_sfx.get("path") or "")).is_file():
                info = dict(old_sfx)
            else:
                try:
                    downloaded = _freesound_download(query, sfx_dir, sfx_base)
                    _normalize_audio(Path(downloaded["path"]), sfx_out, duration=duration, loop=True)
                    info = dict(downloaded)
                    info["path"] = str(sfx_out.resolve())
                except Exception as exc:
                    raw = sfx_dir / f"{sfx_base}-synth.wav"
                    _synthesize_sfx(raw, duration=duration, seed=20261113 + index * 10 + sfx_index, query=query)
                    _normalize_audio(raw, sfx_out, duration=duration, loop=True)
                    info = {"provider": "local_synth", "path": str(sfx_out.resolve()), "license": "Original / generated locally", "query": query}
                    warnings.append(f"{shot_id} Freesound 回退本地合成音效：{exc}")
                info["index"] = sfx_index
                info["start"] = float(sfx_plan.get("start") or 0.35)
                info["volume_db"] = float(sfx_plan.get("volume_db") or -13)
            sfx_infos.append(info)
        entries.append({
            "shot_id": shot_id,
            "start": float(shot.get("audio_plan", {}).get("start") or 0),
            "duration": duration,
            "voice_provider": voice_info.get("provider") or "",
            "voice_path": voice_info.get("path") or "",
            "voice_license": voice_info.get("license") or "",
            "music_provider": music_info.get("provider") or "",
            "music_path": music_info.get("path") or "",
            "music_license": music_info.get("license") or "",
            "music_prompt": music_info.get("prompt") or "",
            "sfx": sfx_infos,
        })
    manifest = {
        "project_id": project_id,
        "title": project.get("title") or "",
        "generated_at": _now_iso(),
        "shots": entries,
        "warnings": warnings,
        "provider_status": provider_status(check_remote=False),
    }
    _write_json(_manifest_path(project), manifest)
    db.update_project(project_id, status="audio_generated")
    return {"ok": True, "status": status(project_id, check_remote=True), "warnings": warnings}


def _mix_shot_audio(entry: dict[str, Any], output: Path) -> Path:
    duration = float(entry.get("duration") or 10)
    voice = Path(str(entry.get("voice_path") or ""))
    music = Path(str(entry.get("music_path") or ""))
    if not voice.is_file():
        voice = _silence(output.parent / f"{entry.get('shot_id')}-voice-silence.wav", duration)
    if not music.is_file():
        music = _silence(output.parent / f"{entry.get('shot_id')}-music-silence.wav", duration)
    sfx_items = [item for item in (entry.get("sfx") or []) if Path(str(item.get("path") or "")).is_file()]
    cmd = [config.ffmpeg_executable(), "-y", "-i", str(voice), "-stream_loop", "-1", "-i", str(music)]
    for item in sfx_items:
        cmd += ["-i", str(item["path"])]
    filters = [
        f"[0:a]aresample=48000,apad,atrim=0:{duration},volume=0dB[v0]",
        f"[1:a]aresample=48000,atrim=0:{duration},volume=-19dB,afade=t=in:st=0:d=0.4,afade=t=out:st={max(0.1, duration - 0.8)}:d=0.8[m0]",
    ]
    labels = ["[v0]", "[m0]"]
    for index, item in enumerate(sfx_items, start=1):
        start_ms = int(float(item.get("start") or 0.35) * 1000)
        volume = float(item.get("volume_db") or -13)
        filters.append(f"[{index + 1}:a]aresample=48000,adelay={start_ms}|{start_ms},apad,atrim=0:{duration},volume={volume}dB[s{index}]")
        labels.append(f"[s{index}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0,alimiter=limit=0.95,aresample=48000[a]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[a]", "-t", str(duration), "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(output)]
    _run_ffmpeg(cmd, cwd=output.parent)
    return output


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip().strip(".")
    return (cleaned or "未命名")[:70]


def render_scene_video(project_id: str, *, force: bool = False) -> dict[str, Any]:
    project = _project(project_id)
    state = status(project_id, check_remote=False)
    if not state["ready_to_render"] and force:
        generate_assets(project_id, force=True)
        project = _project(project_id)
        state = status(project_id, check_remote=False)
    if not state["ready_to_render"]:
        raise SoundError("声音素材尚未全部生成，请先点击“生成场景声音素材”")
    work = _sound_dir(project) / "render"
    work.mkdir(parents=True, exist_ok=True)
    final = work / f"{_safe_filename(str(project.get('title') or '视频'))}_场景声音版.mp4"
    manifest = state.get("manifest") or {}
    saved_source = Path(str(manifest.get("source_video_path") or ""))
    candidates = [
        saved_source,
        Path(project["folder"]) / "doubao_batch" / "render" / "last_train_50s_1080x1920.mp4",
        Path(project["folder"]) / "render" / "silent.mp4",
        Path(project["folder"]) / "render" / "master_9x16.mp4",
        Path(project["folder"]) / "doubao_batch" / "render" / "native-joined.mp4",
        Path(str(project.get("video_path") or "")),
    ]
    source_video = next(
        (path for path in candidates if path.is_file() and path.resolve() != final.resolve()),
        Path(""),
    )
    if not source_video.is_file():
        raise SoundError("没有可混音的视频，请先完成画面渲染")
    entries = state["manifest"].get("shots") or []
    parts: list[Path] = []
    for index, entry in enumerate(entries, start=1):
        part = work / f"shot-{index:02d}.wav"
        _mix_shot_audio(entry, part)
        parts.append(part)
    list_file = work / "audio-list.txt"
    list_file.write_text("\n".join(f"file '{part.as_posix()}'" for part in parts), encoding="utf-8")
    mixed_audio = work / "scene-audio.wav"
    _run_ffmpeg([config.ffmpeg_executable(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:a", "pcm_s16le", str(mixed_audio)], cwd=work)
    manifest["source_video_path"] = str(source_video.resolve())
    _write_json(_manifest_path(project), manifest)
    _run_ffmpeg([
        config.ffmpeg_executable(), "-y", "-i", str(source_video), "-i", str(mixed_audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(final),
    ], cwd=work)
    publish_dir = config.publish_video_dir()
    publish_dir.mkdir(parents=True, exist_ok=True)
    published = publish_dir / f"{_safe_filename(str(project.get('title') or '视频'))}_场景声音版_9x16.mp4"
    shutil.copy2(final, published)
    db.update_project(project_id, video_path=str(final.resolve()), status="rendered")
    return {
        "ok": True,
        "video_path": str(final.resolve()),
        "published_path": str(published.resolve()),
        "published_sha256": _sha256(published),
        "status": status(project_id, check_remote=False),
    }
