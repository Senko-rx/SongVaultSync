from pathlib import Path
import requests
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError


def embed(mp3_path: Path, track_meta: dict) -> None:
    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=track_meta.get("name", ""))
    tags["TPE1"] = TPE1(encoding=3, text="; ".join(track_meta.get("artists", [])))
    tags["TALB"] = TALB(encoding=3, text=track_meta.get("album", ""))

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
