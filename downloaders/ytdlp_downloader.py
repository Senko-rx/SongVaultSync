from pathlib import Path
import yt_dlp
from errors import DownloadError
from settings import AUDIO_BITRATE


class YtDlpDownloader:
    def __init__(self, mp3_only: bool = False):
        self._mp3_only = mp3_only

    def download(self, query: str, track_id: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(out_dir / f"{track_id}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }

        if self._mp3_only:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": AUDIO_BITRATE.rstrip("k"),
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{query}"])
        except Exception as exc:
            raise DownloadError(f"Failed to download '{query}': {exc}") from exc

        matches = list(out_dir.glob(f"{track_id}.*"))
        if not matches:
            raise DownloadError(f"No file found after downloading '{query}'")
        return matches[0]
