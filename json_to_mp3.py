import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from tqdm import tqdm

from converter import convert_audio
from errors import ConversionError, DownloadError
from metadata_embedder import embed
from settings import AUDIO_BITRATE, SOURCE_AUDIO_DIR
from track_utils import assign_filenames, safe_filename, track_key


@dataclass(frozen=True)
class SyncResult:
    available: dict[str, Path] = field(default_factory=dict)  # track key -> audio file
    failed: list[dict] = field(default_factory=list)  # track dicts plus an "error" message


class JsonToMp3:
    def __init__(
        self,
        downloader,
        embed_metadata: bool = True,
        mp3_only: bool = False,
        output_dir: Path = Path("."),
        audio_format: str = "mp3",
        bitrate: str = AUDIO_BITRATE,
        workers: int = 1,
    ):
        self._workers = workers
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

    def json_to_mp3(self, json_file: str) -> SyncResult:
        """Process every track in json_file; report which tracks have a file and which failed."""
        with open(json_file, encoding="utf-8") as f:
            songs = json.load(f)

        self._music_dir.mkdir(parents=True, exist_ok=True)
        self._webm_dir.mkdir(parents=True, exist_ok=True)

        filenames = assign_filenames(songs)
        available: dict[str, Path] = {}
        failed: list[dict] = []
        pending: dict[str, tuple[dict, Path]] = {}

        with tqdm(total=len(songs), desc="Downloading", unit="track") as progress:
            # Cheap filesystem checks stay on this thread; only real work goes to the pool.
            for track in songs:
                key = track_key(track)
                target = self._music_dir / f"{filenames[key]}.{self._format}"
                if target.exists() or self._adopt_legacy_file(key, target):
                    available[key] = target
                    progress.update()
                elif key not in pending:
                    pending[key] = (track, target)

            for key, error in self._run_pending(pending):
                track, target = pending[key]
                if error is None:
                    available[key] = target
                else:
                    tqdm.write(f"  {type(error).__name__}: {error}")
                    failed.append({**track, "error": str(error)})
                progress.update()

        _report([track.get("name") or track_key(track) for track in failed])
        return SyncResult(available=available, failed=failed)

    def _attempt(self, track: dict, target: Path) -> Exception | None:
        try:
            self._process(track, target)
        except (DownloadError, ConversionError) as exc:
            return exc
        return None

    def _run_pending(self, pending: dict[str, tuple[dict, Path]]) -> Iterator[tuple[str, Exception | None]]:
        """Yield (track key, error or None) as tracks finish. Unexpected errors propagate."""
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            futures = {pool.submit(self._attempt, *job): key for key, job in pending.items()}
            for future in as_completed(futures):
                yield futures[future], future.result()


def _report(failed: list[str]) -> None:
    if not failed:
        print("\nAll tracks processed successfully.")
        return
    print(f"\nFailed tracks ({len(failed)}):")
    for name in failed:
        print(f"  - {name}")
