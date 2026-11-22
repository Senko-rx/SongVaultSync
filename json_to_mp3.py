import json
from pathlib import Path

from tqdm import tqdm

from converter import convert_to_mp3
from errors import ConversionError, DownloadError
from metadata_embedder import embed
from settings import MP3_DIR, WEBM_DIR
from track_utils import assign_filenames, safe_filename, track_key


class JsonToMp3:
    def __init__(self, downloader, embed_metadata: bool = True, mp3_only: bool = False):
        self._downloader = downloader
        self._embed_metadata = embed_metadata
        self._mp3_only = mp3_only
        self._webm_dir = Path(WEBM_DIR)
        self._mp3_dir = Path(MP3_DIR)

    def _build_query(self, track: dict) -> str:
        artists = " ".join(track.get("artists", []))
        name = track.get("name", "")
        isrc = track.get("isrc", "")
        if isrc:
            return f"{artists} {name} {isrc}"
        return f"{artists} {name}"

    def _adopt_legacy_file(self, key: str, mp3: Path) -> bool:
        """Earlier versions named files '<spotify_id>.mp3'; rename instead of re-downloading."""
        legacy = self._mp3_dir / f"{safe_filename(key)}.mp3"
        if legacy == mp3 or not legacy.is_file():
            return False
        legacy.rename(mp3)
        return True

    def _process(self, track: dict, mp3: Path) -> None:
        """Download, convert and tag one track. Raises DownloadError or ConversionError."""
        downloaded = self._downloader.download(
            self._build_query(track),
            safe_filename(track_key(track)),
            self._webm_dir,
            duration_ms=track.get("duration_ms"),
        )
        convert_to_mp3(downloaded, mp3)
        if self._mp3_only:
            downloaded.unlink(missing_ok=True)
        if self._embed_metadata:
            embed(mp3, track)

    def json_to_mp3(self, json_file: str) -> dict[str, Path]:
        """Process every track in json_file. Returns {track key: mp3 path} for tracks that have a file."""
        with open(json_file, encoding="utf-8") as f:
            songs = json.load(f)

        self._mp3_dir.mkdir(parents=True, exist_ok=True)
        self._webm_dir.mkdir(parents=True, exist_ok=True)

        filenames = assign_filenames(songs)
        available: dict[str, Path] = {}
        failed: list[str] = []

        for track in tqdm(songs, desc="Downloading", unit="track"):
            key = track_key(track)
            mp3 = self._mp3_dir / f"{filenames[key]}.mp3"
            if mp3.exists() or self._adopt_legacy_file(key, mp3):
                available[key] = mp3
                continue
            try:
                self._process(track, mp3)
            except (DownloadError, ConversionError) as exc:
                print(f"\n  {type(exc).__name__}: {exc}")
                failed.append(track.get("name", key))
                continue
            available[key] = mp3

        _report(failed)
        return available


def _report(failed: list[str]) -> None:
    if not failed:
        print("\nAll tracks processed successfully.")
        return
    print(f"\nFailed tracks ({len(failed)}):")
    for name in failed:
        print(f"  - {name}")
