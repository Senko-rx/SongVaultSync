import argparse
import json
from spotify_sync_to_local import SpotifySyncToLocal
from spotify_client import SpotifyClient
from playlist_selector import select_sources
from downloaders import get_downloader
from json_to_mp3 import JsonToMp3


def _flatten_catalog(catalog_file: str) -> list[dict]:
    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    all_songs: list[dict] = []
    seen_ids: set[str] = set()

    def _add(track: dict) -> None:
        track_id = track.get("id")
        if track_id and track_id in seen_ids:
            return
        if track_id:
            seen_ids.add(track_id)
        all_songs.append(track)

    for track in catalog.get("liked_songs", {}).get("tracks", []):
        _add(track)
    for playlist in catalog.get("playlists", []):
        for track in playlist.get("tracks", []):
            _add(track)

    return all_songs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SongVaultSync: sync your Spotify playlists to local mp3 files."
    )
    parser.add_argument(
        "--from-catalog",
        metavar="FILE",
        help="Skip Spotify auth and download from an existing catalog.json export.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        metavar="PLAYLIST_ID|liked",
        help="Source to download: 'liked' or a Spotify playlist ID. Repeatable.",
    )
    parser.add_argument(
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
        help="Skip embedding metadata and album art into mp3 files.",
    )
    args = parser.parse_args()

    if args.from_catalog:
        all_songs = _flatten_catalog(args.from_catalog)
        print(f"Loaded {len(all_songs)} unique tracks from {args.from_catalog}")
    else:
        sync = SpotifySyncToLocal()
        access_token = sync.get_access_token()
        client = SpotifyClient(access_token)

        if args.all:
            playlists = sync.list_playlists(client)
            sources = ["liked"] + [pl["id"] for pl in playlists]
        elif args.sources:
            sources = args.sources
        else:
            playlists = sync.list_playlists(client)
            sources = select_sources(playlists)

        all_songs = []
        seen_ids: set[str] = set()
        for source in sources:
            for track in sync.fetch_tracks(client, source):
                if track["id"] not in seen_ids:
                    seen_ids.add(track["id"])
                    all_songs.append(track)

        print(f"\nTotal unique tracks: {len(all_songs)}")

    with open("list_data.json", "w") as f:
        json.dump(all_songs, f, indent=2)

    downloader = get_downloader(args.downloader)
    orchestrator = JsonToMp3(downloader, embed_metadata=not args.no_metadata)
    orchestrator.json_to_mp3("list_data.json")


if __name__ == "__main__":
    main()
