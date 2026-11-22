import json
import sys

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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    list_file = args.output_dir / LIST_FILE
    with open(list_file, "w", encoding="utf-8") as f:
        json.dump(all_songs, f, indent=2)

    orchestrator = JsonToMp3(
        get_downloader(args.downloader),
        embed_metadata=not args.no_metadata,
        mp3_only=args.mp3_only,
        output_dir=args.output_dir,
        audio_format=args.format,
        bitrate=args.bitrate,
    )
    available = orchestrator.json_to_mp3(str(list_file))

    playlists_dir = args.output_dir / PLAYLISTS_DIR
    written = write_playlists(groups, available, playlists_dir)
    print(f"Wrote {len(written)} playlist file(s) to {playlists_dir}")


if __name__ == "__main__":
    try:
        main()
    except SpotifyAuthError as exc:
        sys.exit(f"Error: {exc}")
