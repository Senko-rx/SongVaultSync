from pathlib import Path

import requests
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, TSRC, ID3NoHeaderError


def _set_optional_frames(tags: ID3, track_meta: dict) -> None:
    """Write frames only when the track has the data; older catalog exports lack these fields."""
    optional = {
        "TPE2": (TPE2, "; ".join(track_meta.get("album_artists") or [])),
        "TRCK": (TRCK, str(track_meta.get("track_number") or "")),
        "TDRC": (TDRC, track_meta.get("release_date") or ""),
        "TSRC": (TSRC, track_meta.get("isrc") or ""),
    }
    for key, (frame, value) in optional.items():
        if value:
            tags[key] = frame(encoding=3, text=value)


def embed(mp3_path: Path, track_meta: dict) -> None:
    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=track_meta.get("name", ""))
    tags["TPE1"] = TPE1(encoding=3, text="; ".join(track_meta.get("artists", [])))
    tags["TALB"] = TALB(encoding=3, text=track_meta.get("album", ""))
    _set_optional_frames(tags, track_meta)

    cover_url = track_meta.get("album_cover_url", "")
    if cover_url:
        try:
            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()
            tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=response.content,
            )
        except Exception as exc:
            print(f"  Warning: could not embed album art for '{track_meta.get('name')}': {exc}")

    tags.save(str(mp3_path))
