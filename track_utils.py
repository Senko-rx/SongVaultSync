from collections.abc import Iterable


def dedupe_tracks(groups: Iterable[list[dict]]) -> list[dict]:
    """Merge track lists, dropping repeated Spotify IDs but keeping first-seen order.

    Tracks without an ID (Spotify local files) are always kept, since there is
    nothing reliable to compare them on.
    """
    seen_ids: set[str] = set()
    merged: list[dict] = []
    for tracks in groups:
        for track in tracks:
            track_id = track.get("id")
            if track_id:
                if track_id in seen_ids:
                    continue
                seen_ids.add(track_id)
            merged.append(track)
    return merged
