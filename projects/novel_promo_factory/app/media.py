from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import config, db

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]


def _run(cmd: list[str], *, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-2400:]
        raise RuntimeError(f"FFmpeg 失败：{tail}")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(shots: list[dict[str, Any]], path: Path) -> None:
    lines: list[str] = []
    cursor = 0.0
    for index, shot in enumerate(shots, start=1):
        duration = max(1.0, float(shot.get("duration", 4)))
        text = str(shot.get("narration") or shot.get("visual") or "").strip()
        if text:
            lines.extend([str(index), f"{_format_srt_time(cursor)} --> {_format_srt_time(cursor + duration)}", text, ""])
        cursor += duration
    path.write_text("\n".join(lines), encoding="utf-8")


def _silence(path: Path, duration: float) -> None:
    cmd = [config.ffmpeg_executable(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(max(1.0, duration)), "-q:a", "9", "-acodec", "libmp3lame", str(path)]
    _run(cmd, cwd=path.parent)


async def synthesize_voice(text: str, path: Path, duration: float, *, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "-5%") -> tuple[Path, str | None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()
    if not text:
        _silence(path, duration)
        return path, "没有旁白，已生成静音音轨"
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        await communicate.save(str(path))
        if not path.is_file() or path.stat().st_size < 100:
            raise RuntimeError("Edge TTS 没有生成有效音频")
        return path, None
    except Exception as exc:
        _silence(path, duration)
        return path, f"Edge TTS 失败，已回退静音：{exc}"


def _placeholder(path: Path, title: str, text: str) -> None:
    image = Image.new("RGB", (1080, 1920), "#10131c")
    draw = ImageDraw.Draw(image)
    for y in range(1920):
        color = int(18 + 30 * (y / 1920))
        draw.line([(0, y), (1080, y)], fill=(color, color + 4, min(255, color + 15)))
    draw.text((80, 720), title[:20], font=_font(72), fill="white")
    draw.text((80, 850), text[:34], font=_font(40), fill="#d7d9e2")
    image.save(path, quality=92)


def _extract_frame(source: Path, target: Path) -> None:
    cmd = [config.ffmpeg_executable(), "-y", "-i", str(source), "-frames:v", "1", "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", "-q:v", "2", str(target)]
    _run(cmd, cwd=target.parent)


def _selected_asset(project: dict[str, Any], shot_id: str) -> dict[str, Any] | None:
    assets = [asset for asset in project.get("assets") or [] if asset.get("shot_id") == shot_id]
    for asset in assets:
        if asset.get("selected"):
            return asset
    return assets[0] if assets else None


def _render_clip(source: Path, duration: float, output: Path, *, is_image: bool) -> None:
    common_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p"
    if is_image:
        cmd = [config.ffmpeg_executable(), "-y", "-loop", "1", "-i", str(source), "-t", str(max(1.0, duration)), "-vf", common_filter, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-movflags", "+faststart", str(output)]
    else:
        cmd = [config.ffmpeg_executable(), "-y", "-stream_loop", "-1", "-i", str(source), "-t", str(max(1.0, duration)), "-vf", common_filter, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-movflags", "+faststart", str(output)]
    _run(cmd, cwd=output.parent)


def _concat_clips(clips: list[Path], output: Path) -> None:
    list_file = output.parent / "clips.txt"
    lines = [f"file '{clip.as_posix()}'" for clip in clips]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    _run([config.ffmpeg_executable(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)], cwd=output.parent)


def make_covers(project: dict[str, Any], work_dir: Path) -> list[Path]:
    title = str(project.get("title") or "AI 小说推文")
    hook = str(((project.get("script") or {}).get("hooks") or ["一条小说，三分钟讲完。"])[0])
    first_source: Path | None = None
    for shot in project.get("shots") or []:
        asset = _selected_asset(project, str(shot.get("id")))
        if asset and Path(asset["path"]).is_file():
            first_source = Path(asset["path"])
            break
    base = work_dir / "cover_base.jpg"
    if first_source and first_source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        image = Image.open(first_source).convert("RGB")
    elif first_source and first_source.is_file():
        _extract_frame(first_source, base)
        image = Image.open(base).convert("RGB")
    else:
        _placeholder(base, title, hook)
        image = Image.open(base).convert("RGB")
    outputs: list[Path] = []
    for name, size in (("cover_douyin.jpg", (1080, 1920)), ("cover_xhs.jpg", (1080, 1440))):
        cover = ImageOps_fit(image, size)
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([0, int(size[1] * 0.58), size[0], size[1]], fill=(5, 7, 12, 155))
        draw.text((64, int(size[1] * 0.66)), title[:18], font=_font(int(size[0] * 0.075)), fill="white")
        draw.text((64, int(size[1] * 0.76)), hook[:28], font=_font(int(size[0] * 0.036)), fill="#e5e7ef")
        cover = Image.alpha_composite(cover.convert("RGBA"), overlay).convert("RGB")
        target = work_dir / name
        cover.save(target, quality=92, optimize=True)
        outputs.append(target)
    return outputs


def ImageOps_fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    from PIL import ImageOps

    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def render_project(project_id: str) -> dict[str, Any]:
    project = db.get_project(project_id)
    if not project:
        raise ValueError("项目不存在")
    if project.get("rights_status") not in {"owned", "authorized"}:
        raise ValueError("请先确认文本为自有或已授权")
    shots = project.get("shots") or []
    if not shots:
        raise ValueError("没有分镜，请先生成脚本")
    work_dir = Path(project["folder"]) / "render"
    work_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    clips: list[Path] = []
    for index, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("id") or f"shot-{index:02d}")
        duration = max(1.0, float(shot.get("duration", 4)))
        asset = _selected_asset(project, shot_id)
        source: Path
        is_image = False
        if asset and Path(asset["path"]).is_file():
            source = Path(asset["path"])
            is_image = str(asset.get("kind")) == "image" or source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        else:
            source = work_dir / f"placeholder-{index:02d}.jpg"
            _placeholder(source, str(project.get("title") or "缺少素材"), str(shot.get("visual") or "请补充素材"))
            is_image = True
            warnings.append(f"{shot_id} 缺少素材，已使用占位画面")
        clip = work_dir / f"clip-{index:02d}.mp4"
        _render_clip(source, duration, clip, is_image=is_image)
        clips.append(clip)
    silent = work_dir / "silent.mp4"
    _concat_clips(clips, silent)
    total_duration = sum(max(1.0, float(shot.get("duration", 4))) for shot in shots)
    narration = " ".join(str(shot.get("narration") or "") for shot in shots).strip()
    voice_path = work_dir / "voice.mp3"
    voice_path, warning = asyncio.run(synthesize_voice(narration, voice_path, total_duration))
    if warning:
        warnings.append(warning)
    srt_path = work_dir / "subtitles.srt"
    write_srt(shots, srt_path)
    final = work_dir / "master_9x16.mp4"
    bgm = next((path for path in (config.assets_dir() / "manual" / "bgm.mp3", config.assets_dir() / "manual" / "bgm.wav", config.assets_dir() / "manual" / "bgm.m4a") if path.is_file()), None)
    subtitle_filter = "subtitles=subtitles.srt:force_style='FontName=Microsoft YaHei,FontSize=18,PrimaryColour=&HFFFFFF&,OutlineColour=&H101010&,BorderStyle=1,Outline=2,Shadow=0,MarginV=70'"
    if bgm:
        filter_complex = (
            f"[0:v]{subtitle_filter}[v];"
            f"[1:a]apad=whole_dur={total_duration}[voice];"
            f"[2:a]volume=-18dB,atrim=0:{total_duration}[bg];"
            "[voice][bg]amix=inputs=2:duration=first:dropout_transition=0[a]"
        )
        cmd = [
            config.ffmpeg_executable(), "-y", "-i", str(silent), "-i", str(voice_path),
            "-stream_loop", "-1", "-i", str(bgm), "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]", "-t", str(total_duration), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final),
        ]
    else:
        cmd = [
            config.ffmpeg_executable(), "-y", "-i", str(silent), "-i", str(voice_path),
            "-vf", subtitle_filter, "-af", f"apad=whole_dur={total_duration}", "-t", str(total_duration),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(final),
        ]
    try:
        _run(cmd, cwd=work_dir)
    except Exception:
        warnings.append("字幕烧录失败，已输出无烧录字幕版本")
        fallback = [config.ffmpeg_executable(), "-y", "-i", str(silent), "-i", str(voice_path), "-af", f"apad=whole_dur={total_duration}", "-t", str(total_duration), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)]
        _run(fallback, cwd=work_dir)
    covers = make_covers(project, work_dir)
    db.update_project(project_id, video_path=str(final.resolve()), status="rendered")
    return {"video_path": str(final.resolve()), "covers": [str(path.resolve()) for path in covers], "warnings": warnings}
