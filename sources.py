"""Collect tracks grouped by the playlist they came from, so playlists can be rebuilt locally."""

import json

from playlist_selector import select_sources
from spotify_client import SpotifyClient
from spotify_sync_to_local import SpotifySyncToLocal

LIKED_SONGS_NAME = "Liked Songs"

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
