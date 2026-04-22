from pathlib import Path
import json
from tqdm import tqdm
from converter import convert_to_mp3
from metadata_embedder import embed
from errors import DownloadError, ConversionError
from settings import WEBM_DIR, MP3_DIR


class JsonToMp3:
    def __init__(self, downloader, embed_metadata: bool = True):
        self._downloader = downloader
        self._embed_metadata = embed_metadata
        self._webm_dir = Path(WEBM_DIR)
        self._mp3_dir = Path(MP3_DIR)

    def _mp3_path(self, track: dict) -> Path:
        track_id = track.get("id") or track["name"]
        return self._mp3_dir / f"{track_id}.mp3"

    def _webm_path(self, track: dict) -> Path:
        track_id = track.get("id") or track["name"]
        return self._webm_dir / f"{track_id}.webm"

    def _build_query(self, track: dict) -> str:
        artists = " ".join(track.get("artists", []))
        name = track.get("name", "")
        isrc = track.get("isrc", "")
        if isrc:
            return f"{artists} {name} {isrc}"
        return f"{artists} {name}"

    def json_to_mp3(self, json_file: str) -> None:
        with open(json_file, "r", encoding="utf-8") as f:
            songs = json.load(f)

        self._mp3_dir.mkdir(parents=True, exist_ok=True)
        self._webm_dir.mkdir(parents=True, exist_ok=True)

        failed: list[str] = []

        for track in tqdm(songs, desc="Downloading", unit="track"):
            mp3 = self._mp3_path(track)
            if mp3.exists():
                continue

            track_id = track.get("id") or track["name"]
            query = self._build_query(track)

            try:
                downloaded = self._downloader.download(query, track_id, self._webm_dir)
            except DownloadError as exc:
                print(f"\n  Download failed: {exc}")
                failed.append(track.get("name", track_id))
                continue

            try:
                convert_to_mp3(downloaded, mp3)
            except ConversionError as exc:
                print(f"\n  Conversion failed: {exc}")
                failed.append(track.get("name", track_id))
                continue

            if self._embed_metadata:
                embed(mp3, track)

        if failed:
            print(f"\nFailed tracks ({len(failed)}):")
            for name in failed:
                print(f"  - {name}")
        else:
            print("\nAll tracks processed successfully.")
