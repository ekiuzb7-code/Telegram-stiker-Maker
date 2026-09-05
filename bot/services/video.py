"""FFmpeg yordamida video va GIF'larni Telegram stiker formatiga o'girish.

Video stiker talablari: WebM (VP9), 512x512, <= 3 soniya, ovoz yo'q, <= 256KB.
Animatsion stiker: animated WebP, 512x512, <= 3 soniya, <= 256KB.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path


class FFmpegMissing(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _run_ffmpeg(args: list[str]) -> None:
    if not ffmpeg_available():
        raise FFmpegMissing("FFmpeg o'rnatilmagan")
    result = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg xatosi: {result.stderr.strip()}")


def video_to_sticker_webm(src: Path, dst: Path) -> Path:
    """Videoni Telegram video stiker formatiga (WebM VP9) o'giradi."""
    _run_ffmpeg([
        "-i", str(src),
        "-t", "3",                      # maksimal 3 soniya
        "-an",                          # ovoz yo'q
        "-vf", "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000",
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-b:v", "300k",                 # 256KB limitga sig'ish uchun
        "-crf", "40",
        str(dst),
    ])
    return dst


def gif_to_sticker_webp(src: Path, dst: Path) -> Path:
    """GIF'ni Telegram animatsion stiker formatiga (animated WebP) o'giradi."""
    _run_ffmpeg([
        "-i", str(src),
        "-t", "3",
        "-vf", "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000,fps=15",
        "-loop", "0",
        "-compression_level", "6",
        "-quality", "60",
        str(dst),
    ])
    return dst