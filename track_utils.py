import hashlib
import re
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


# Characters that are invalid in file names on Windows, macOS or Linux, plus control chars.
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MAX_FILENAME_LENGTH = 150  # leaves room for the directory and extension under common path limits
COLLISION_ID_LENGTH = 8


def track_key(track: dict) -> str:
    """Stable identifier for a track: its Spotify ID, or its title for ID-less local files."""
    return track.get("id") or track["name"]


def safe_filename(name: str) -> str:
    """Make a string safe to use as a file name on any common filesystem."""
    cleaned = _FORBIDDEN.sub("_", name)[:MAX_FILENAME_LENGTH]
    return cleaned.strip().rstrip(". ").strip()


def display_name(track: dict) -> str:
    """Human-readable "Artist, Artist - Title" label, without a dangling dash when parts are missing."""
    artists = ", ".join(track.get("artists") or [])
    title = track.get("name") or ""
    return f"{artists} - {title}" if artists and title else title or artists


def assign_filenames(tracks: Iterable[dict]) -> dict[str, str]:
    """Map each track key to a unique 'Artist - Title' file stem (no extension).

    When two different tracks would share a name (case-insensitively, for macOS and
    Windows), later ones get a short ID suffix so neither overwrites the other.
    """
    names: dict[str, str] = {}
    taken: set[str] = set()
    for track in tracks:
        key = track_key(track)
        if key in names:
            continue
        stem = safe_filename(display_name(track)) or safe_filename(key)
        if stem.lower() in taken:
            stem = f"{stem} [{safe_filename(key)[:COLLISION_ID_LENGTH]}]"
        taken.add(stem.lower())
        names[key] = stem
    return names


def temp_stem(track: dict) -> str:
    """Name for the downloaded intermediate file, unique per track.

    Spotify IDs are already filesystem-safe; ID-less local files get a hash so two
    titles that sanitize to the same string never share (or delete) a temp file.
    """
    if track.get("id"):
        return track["id"]
    digest = hashlib.sha1(track_key(track).encode("utf-8")).hexdigest()[:12]
    return f"local-{digest}"
