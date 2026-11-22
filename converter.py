import shutil
import subprocess
import sys
from pathlib import Path

from errors import ConversionError
from settings import AUDIO_BITRATE, SAMPLE_RATE


def ensure_ffmpeg() -> None:
    """Exit with a clear message if ffmpeg is not installed. Call from entry points."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg not found on PATH. Please install ffmpeg and try again.")
        sys.exit(1)


def convert_to_mp3(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-i", str(src), "-vn", "-ab", AUDIO_BITRATE, "-ar", str(SAMPLE_RATE), "-y", str(dst)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise ConversionError(f"ffmpeg failed converting '{src}' (exit code {result.returncode})")
