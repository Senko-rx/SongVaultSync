"""Write .m3u8 playlist files that point at the downloaded mp3s with relative paths."""

import os
from pathlib import Path

from track_utils import display_name, safe_filename, track_key

TrackGroup = tuple[str, list[dict]]


def _unique_stem(name: str, used: set[str]) -> str:
    base = safe_filename(name) or "Playlist"
    stem, counter = base, 2
    while stem.lower() in used:
        stem = f"{base} ({counter})"
        counter += 1
    used.add(stem.lower())
    return stem


def _entry(track: dict, mp3: Path, playlists_dir: Path) -> list[str]:
    seconds = round((track.get("duration_ms") or 0) / 1000) or -1
    relative = Path(os.path.relpath(mp3, playlists_dir)).as_posix()
    return [f"#EXTINF:{seconds},{display_name(track)}", relative]


def write_playlists(groups: list[TrackGroup], available: dict[str, Path], playlists_dir: Path) -> list[Path]:
    """Write one playlist per group, listing only tracks that have an mp3. Returns written paths."""
    playlists_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used: set[str] = set()
    for name, tracks in groups:
        lines = ["#EXTM3U"]
        for track in tracks:
            mp3 = available.get(track_key(track))
            if mp3 is not None:
                lines += _entry(track, mp3, playlists_dir)
        if len(lines) == 1:
            continue
        path = playlists_dir / f"{_unique_stem(name, used)}.m3u8"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written
