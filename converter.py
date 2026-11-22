import shutil
import subprocess
import sys
from pathlib import Path

from errors import ConversionError
from settings import AUDIO_BITRATE, SAMPLE_RATE

SUPPORTED_FORMATS = ("mp3", "opus")


def ensure_ffmpeg() -> None:
    """Exit with a clear message if ffmpeg is not installed. Call from entry points."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg not found on PATH. Please install ffmpeg and try again.")
        sys.exit(1)


def _ffmpeg(src: Path, dst: Path, codec_args: list[str]) -> int:
    command = ["ffmpeg", "-i", str(src), "-vn", *codec_args, "-y", str(dst)]
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def convert_audio(src: Path, dst: Path, bitrate: str = AUDIO_BITRATE) -> None:
    """Convert src to the format implied by dst's extension (.mp3 or .opus).

    For .opus the source stream is copied as-is when it is already Opus (the usual
    case for YouTube audio), avoiding a second lossy encode; otherwise it is encoded.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    fmt = dst.suffix.lstrip(".").lower()
    if fmt == "mp3":
        attempts = [["-c:a", "libmp3lame", "-b:a", bitrate, "-ar", str(SAMPLE_RATE)]]
    elif fmt == "opus":
        attempts = [["-c:a", "copy"], ["-c:a", "libopus", "-b:a", bitrate]]
    else:
        raise ConversionError(f"Unsupported output format '{dst.suffix}'. Use one of {SUPPORTED_FORMATS}.")

    returncode = 1
    for codec_args in attempts:
        returncode = _ffmpeg(src, dst, codec_args)
        if returncode == 0:
            return
    raise ConversionError(f"ffmpeg failed converting '{src}' (exit code {returncode})")
