"""Export a copy of the library laid out for older car stereos (--car).

Older head units (e.g. a 2012 Toyota Yaris) generally can't use playlist files but
can browse folders, read ID3v1/ID3v2.3 most reliably, and stop listing files past
fixed limits. So each playlist becomes a numbered folder of numbered, re-tagged copies.
"""

import json
import os
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TRCK

from track_utils import display_name, safe_filename, track_key

MARKER_FILE = ".songvaultsync-car.json"
MARKER_VERSION = 1
# Limits from Toyota owner's manuals of that era; other brands are similar or higher.
MAX_FILES_PER_FOLDER = 255
MAX_TOTAL_FOLDERS = 999  # including the root
MAX_TOTAL_FILES = 9999
MAX_NAME_BYTES = 100
_PUNCTUATION = str.maketrans({"–": "-", "—": "-", "‘": "'", "’": "'", "“": "'", "”": "'", "…": "..."})

Entry = tuple[str, str, int, int]  # (file name, source path, source mtime_ns, source size)
Plan = dict[str, list[tuple[dict, Path]]]  # folder name -> ordered (track, source file)


class CarExportError(Exception):
    pass


@dataclass
class CarReport:
    files_written: int = 0
    folders_unchanged: int = 0
    folders_removed: int = 0
    warnings: list[str] = field(default_factory=list)


def ascii_name(text: str, fallback: str = "Untitled") -> str:
    """Plain-ASCII, filesystem-safe name: accents dropped, typographic punctuation simplified."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_PUNCTUATION))
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    return safe_filename(" ".join(ascii_only.split()), MAX_NAME_BYTES) or fallback


def _plan(groups, available: dict[str, Path], max_per_folder: int) -> Plan:
    """One numbered folder per playlist (split when too big), tracks in playlist order."""
    width = max(2, len(str(len(groups))))
    plan: Plan = {}
    for number, (name, tracks) in enumerate(groups, start=1):
        seen: set[str] = set()
        items = []
        for track in tracks:
            key = track_key(track)
            if key in available and key not in seen:
                seen.add(key)
                items.append((track, available[key]))
        chunks = [items[i : i + max_per_folder] for i in range(0, len(items), max_per_folder)]
        base = f"{number:0{width}d} {ascii_name(name, 'Playlist')}"
        for part, chunk in enumerate(chunks, start=1):
            plan[base if len(chunks) == 1 else f"{base} ({part})"] = chunk
    return plan


def _entries(items: list[tuple[dict, Path]]) -> list[Entry]:
    entries = []
    for position, (track, source) in enumerate(items, start=1):
        stat = source.stat()
        file_name = f"{position:03d} {ascii_name(display_name(track), 'Track')}.mp3"
        entries.append((file_name, str(source.resolve()), stat.st_mtime_ns, stat.st_size))
    return entries


def _retag(path: Path, track: dict, position: int) -> None:
    """Replace the tags with a minimal ID3v2.3 + ID3v1 set; drops cover art."""
    tags = ID3()
    tags["TIT2"] = TIT2(encoding=1, text=track.get("name", ""))
    tags["TPE1"] = TPE1(encoding=1, text=", ".join(track.get("artists") or []))
    tags["TALB"] = TALB(encoding=1, text=track.get("album", ""))
    tags["TRCK"] = TRCK(encoding=0, text=str(position))  # playlist position: units often sort by it
    tags.save(str(path), v1=2, v2_version=3)


def _write_folder(folder: Path, items: list[tuple[dict, Path]], entries: list[Entry]) -> int:
    """Write a folder from scratch, in order: many units play in the order files were written."""
    folder.mkdir(parents=True)
    for position, ((track, source), (file_name, *_)) in enumerate(zip(items, entries, strict=True), start=1):
        partial = folder / f".{file_name}.part"
        shutil.copyfile(source, partial)
        _retag(partial, track, position)
        os.replace(partial, folder / file_name)
    return len(entries)


def _load_marker(car_dir: Path) -> dict[str, list[Entry]]:
    marker = car_dir / MARKER_FILE
    if marker.is_file():
        data = json.loads(marker.read_text(encoding="utf-8"))
        return {name: [tuple(e) for e in entries] for name, entries in data.get("folders", {}).items()}
    if car_dir.exists() and any(car_dir.iterdir()):
        raise CarExportError(
            f"{car_dir} is not empty and wasn't created by --car. "
            "Use an empty folder (e.g. a 'Music' folder on the stick) so nothing of yours gets touched."
        )
    return {}


def _save_marker(car_dir: Path, folders: dict[str, list[Entry]]) -> None:
    tmp = car_dir / f"{MARKER_FILE}.tmp"
    tmp.write_text(json.dumps({"version": MARKER_VERSION, "folders": folders}, indent=1), encoding="utf-8")
    os.replace(tmp, car_dir / MARKER_FILE)


def _check_conflicts(car_dir: Path, plan: Plan, owned: dict) -> None:
    """Fail before changing anything if a planned folder exists but isn't ours."""
    for name in plan:
        if name not in owned and (car_dir / name).exists():
            raise CarExportError(f"{car_dir / name} already exists and wasn't created by --car; rename or remove it.")


def _limit_warnings(plan: Plan, max_total_folders: int, max_total_files: int) -> list[str]:
    total_files = sum(len(items) for items in plan.values())
    warnings = []
    if len(plan) + 1 > max_total_folders:
        warnings.append(f"{len(plan)} folders exceeds the {max_total_folders} many car stereos can list.")
    if total_files > max_total_files:
        warnings.append(f"{total_files} files exceeds the {max_total_files} many car stereos can list.")
    return warnings


def export_car(
    groups,
    available: dict[str, Path],
    car_dir: Path,
    max_files_per_folder: int = MAX_FILES_PER_FOLDER,
    max_total_folders: int = MAX_TOTAL_FOLDERS,
    max_total_files: int = MAX_TOTAL_FILES,
) -> CarReport:
    """Sync car_dir to one numbered folder per playlist. Only folders it created are ever removed."""
    owned = _load_marker(car_dir)
    plan = _plan(groups, available, max_files_per_folder)
    _check_conflicts(car_dir, plan, owned)
    car_dir.mkdir(parents=True, exist_ok=True)
    report = CarReport(warnings=_limit_warnings(plan, max_total_folders, max_total_files))

    for stale in set(owned) - set(plan):
        shutil.rmtree(car_dir / stale, ignore_errors=True)
        del owned[stale]
        report.folders_removed += 1
    _save_marker(car_dir, owned)

    for name, items in plan.items():
        entries = _entries(items)
        folder = car_dir / name
        if owned.get(name) == entries and folder.is_dir():
            report.folders_unchanged += 1
            continue
        owned[name] = []  # "in progress": if interrupted, the next run sees a mismatch and rebuilds it
        _save_marker(car_dir, owned)
        shutil.rmtree(folder, ignore_errors=True)
        report.files_written += _write_folder(folder, items, entries)
        owned[name] = entries
        _save_marker(car_dir, owned)
    return report
