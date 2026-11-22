"""Command-line interface definition for songvaultsync."""

import argparse
import re
from pathlib import Path

from converter import SUPPORTED_FORMATS
from settings import AUDIO_BITRATE

MIN_BITRATE_KBPS = 32
MAX_BITRATE_KBPS = 320
MAX_WORKERS = 8  # more parallel downloads mostly gets you throttled by YouTube


def bitrate(value: str) -> str:
    """argparse type: a bitrate like '192k' within the range common encoders accept."""
    match = re.fullmatch(r"(\d+)k", value)
    if not match or not MIN_BITRATE_KBPS <= int(match.group(1)) <= MAX_BITRATE_KBPS:
        raise argparse.ArgumentTypeError(
            f"invalid bitrate '{value}': use e.g. 192k ({MIN_BITRATE_KBPS}k-{MAX_BITRATE_KBPS}k)"
        )
    return value


def worker_count(value: str) -> int:
    """argparse type: number of parallel downloads, 1..MAX_WORKERS."""
    try:
        count = int(value)
    except ValueError:
        count = 0
    if not 1 <= count <= MAX_WORKERS:
        raise argparse.ArgumentTypeError(f"invalid worker count '{value}': use 1-{MAX_WORKERS}")
    return count


def source(value: str) -> str:
    """argparse type: 'liked' or a Spotify playlist ID (base62), not a URL or path."""
    if value == "liked" or re.fullmatch(r"[A-Za-z0-9]{1,64}", value):
        return value
    raise argparse.ArgumentTypeError(
        f"invalid source '{value}': use 'liked' or a playlist ID (the part after /playlist/ in its link)"
    )


def directory(value: str) -> Path:
    return Path(value).expanduser()


CAR_IN_OUTPUT_DIR = Path("\0car-in-output-dir")  # sentinel: '--car' given without a directory
CAR_SUBDIR = "car"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse arguments and apply checks that involve more than one option."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.car is not None and args.format != "mp3":
        parser.error("--car requires --format mp3 (older car stereos can't play opus)")
    if args.car == CAR_IN_OUTPUT_DIR:
        args.car = args.output_dir / CAR_SUBDIR
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SongVaultSync: sync your Spotify playlists to local mp3 files."
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry only the tracks listed in failed.json from the previous run.",
    )
    source_group.add_argument(
        "--from-catalog",
        metavar="FILE",
        help="Skip Spotify auth and download from an existing catalog.json export.",
    )
    source_group.add_argument(
        "--source",
        action="append",
        dest="sources",
        type=source,
        metavar="PLAYLIST_ID|liked",
        help="Source to download: 'liked' or a Spotify playlist ID. Repeatable.",
    )
    source_group.add_argument(
        "--all",
        action="store_true",
        help="Download liked songs and all playlists.",
    )
    parser.add_argument(
        "--downloader",
        default="ytdlp",
        help="Downloader backend to use (default: ytdlp).",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip embedding metadata and album art.",
    )
    parser.add_argument(
        "--mp3-only",
        action="store_true",
        help="Delete the downloaded source audio after converting, keeping only the converted file.",
    )
    parser.add_argument(
        "--output-dir",
        type=directory,
        default=Path("."),
        metavar="DIR",
        help="Where to put the music, playlist and source-audio folders (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_FORMATS,
        default="mp3",
        help="Output format. 'opus' keeps YouTube's audio without re-encoding when possible (default: mp3).",
    )
    parser.add_argument(
        "--bitrate",
        type=bitrate,
        default=AUDIO_BITRATE,
        help=f"Encoding bitrate, e.g. 192k (default: {AUDIO_BITRATE}). Ignored when opus is remuxed.",
    )
    parser.add_argument(
        "--car",
        nargs="?",
        const=CAR_IN_OUTPUT_DIR,
        type=directory,
        metavar="DIR",
        help=(
            "Also export a copy for older car stereos: one numbered folder per playlist, ID3v2.3+v1 tags, "
            "no cover art, ASCII names, max 255 files per folder. Writes to DIR (an empty folder, e.g. on "
            "the USB stick) or to <output-dir>/car if DIR is omitted. Requires --format mp3."
        ),
    )
    parser.add_argument(
        "--workers",
        type=worker_count,
        default=1,
        metavar="N",
        help=f"Download N tracks in parallel (1-{MAX_WORKERS}, default: 1).",
    )
    return parser
