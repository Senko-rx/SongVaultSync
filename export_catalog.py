import json
from datetime import datetime, timezone

from spotify_sync_to_local import SpotifySyncToLocal
from spotify_client import SpotifyClient

OUTPUT_FILE = "catalog.json"


def build_catalog(sync: SpotifySyncToLocal, client: SpotifyClient) -> dict:
    account_info = client.get_me()
    account = {
        "display_name": account_info.get("display_name") or "",
        "id": account_info["id"],
    }

    liked_tracks = sync.fetch_tracks(client, "liked")
    liked_songs = {
        "total": len(liked_tracks),
        "tracks": liked_tracks,
    }

    raw_playlists = sync.list_playlists(client)
    playlists = []
    for pl in raw_playlists:
        tracks = sync.fetch_tracks(client, pl["id"])
        playlists.append({
            "id": pl["id"],
            "name": pl["name"],
            "owner": pl["owner"],
            "total_tracks": pl["track_count"],
            "tracks": tracks,
        })

    return {
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account": account,
        "liked_songs": liked_songs,
        "playlists": playlists,
    }


def main() -> None:
    sync = SpotifySyncToLocal()
    access_token = sync.get_access_token()
    client = SpotifyClient(access_token)

    print("Building catalog...")
    catalog = build_catalog(sync, client)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    total_slots = catalog["liked_songs"]["total"] + sum(
        p["total_tracks"] for p in catalog["playlists"]
    )
    print(
        f"\nExported {len(catalog['playlists'])} playlist(s) + liked songs "
        f"({total_slots} track slots) → {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
