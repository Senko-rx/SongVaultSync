import argparse
import json
from spotify_sync_to_local import SpotifySyncToLocal
from spotify_client import SpotifyClient
from playlist_selector import select_sources
from downloaders import get_downloader
from json_to_mp3 import JsonToMp3


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SongVaultSync: sync your Spotify playlists to local mp3 files."
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

    all_songs: list[dict] = []
    seen_ids: set[str] = set()
    for source in sources:
        for track in sync.fetch_tracks(client, source):
            if track["id"] not in seen_ids:
                seen_ids.add(track["id"])
                all_songs.append(track)

    with open("list_data.json", "w") as f:
        json.dump(all_songs, f, indent=2)
    print(f"\nTotal unique tracks: {len(all_songs)}")

    downloader = get_downloader(args.downloader)
    orchestrator = JsonToMp3(downloader, embed_metadata=not args.no_metadata)
    orchestrator.json_to_mp3("list_data.json")


if __name__ == "__main__":
    main()
