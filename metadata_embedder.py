import base64
import urllib.parse
from pathlib import Path

import requests
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, TSRC, ID3NoHeaderError
from mutagen.oggopus import OggOpus
from tqdm import tqdm

COVER_TIMEOUT_SECONDS = 10
FRONT_COVER = 3  # picture type for "Cover (front)" in both ID3 and FLAC/Vorbis
MAX_COVER_BYTES = 5 * 1024 * 1024
# Spotify serves album art from these CDNs. Anything else (e.g. from a hand-edited
# catalog.json) is refused, so a crafted URL can't make us probe internal services.
COVER_HOST_SUFFIXES = (".scdn.co", ".spotifycdn.com")
IMAGE_SIGNATURES = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png"}


def _warn(track_meta: dict, message: str) -> None:
    tqdm.write(f"  Warning: album art for '{track_meta.get('name')}': {message}")


def _is_trusted_cover_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host.endswith(COVER_HOST_SUFFIXES)


def _read_capped(response) -> bytes | None:
    data = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        data.extend(chunk)
        if len(data) > MAX_COVER_BYTES:
            return None
    return bytes(data)


def _fetch_cover(track_meta: dict) -> tuple[bytes, str] | None:
    """Download album art as (bytes, mime type). Any problem only costs the cover."""
    url = track_meta.get("album_cover_url", "")
    if not url:
        return None
    if not _is_trusted_cover_url(url):
        _warn(track_meta, f"skipping untrusted URL {url!r}")
        return None
    try:
        with requests.get(url, timeout=COVER_TIMEOUT_SECONDS, stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            data = _read_capped(response)
    except Exception as exc:
        _warn(track_meta, str(exc))
        return None
    if data is None:
        _warn(track_meta, f"larger than {MAX_COVER_BYTES} bytes")
        return None
    mime = next((m for sig, m in IMAGE_SIGNATURES.items() if data.startswith(sig)), None)
    if mime is None:
        _warn(track_meta, "response is not a JPEG or PNG image")
        return None
    return data, mime


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
        data, mime = cover
        tags["APIC"] = APIC(encoding=3, mime=mime, type=FRONT_COVER, desc="Cover", data=data)
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
        picture.data, picture.mime = cover
        picture.type, picture.desc = FRONT_COVER, "Cover"
        audio["metadata_block_picture"] = base64.b64encode(picture.write()).decode("ascii")
    audio.save()


def embed(path: Path, track_meta: dict) -> None:
    """Write tags and cover art, choosing ID3 (.mp3) or Vorbis comments (.opus) by extension."""
    if path.suffix.lower() == ".opus":
        _embed_vorbis(path, track_meta)
    else:
        _embed_id3(path, track_meta)
