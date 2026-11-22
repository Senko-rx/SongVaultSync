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


def directory(value: str) -> Path:
    return Path(value).expanduser()


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
        "--workers",
        type=worker_count,
        default=1,
        metavar="N",
        help=f"Download N tracks in parallel (1-{MAX_WORKERS}, default: 1).",
    )
    return parser
