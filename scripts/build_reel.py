#!/usr/bin/env python3
"""Build a simple, original, vertical VAYANA slideshow reel from existing public site image URLs."""
import os, subprocess, urllib.request, tempfile, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(".")
OUT = ROOT / "media"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
TITLE = os.getenv("REEL_TITLE", "Discover Luxor with VAYANA").strip()[:80]
SUBTITLE = os.getenv("REEL_SUBTITLE", "Ancient wonders. Unforgettable moments. Travel Your Way.").strip()[:120]

# These are image URLs already referenced by the current VAYANA website.
SCENES = [
    ("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Hot_air_balloons_over_Luxor%2C_Egypt.jpg/800px-Hot_air_balloons_over_Luxor%2C_Egypt.jpg", "A DIFFERENT VIEW OF LUXOR"),
    ("https://upload.wikimedia.org/wikipedia/commons/c/c8/Forest_of_eternity._Temple_of_Karnak%2C_Egypt.jpg", "WALK THROUGH HISTORY"),
    ("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Templo_de_Luxor%2C_Luxor%2C_Egipto%2C_2022-04-01%2C_DD_02.jpg/800px-Templo_de_Luxor%2C_Luxor%2C_Egipto%2C_2022-04-01%2C_DD_02.jpg", "DISCOVER TIMELESS LANDMARKS"),
    ("https://commons.wikimedia.org/wiki/Special:FilePath/Temple_of_Hatshepsut,_Deir_el-Bahari,_Luxor,_Egypt.jpg", "EXPERIENCES MADE YOUR WAY"),
    ("https://commons.wikimedia.org/wiki/Special:FilePath/Felucca_on_the_Nile_in_Luxor.jpg", "SLOW DOWN BY THE NILE"),
    ("https://commons.wikimedia.org/wiki/Special:FilePath/Luxor_Temple_at_night.jpg", "LUXOR, AFTER DARK"),
]

def font(size, bold=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size)

def download(url, target):
    # Wikimedia throttles bursts; retry politely and use a browser-like User-Agent.
    headers = {"User-Agent": "VAYANA-ReelBuilder/1.0 (travel content; contact: xboad514725@gmail.com)", "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
    last_error = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            target.write_bytes(data)
            with Image.open(target) as im:
                im.verify()
            return True
        except Exception as e:
            last_error = e
            time.sleep(4 * (attempt + 1))
    raise last_error

def cover(im):
    im = im.convert("RGB")
    ratio = max(W / im.width, H / im.height)
    nw, nh = int(im.width * ratio), int(im.height * ratio)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x, y = (nw-W)//2, (nh-H)//2
    return im.crop((x, y, x+W, y+H))

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    rendered = []
    for i, (url, caption) in enumerate(SCENES, 1):
        src = td / f"source_{i}.img"
        try:
            download(url, src)
            im = cover(Image.open(src))
        except Exception as e:
            print(f"Skipping image {i}: {e}")
            continue
        time.sleep(3)
        # Darken lower area for legible editorial typography.
        shade = Image.new("RGBA", (W, H), (0,0,0,0))
        sd = ImageDraw.Draw(shade)
        for yy in range(900, H):
            alpha = int(185 * (yy-900)/(H-900))
            sd.line((0, yy, W, yy), fill=(8,18,28,alpha))
        im = Image.alpha_composite(im.convert("RGBA"), shade)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((66, 82, 370, 145), radius=26, fill=(255,255,255,225))
        d.text((94, 99), "V A Y A N A", font=font(27, True), fill=(20,28,36,255))
        d.text((70, 1390), caption, font=font(36, True), fill="white", stroke_width=1, stroke_fill=(0,0,0,120))
        if i == 1:
            d.text((70, 1490), TITLE, font=font(62, True), fill="white", stroke_width=2, stroke_fill=(0,0,0,140))
            d.text((72, 1590), SUBTITLE, font=font(27), fill=(242,246,250,255))
        else:
            d.text((70, 1510), "TRAVEL YOUR WAY", font=font(34, True), fill=(255,255,255,245))
        d.text((70, 1800), f"LUXOR  •  EGYPT     |     {i:02d}", font=font(22, True), fill=(240,244,248,230))
        frame = td / f"frame_{i:02d}.jpg"
        im.convert("RGB").save(frame, quality=94, optimize=True)
        rendered.append(frame)

    if len(rendered) < 3:
        raise SystemExit("Not enough website images could be downloaded; no video was published.")

    # Render each still as a 5-second cinematic camera move, then blend scenes with cross-dissolves.
    clips = []
    duration = 5
    fps = 30
    frames = duration * fps
    for idx, frame in enumerate(rendered):
        clip = td / f"clip_{idx:02d}.mp4"
        progress = f"(0.5-0.5*cos(PI*on/{frames-1}))"
        if idx % 2 == 0:
            zoom = f"1+0.055*{progress}"
            pan_x = f"(iw-iw/zoom)*(0.18+0.52*on/{frames-1})"
        else:
            zoom = f"1.055-0.055*{progress}"
            pan_x = f"(iw-iw/zoom)*(0.70-0.52*on/{frames-1})"
        pan_y = f"(ih-ih/zoom)*(0.30+0.36*on/{frames-1})"
        vf = (
            f"scale=1200:2134,"
            f"zoompan=z='{zoom}':x='{pan_x}':y='{pan_y}':"
            f"d={frames}:s=1080x1920:fps={fps},"
            "setsar=1,fps=30,format=yuv420p"
        )
        subprocess.run([
            "ffmpeg","-y","-loop","1","-i",str(frame),"-frames:v",str(frames),
            "-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p",str(clip)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        clips.append(clip)

    # Chain elegant cross-dissolves; each next scene eases in over the previous one.
    transition = 0.9
    inputs = []
    for clip in clips:
        inputs.extend(["-i", str(clip)])
    filters = []
    previous = "[0:v]"
    for idx in range(1, len(clips)):
        out_label = f"[mix{idx}]"
        offset = idx * (duration - transition)
        filters.append(
            f"{previous}[{idx}:v]xfade=transition=fade:duration={transition}:"
            f"offset={offset},format=yuv420p{out_label}"
        )
        previous = out_label

    final = OUT / "vayana-reel.mp4"
    subprocess.run([
        "ffmpeg","-y",*inputs,
        "-filter_complex",";".join(filters),
        "-map",previous,"-an","-r","30","-c:v","libx264",
        "-preset","medium","-crf","19","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(final)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    (OUT / "vayana-reel.txt").write_text(
        "VAYANA draft reel\n"
        f"Title: {TITLE}\nSubtitle: {SUBTITLE}\n"
        "Format: 1080x1920 MP4, silent, approximately 24 seconds.\n"
        "Review image rights/credits and the final edit before publishing.\n"
    )
    print(f"Created {final} ({final.stat().st_size} bytes)")
