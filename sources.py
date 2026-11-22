"""Collect tracks grouped by the playlist they came from, so playlists can be rebuilt locally."""

import json
from pathlib import Path

from playlist_selector import select_sources
from spotify_client import SpotifyClient
from spotify_sync_to_local import SpotifySyncToLocal
from track_utils import track_key

LIKED_SONGS_NAME = "Liked Songs"
RETRY_GROUP_NAME = "Retry failed"

TrackGroup = tuple[str, list[dict]]


def load_catalog_groups(catalog_file: str) -> list[TrackGroup]:
    """Read a catalog.json export into (playlist name, tracks) groups, liked songs first."""
    with open(catalog_file, encoding="utf-8") as f:
        catalog = json.load(f)

    groups: list[TrackGroup] = [(LIKED_SONGS_NAME, catalog.get("liked_songs", {}).get("tracks", []))]
    for playlist in catalog.get("playlists", []):
        groups.append((playlist.get("name") or playlist.get("id", "Playlist"), playlist.get("tracks", [])))
    return groups


def source_name(source: str, playlist_names: dict[str, str]) -> str:
    if source == "liked":
        return LIKED_SONGS_NAME
    return playlist_names.get(source, source)


def fetch_spotify_groups(requested: list[str] | None, download_all: bool) -> list[TrackGroup]:
    """Authenticate, choose sources (from flags or the interactive menu) and fetch their tracks."""
    sync = SpotifySyncToLocal()
    client = SpotifyClient(sync.get_access_token())
    playlists = sync.list_playlists(client)

    if download_all:
        sources = ["liked"] + [pl["id"] for pl in playlists]
    elif requested:
        sources = requested
    else:
        sources = select_sources(playlists)

    names = {pl["id"]: pl["name"] for pl in playlists}
    return [(source_name(source, names), sync.fetch_tracks(client, source)) for source in sources]


def save_failed(path: Path, failed: list[dict], attempted_keys: set[str]) -> None:
    """Update the failure record for --retry-failed.

    Earlier failures for tracks this run didn't attempt (e.g. a different --source)
    are kept; tracks this run attempted are replaced by this run's outcome.
    """
    previous = []
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            previous = json.load(f)
    merged = [track for track in previous if track_key(track) not in attempted_keys] + failed
    if not merged:
        path.unlink(missing_ok=True)
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)


def load_failed_groups(path: Path) -> list[TrackGroup]:
    if not path.is_file():
        raise FileNotFoundError(f"Nothing to retry: {path} does not exist.")
    with open(path, encoding="utf-8") as f:
        failed = json.load(f)
    tracks = [{key: value for key, value in track.items() if key != "error"} for track in failed]
    return [(RETRY_GROUP_NAME, tracks)]
