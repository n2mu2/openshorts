#!/usr/bin/env python3
"""Sample Reel Builder — renders a demo reel locally (no API keys needed).

Composites the committed sample assets into a 1080x1920 vertical reel in the
exact format the Reels Bot produces:
  - photorealistic AI influencer portrait (generated from the persona sheet)
  - bilingual voiceover: starts in English, flips to Hindi mid-reel
  - CROSS-LANGUAGE subtitles: English speech -> Hindi subs, Hindi speech -> English subs
  - bold hook overlay, influencer handle, mandatory disclaimer strip
  - cinematic slow zoom on the portrait

Output: automation/output/sample_reel_L01.mp4  (git-ignored; the Sample Reel
GitHub workflow uploads it as an Actions artifact you can download).

Usage:
    python3 automation/sample_reel.py            # build the sample reel

Requirements: an ffmpeg with the drawtext filter.
  - Ubuntu runners: sudo apt-get install -y ffmpeg   (has drawtext)
  - Local: set SAMPLE_FFMPEG=/path/to/ffmpeg, or pip install imageio-ffmpeg
  - Audio duration: pip install mutagen
"""

import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONTS = os.path.join(ASSETS, "fonts")
OUT = os.path.join(BASE, "output")

ACTOR_PNG = os.path.join(ASSETS, "sample_actor.png")
VOICE_MP3 = os.path.join(ASSETS, "sample_voice.mp3")
OUTPUT_MP4 = os.path.join(OUT, "sample_reel_L01.mp4")

W, H, FPS = 1080, 1920, 30
BRASS = "0xD4A24A"

# The reel script (L01 from launch_batch.json, trimmed for the sample):
# narration per segment + the cross-language subtitle shown while it plays.
HOOK_TEXT = "NIFTY = SCOREBOARD"
HANDLE = "@rohan.marketcafe"
DISCLAIMER = "\u26A0 Educational content. Not investment advice."

SEGMENTS = [
    # (subtitle language, subtitle text) — narration language is the opposite
    ("hi", "रुको! NIFTY बस एक स्कोरबोर्ड है।"),
    ("hi", "देखो, सिंपल सी बात है —"),
    ("en", "Actually, NIFTY is a scoreboard of India's 50 biggest companies."),
    ("en", "When they do well, the score rises - just like cricket."),
    ("en", "Will you see the market differently from tomorrow? Comment YES!"),
]
# narration text per segment — used only to weight subtitle timing
NARRATION = [
    "Stop scrolling! NIFTY is just a scoreboard, and you are overthinking it.",
    "Dekho, simple si baat hai -",
    "असल में NIFTY भारत की 50 सबसे बड़ी कंपनियों का स्कोरबोर्ड है।",
    "जब ये कंपनियां अच्छा करती हैं, स्कोर ऊपर जाता है, बिल्कुल cricket की तरह।",
    "कल से आप market को नई नज़र से देखोगे? Comment YES!",
]


def ffmpeg_exe() -> str:
    """Pick a drawtext-capable ffmpeg:
    1. $SAMPLE_FFMPEG override
    2. system `ffmpeg` on PATH (ubuntu runners: apt install ffmpeg)
    3. imageio-ffmpeg's bundled binary (may lack drawtext - verified below)
    """
    override = os.environ.get("SAMPLE_FFMPEG", "").strip()
    if override:
        return override
    which = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if which.returncode == 0 and which.stdout.strip():
        return which.stdout.strip()
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("error: no ffmpeg found - set SAMPLE_FFMPEG or pip install imageio-ffmpeg", file=sys.stderr)
        sys.exit(1)


def audio_duration(path: str) -> float:
    from mutagen.mp3 import MP3
    return float(MP3(path).info.length)


def escape_drawtext(text: str) -> str:
    # escape the characters the drawtext value parser treats specially
    return (
        text.replace("\\", "\u200b")   # strip stray backslashes (safety)
        .replace(":", "\\:")
        .replace(",", "\\,")
        .replace("'", "")
        .replace("%", "\\%")
    )


def main() -> int:
    if not (os.path.exists(ACTOR_PNG) and os.path.exists(VOICE_MP3)):
        print("error: sample assets missing. Expected:", ACTOR_PNG, VOICE_MP3, file=sys.stderr)
        return 1

    exe = ffmpeg_exe()
    probe = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True)
    if "drawtext" not in probe.stdout:
        print("error: this ffmpeg build has no drawtext filter; install a full build (e.g. apt ffmpeg)", file=sys.stderr)
        return 1

    duration = audio_duration(VOICE_MP3)
    tail = 1.5
    total = duration + tail
    print(f"audio: {duration:.2f}s | reel: {total:.2f}s")

    # proportional segment timing
    weights = [max(len(n), 8) for n in NARRATION]
    wsum = sum(weights)
    bounds = []
    t = 0.0
    for i, w in enumerate(weights):
        seg_dur = max(1.2, duration * w / wsum)
        end = min(t + seg_dur, duration)
        if i == len(weights) - 1:
            end = duration
        bounds.append((t, end))
        t = end
    for i, (a, b) in enumerate(bounds):
        print(f"  seg{i + 1} {a:5.2f}-{b:5.2f}s -> {SEGMENTS[i][1][:44]}")

    sub_font = os.path.join(FONTS, "Mukta-Bold.ttf")   # Devanagari + Latin
    anton = os.path.join(FONTS, "Anton-Regular.ttf")
    for f in (sub_font, anton):
        if not os.path.exists(f):
            print(f"error: missing font {f}", file=sys.stderr)
            return 1

    def dtext(text, font, size, x, y, color, start, end, border=5, bcolor="black"):
        # quoted enable expression — no backslashes needed anywhere
        enable = f"enable='between(t,{start:.2f},{end:.2f})'"
        return (
            f"drawtext=fontfile='{font}':text='{escape_drawtext(text)}':fontsize={size}"
            f":fontcolor={color}:borderw={border}:bordercolor={bcolor}"
            f":x={x}:y={y}:{enable}"
        )

    filters = [
        # portrait -> cover-crop to 9:16 -> slow push-in zoom
        "scale=1620:2880:force_original_aspect_ratio=increase",
        "crop=1620:2880",
        "zoompan=z='min(1+0.00065*on,1.15)':x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':d=1:s=1080x1920:fps=30",
        # soft dark vignette for legibility
        "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.15:t=fill",
        # top branding + hook
        dtext(HOOK_TEXT, anton, 82, "(w-text_w)/2", 130, BRASS, 0, total, border=0),
        dtext(HANDLE, sub_font, 38, "(w-text_w)/2", 236, "white", 0, total, border=3),
    ]
    # cross-language subtitles
    for (a, b), (_, sub_text) in zip(bounds, SEGMENTS):
        size = 62 if len(sub_text) < 42 else 54
        filters.append(dtext(sub_text, sub_font, size, "(w-text_w)/2", "h-460", "white", a, b + 0.4))
    # bottom strip
    filters.append(dtext(DISCLAIMER, sub_font, 30, "(w-text_w)/2", "h-96", "0x999999", 0, total, border=0))

    graph = "[0:v]" + ",".join(filters) + f"[bg];[bg]tpad=stop_mode=clone:stop_duration={tail}[v]"
    if os.environ.get("SAMPLE_DEBUG"):
        print("FILTER GRAPH:\n", graph, "\n")

    os.makedirs(OUT, exist_ok=True)
    cmd = [
        exe, "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", ACTOR_PNG,
        "-i", VOICE_MP3,
        "-filter_complex", graph,
        "-map", "[v]", "-map", "1:a",
        "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT_MP4,
    ]
    print("compositing…")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-1500:], file=sys.stderr)
        return 1
    size = os.path.getsize(OUTPUT_MP4)
    print(f"OK -> {OUTPUT_MP4} ({size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
