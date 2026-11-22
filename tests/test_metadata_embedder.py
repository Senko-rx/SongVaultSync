import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TRACK = {
    "id": "abc123",
    "name": "Test Song",
    "artists": ["Artist One", "Artist Two"],
    "album": "Test Album",
    "album_cover_url": "https://i.scdn.co/image/test",
}


def _make_mp3(tmp_path: Path) -> Path:
    mp3 = tmp_path / "abc123.mp3"
    mp3.write_bytes(b"\xff\xfb" + b"\x00" * 256)
    return mp3


def test_embed_writes_title_and_artist(tmp_path):
    mp3 = _make_mp3(tmp_path)
    mock_tags_instance = MagicMock()

    with patch("metadata_embedder.ID3", return_value=mock_tags_instance), \
         patch("metadata_embedder.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        import metadata_embedder
        metadata_embedder.embed(mp3, TRACK)

    mock_tags_instance.save.assert_called_once()
    set_keys = [call.args[0] for call in mock_tags_instance.__setitem__.call_args_list]
    assert "TIT2" in set_keys
    assert "TPE1" in set_keys
    assert "TALB" in set_keys


def test_embed_continues_when_album_art_fetch_fails(tmp_path, capsys):
    mp3 = _make_mp3(tmp_path)

    with patch("metadata_embedder.ID3", return_value=MagicMock()), \
         patch("metadata_embedder.requests.get", side_effect=Exception("network error")):
        import metadata_embedder
        metadata_embedder.embed(mp3, TRACK)

    captured = capsys.readouterr()
    assert "Warning" in captured.out


def test_embed_skips_art_when_no_url(tmp_path):
    mp3 = _make_mp3(tmp_path)
    track_no_art = {**TRACK, "album_cover_url": ""}

    with patch("metadata_embedder.ID3", return_value=MagicMock()), \
         patch("metadata_embedder.requests.get") as mock_get:
        import metadata_embedder
        metadata_embedder.embed(mp3, track_no_art)

    mock_get.assert_not_called()


FULL_TRACK = {
    **TRACK,
    "album_cover_url": "",
    "album_artists": ["Album Artist"],
    "track_number": 7,
    "release_date": "2019-03-15",
    "isrc": "USRC17607839",
}


def test_embed_writes_extended_tags_readable_by_mutagen(tmp_path):
    from mutagen.id3 import ID3

    import metadata_embedder

    mp3 = _make_mp3(tmp_path)
    metadata_embedder.embed(mp3, FULL_TRACK)

    tags = ID3(str(mp3))
    assert str(tags["TPE2"]) == "Album Artist"
    assert str(tags["TRCK"]) == "7"
    assert str(tags["TDRC"]) == "2019-03-15"
    assert str(tags["TSRC"]) == "USRC17607839"


def test_embed_omits_extended_tags_when_fields_missing(tmp_path):
    # Older catalog.json exports don't carry these fields.
    from mutagen.id3 import ID3

    import metadata_embedder

    mp3 = _make_mp3(tmp_path)
    metadata_embedder.embed(mp3, {**TRACK, "album_cover_url": ""})

    tags = ID3(str(mp3))
    for frame in ("TPE2", "TRCK", "TDRC", "TSRC"):
        assert frame not in tags


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _make_opus(tmp_path: Path) -> Path:
    import subprocess

    path = tmp_path / "song.opus"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=1", "-c:a", "libopus", "-y", str(path)],
        check=True,
    )
    return path


@needs_ffmpeg
def test_embed_writes_vorbis_comments_for_opus(tmp_path):
    from mutagen.oggopus import OggOpus

    import metadata_embedder

    opus = _make_opus(tmp_path)
    metadata_embedder.embed(opus, FULL_TRACK)

    tags = OggOpus(str(opus))
    assert tags["title"] == ["Test Song"]
    assert tags["artist"] == ["Artist One", "Artist Two"]
    assert tags["albumartist"] == ["Album Artist"]
    assert tags["tracknumber"] == ["7"]
    assert tags["date"] == ["2019-03-15"]
    assert tags["isrc"] == ["USRC17607839"]


@needs_ffmpeg
def test_embed_adds_cover_picture_to_opus(tmp_path):
    from mutagen.oggopus import OggOpus

    import metadata_embedder

    opus = _make_opus(tmp_path)
    with patch("metadata_embedder.requests.get", return_value=_cover_response([b"\xff\xd8\xffjpeg"])):
        metadata_embedder.embed(opus, TRACK)

    assert "metadata_block_picture" in OggOpus(str(opus))


@pytest.mark.parametrize(
    "url",
    [
        "http://i.scdn.co/image/abc",  # not https
        "https://127.0.0.1:8080/admin",  # internal address
        "https://evil.example/cover.jpg",  # not Spotify's CDN
        "https://i.scdn.co.evil.example/x",  # suffix trick
        "file:///etc/passwd",
    ],
)
def test_cover_fetch_refuses_non_spotify_urls(url):
    import metadata_embedder

    with patch("metadata_embedder.requests.get") as mock_get:
        assert metadata_embedder._fetch_cover({"name": "x", "album_cover_url": url}) is None
    mock_get.assert_not_called()


def _cover_response(chunks):
    response = MagicMock()
    response.iter_content.return_value = iter(chunks)
    response.__enter__.return_value = response
    return response


def test_cover_fetch_accepts_spotify_jpeg_without_redirects():
    import metadata_embedder

    jpeg = b"\xff\xd8\xff" + b"0" * 10
    with patch("metadata_embedder.requests.get", return_value=_cover_response([jpeg])) as mock_get:
        cover = metadata_embedder._fetch_cover({"name": "x", "album_cover_url": "https://i.scdn.co/image/ab"})
    assert cover == (jpeg, "image/jpeg")
    assert mock_get.call_args.kwargs["allow_redirects"] is False


def test_cover_fetch_rejects_oversized_or_non_image_bodies():
    import metadata_embedder

    url = {"name": "x", "album_cover_url": "https://i.scdn.co/image/ab"}
    huge = [b"\xff\xd8\xff" + b"0" * (1024 * 1024)] * 6
    with patch("metadata_embedder.requests.get", return_value=_cover_response(huge)):
        assert metadata_embedder._fetch_cover(url) is None
    with patch("metadata_embedder.requests.get", return_value=_cover_response([b"<html>"])):
        assert metadata_embedder._fetch_cover(url) is None
