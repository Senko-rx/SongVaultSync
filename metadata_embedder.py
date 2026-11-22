import base64
from pathlib import Path

import requests
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, TSRC, ID3NoHeaderError
from mutagen.oggopus import OggOpus

COVER_TIMEOUT_SECONDS = 10
FRONT_COVER = 3  # picture type for "Cover (front)" in both ID3 and FLAC/Vorbis


def _fetch_cover(track_meta: dict) -> bytes | None:
    """Download album art; a failure only costs the cover, never the whole track."""
    cover_url = track_meta.get("album_cover_url", "")
    if not cover_url:
        return None
    try:
        response = requests.get(cover_url, timeout=COVER_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        print(f"  Warning: could not embed album art for '{track_meta.get('name')}': {exc}")
        return None


def _optional_fields(track_meta: dict) -> dict[str, str]:
    """Fields older catalog exports may lack; only non-empty ones are written."""
    fields = {
        "albumartist": "; ".join(track_meta.get("album_artists") or []),
        "tracknumber": str(track_meta.get("track_number") or ""),
        "date": track_meta.get("release_date") or "",
        "isrc": track_meta.get("isrc") or "",
    }
    return {key: value for key, value in fields.items() if value}


_ID3_FRAMES = {
    "albumartist": ("TPE2", TPE2),
    "tracknumber": ("TRCK", TRCK),
    "date": ("TDRC", TDRC),
    "isrc": ("TSRC", TSRC),
}


def _embed_id3(path: Path, track_meta: dict) -> None:
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=track_meta.get("name", ""))
    tags["TPE1"] = TPE1(encoding=3, text="; ".join(track_meta.get("artists", [])))
    tags["TALB"] = TALB(encoding=3, text=track_meta.get("album", ""))
    for field, value in _optional_fields(track_meta).items():
        key, frame = _ID3_FRAMES[field]
        tags[key] = frame(encoding=3, text=value)

    cover = _fetch_cover(track_meta)
    if cover:
        tags["APIC"] = APIC(encoding=3, mime="image/jpeg", type=FRONT_COVER, desc="Cover", data=cover)
    tags.save(str(path))


def _embed_vorbis(path: Path, track_meta: dict) -> None:
    audio = OggOpus(str(path))
    audio["title"] = track_meta.get("name", "")
    audio["artist"] = list(track_meta.get("artists", []))
    audio["album"] = track_meta.get("album", "")
    for field, value in _optional_fields(track_meta).items():
        audio[field] = value

    cover = _fetch_cover(track_meta)
    if cover:
        picture = Picture()
        picture.type, picture.mime, picture.desc, picture.data = FRONT_COVER, "image/jpeg", "Cover", cover
        audio["metadata_block_picture"] = base64.b64encode(picture.write()).decode("ascii")
    audio.save()


def embed(path: Path, track_meta: dict) -> None:
    """Write tags and cover art, choosing ID3 (.mp3) or Vorbis comments (.opus) by extension."""
    if path.suffix.lower() == ".opus":
        _embed_vorbis(path, track_meta)
    else:
        _embed_id3(path, track_meta)
