import json
import sys
from pathlib import Path

from cli import build_parser
from converter import ensure_ffmpeg
from downloaders import get_downloader
from errors import SpotifyAuthError
from json_to_mp3 import JsonToMp3
from playlist_writer import write_playlists
from settings import PLAYLISTS_DIR
from sources import TrackGroup, fetch_spotify_groups, load_catalog_groups
from track_utils import dedupe_tracks

LIST_FILE = "list_data.json"


def _collect_groups(args) -> list[TrackGroup]:
    if args.from_catalog:
        print(f"Loading tracks from {args.from_catalog}")
        return load_catalog_groups(args.from_catalog)
    return fetch_spotify_groups(args.sources, args.all)


def main() -> None:
    args = build_parser().parse_args()
    ensure_ffmpeg()

    groups = _collect_groups(args)
    all_songs = dedupe_tracks(tracks for _, tracks in groups)
    print(f"\nTotal unique tracks: {len(all_songs)}")

    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(all_songs, f, indent=2)

    downloader = get_downloader(args.downloader)
    orchestrator = JsonToMp3(downloader, embed_metadata=not args.no_metadata, mp3_only=args.mp3_only)
    available = orchestrator.json_to_mp3(LIST_FILE)

    written = write_playlists(groups, available, Path(PLAYLISTS_DIR))
    print(f"Wrote {len(written)} playlist file(s) to {PLAYLISTS_DIR}")


if __name__ == "__main__":
    try:
        main()
    except SpotifyAuthError as exc:
        sys.exit(f"Error: {exc}")
