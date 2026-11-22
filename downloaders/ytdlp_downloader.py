import glob
from collections.abc import Callable
from pathlib import Path

import yt_dlp
from yt_dlp.utils import MaxDownloadsReached

from errors import DownloadError
from settings import DURATION_TOLERANCE_SECONDS, SEARCH_CANDIDATES

MatchFilter = Callable[..., str | None]
SOCKET_TIMEOUT_SECONDS = 30
NETWORK_RETRIES = 3
LEFTOVER_SUFFIXES = {".part", ".ytdl", ".json", ".temp"}


def duration_filter(expected_ms: int, tolerance_s: int = DURATION_TOLERANCE_SECONDS) -> MatchFilter:
    """Build a yt-dlp match_filter that rejects results whose length is far from expected."""
    expected_s = expected_ms / 1000

    def _accept(info: dict, *, incomplete: bool = False) -> str | None:
        title = info.get("title", "?")
        if info.get("is_live"):
            return f"'{title}' is a live stream"
        duration = info.get("duration")
        if duration is None:
            # Search listings may omit durations; yt-dlp calls again with full info.
            return None if incomplete else f"'{title}' has no known length"
        if abs(duration - expected_s) <= tolerance_s:
            return None
        return f"'{title}' is {duration:.0f}s, expected ~{expected_s:.0f}s"

    return _accept


class YtDlpDownloader:
    def download(self, query: str, track_id: str, out_dir: Path, duration_ms: int | None = None) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        ydl_opts = {
            "format": "bestaudio/best",
            # '%' is yt-dlp template syntax; escape it in the literal part of the path.
            "outtmpl": str(out_dir / track_id).replace("%", "%%") + ".%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": SOCKET_TIMEOUT_SECONDS,
            "retries": NETWORK_RETRIES,
        }
        search = f"ytsearch1:{query}"
        if duration_ms:
            # Look past the top hit, but stop after the first result that fits.
            ydl_opts["match_filter"] = duration_filter(duration_ms)
            ydl_opts["max_downloads"] = 1
            search = f"ytsearch{SEARCH_CANDIDATES}:{query}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search])
        except MaxDownloadsReached:
            pass  # expected: a matching candidate was downloaded
        except Exception as exc:
            raise DownloadError(f"Failed to download '{query}': {exc}") from exc

        matches = _downloaded_files(out_dir, track_id)
        if not matches:
            if duration_ms:
                raise DownloadError(
                    f"No result for '{query}' within {DURATION_TOLERANCE_SECONDS}s of the expected length"
                )
            raise DownloadError(f"No file found after downloading '{query}'")
        return max(matches, key=lambda path: path.stat().st_mtime)


def _downloaded_files(out_dir: Path, stem: str) -> list[Path]:
    """Finished audio files named '<stem>.<ext>', ignoring yt-dlp's partial and metadata files."""
    candidates = out_dir.glob(f"{glob.escape(stem)}.*")
    return [path for path in candidates if path.suffix not in LEFTOVER_SUFFIXES and path.stem == stem]
