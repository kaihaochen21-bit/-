from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = ROOT / "content" / "32ff615c6844" / "doubao_batch" / "segments"
SOURCE = SEGMENTS / "shot-04.mp4"
OUTPUT = SEGMENTS / "shot-05.mp4"
FRAME = SEGMENTS / ".shot-05-frame.png"
TITLE_IMAGE = SEGMENTS / ".shot-05-title.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def main() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-ss", "5.0", "-i", str(SOURCE), "-frames:v", "1", str(FRAME)], check=True)
    image = Image.open(FRAME).convert("RGB").resize((720, 1280), Image.Resampling.LANCZOS)
    image = image.filter(ImageFilter.GaussianBlur(0.8))
    image = ImageEnhance.Brightness(image).enhance(0.38)
    image = ImageEnhance.Color(image).enhance(0.55)
    overlay = Image.new("RGB", image.size, "#07100f")
    image = Image.blend(image, overlay, 0.38)

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 720, 1280), fill=(0, 8, 10, 80))
    draw.rectangle((0, 250, 720, 1030), fill=(2, 15, 16, 105))
    draw.line((70, 365, 650, 365), fill=(128, 220, 195, 90), width=2)
    draw.line((70, 930, 650, 930), fill=(128, 220, 195, 90), width=2)
    draw.text((72, 310), "末班地铁 · 终点站", font=font(28), fill=(151, 221, 201, 230))
    draw.text((72, 430), "下一站", font=font(64, True), fill=(238, 247, 242, 245))
    draw.text((72, 535), "她的名字", font=font(94, True), fill=(210, 250, 236, 255))
    draw.text((72, 705), "车门打开了。", font=font(43), fill=(224, 231, 226, 235))
    draw.text((72, 770), "站台上，没有一个人。", font=font(43), fill=(224, 231, 226, 235))
    draw.text((72, 1000), "《最后一班地铁》", font=font(34, True), fill=(155, 211, 195, 230))
    draw.text((72, 1060), "有些终点，会记住你的名字。", font=font(25), fill=(156, 176, 169, 230))

    # Vignette
    vignette = Image.new("L", image.size, 0)
    vdraw = ImageDraw.Draw(vignette)
    for i in range(190):
        alpha = int(i * 0.7)
        vdraw.rectangle((i, i, 720 - i, 1280 - i), outline=alpha)
    black = Image.new("RGB", image.size, "black")
    image = Image.composite(black, image, vignette.point(lambda x: max(0, 150 - x // 2)))
    image.save(TITLE_IMAGE)

    filter_complex = (
        "[0:v]scale=720:1280,zoompan=z='min(zoom+0.00012,1.035)':x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':d=240:s=720x1280:fps=24,"
        "eq=brightness='0.01*sin(2*PI*t*0.7)':saturation=0.85,fade=t=in:st=0:d=1.1,fade=t=out:st=8.9:d=1.1[v];"
        "[1:a]volume=0.32,lowpass=f=1700,afade=t=in:st=0:d=1.0,afade=t=out:st=8.7:d=1.3[a]"
    )
    cmd = [
        ffmpeg, "-y", "-loop", "1", "-i", str(TITLE_IMAGE), "-i", str(SOURCE),
        "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]", "-t", "10.0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(OUTPUT),
    ]
    subprocess.run(cmd, check=True)
    OUTPUT.with_suffix(".source.json").write_text(
        json.dumps(
            {
                "provider": "local_fallback",
                "author": "本地后期",
                "license": "Original / generated locally",
                "note": "豆包免费额度不足，使用 shot-04 画面与声音生成标题化收尾镜头",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    FRAME.unlink(missing_ok=True)
    TITLE_IMAGE.unlink(missing_ok=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
