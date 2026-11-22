import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping


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


# Characters that are invalid in file names on Windows, macOS or Linux, plus ASCII control chars.
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
# Other control, formatting (bidi overrides, zero-width) and line/paragraph separators: removed.
_INVISIBLE_CATEGORIES = {"Cc", "Cf", "Zl", "Zp"}
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
MAX_FILENAME_BYTES = 200  # under the common 255-byte limit, leaving room for '.part' and the extension
COLLISION_ID_LENGTH = 8
UNTITLED = "untitled"


def track_key(track: dict) -> str:
    """Stable identifier: the Spotify ID, or 'local:<Artist - Title>' for ID-less local files."""
    if track.get("id"):
        return track["id"]
    return f"local:{display_name(track) or UNTITLED}"


def _truncate_bytes(text: str, limit: int) -> str:
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def safe_filename(name: str, max_bytes: int = MAX_FILENAME_BYTES) -> str:
    """Make a string safe to use as a file name on any common filesystem."""
    cleaned = _FORBIDDEN.sub("_", name)
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) not in _INVISIBLE_CATEGORIES)
    cleaned = _truncate_bytes(cleaned, max_bytes).strip().rstrip(". ").strip()
    if cleaned.split(".")[0].upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def display_name(track: dict) -> str:
    """Human-readable "Artist, Artist - Title" label on one line, without a dangling dash."""
    artists = ", ".join(track.get("artists") or [])
    title = track.get("name") or ""
    label = f"{artists} - {title}" if artists and title else title or artists
    return " ".join(label.split())  # collapses newlines/tabs that would break playlist files


def _short_id(track: dict) -> str:
    return (track.get("id") or hashlib.sha1(track_key(track).encode("utf-8")).hexdigest())[:COLLISION_ID_LENGTH]


def _unique_stem(track: dict, taken: set[str]) -> str:
    base = safe_filename(display_name(track)) or safe_filename(track.get("id") or "") or UNTITLED
    if base.lower() not in taken:
        return base
    tag, counter = _short_id(track), 1
    while True:  # the ID suffix is almost always enough; the counter is a last resort
        suffix = f" [{tag}]" if counter == 1 else f" [{tag}-{counter}]"
        stem = safe_filename(base, MAX_FILENAME_BYTES - len(suffix.encode("utf-8"))) + suffix
        if stem.lower() not in taken:
            return stem
        counter += 1


def assign_filenames(tracks: Iterable[dict], existing: Mapping[str, str] | None = None) -> dict[str, str]:
    """Map each track key to a unique 'Artist - Title' file stem (no extension).

    Names in `existing` (from earlier runs) are kept and count as taken, so a track's
    file name doesn't depend on which other tracks are in this run. When two tracks
    would share a name (case-insensitively, for macOS and Windows), the newcomer gets
    a short ID suffix.
    """
    names: dict[str, str] = dict(existing or {})
    taken = {stem.lower() for stem in names.values()}
    for track in tracks:
        key = track_key(track)
        if key not in names:
            names[key] = _unique_stem(track, taken)
            taken.add(names[key].lower())
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
