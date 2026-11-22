import json
from pathlib import Path

from tqdm import tqdm

from converter import convert_audio
from errors import ConversionError, DownloadError
from metadata_embedder import embed
from settings import AUDIO_BITRATE, SOURCE_AUDIO_DIR
from track_utils import assign_filenames, safe_filename, track_key


class JsonToMp3:
    def __init__(
        self,
        downloader,
        embed_metadata: bool = True,
        mp3_only: bool = False,
        output_dir: Path = Path("."),
        audio_format: str = "mp3",
        bitrate: str = AUDIO_BITRATE,
    ):
        self._downloader = downloader
        self._embed_metadata = embed_metadata
        self._mp3_only = mp3_only  # i.e. keep only the converted file, whatever its format
        self._format = audio_format
        self._bitrate = bitrate
        self._webm_dir = Path(output_dir) / SOURCE_AUDIO_DIR
        self._music_dir = Path(output_dir) / audio_format

    def _build_query(self, track: dict) -> str:
        artists = " ".join(track.get("artists", []))
        name = track.get("name", "")
        isrc = track.get("isrc", "")
        if isrc:
            return f"{artists} {name} {isrc}"
        return f"{artists} {name}"

    def _adopt_legacy_file(self, key: str, target: Path) -> bool:
        """Earlier versions named files '<spotify_id>.<ext>'; rename instead of re-downloading."""
        legacy = self._music_dir / f"{safe_filename(key)}.{self._format}"
        if legacy == target or not legacy.is_file():
            return False
        legacy.rename(target)
        return True

    def _process(self, track: dict, target: Path) -> None:
        """Download, convert and tag one track. Raises DownloadError or ConversionError."""
        downloaded = self._downloader.download(
            self._build_query(track),
            safe_filename(track_key(track)),
            self._webm_dir,
            duration_ms=track.get("duration_ms"),
        )
        convert_audio(downloaded, target, bitrate=self._bitrate)
        if self._mp3_only:
            downloaded.unlink(missing_ok=True)
        if self._embed_metadata:
            embed(target, track)

    def json_to_mp3(self, json_file: str) -> dict[str, Path]:
        """Process every track in json_file. Returns {track key: audio file path} for tracks that have a file."""
        with open(json_file, encoding="utf-8") as f:
            songs = json.load(f)

        self._music_dir.mkdir(parents=True, exist_ok=True)
        self._webm_dir.mkdir(parents=True, exist_ok=True)

        filenames = assign_filenames(songs)
        available: dict[str, Path] = {}
        failed: list[str] = []

        for track in tqdm(songs, desc="Downloading", unit="track"):
            key = track_key(track)
            target = self._music_dir / f"{filenames[key]}.{self._format}"
            if target.exists() or self._adopt_legacy_file(key, target):
                available[key] = target
                continue
            try:
                self._process(track, target)
            except (DownloadError, ConversionError) as exc:
                print(f"\n  {type(exc).__name__}: {exc}")
                failed.append(track.get("name", key))
                continue
            available[key] = target

        _report(failed)
        return available


def _report(failed: list[str]) -> None:
    if not failed:
        print("\nAll tracks processed successfully.")
        return
    print(f"\nFailed tracks ({len(failed)}):")
    for name in failed:
        print(f"  - {name}")
