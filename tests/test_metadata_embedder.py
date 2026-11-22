from pathlib import Path
from unittest.mock import MagicMock, patch

TRACK = {
    "id": "abc123",
    "name": "Test Song",
    "artists": ["Artist One", "Artist Two"],
    "album": "Test Album",
    "album_cover_url": "https://example.com/cover.jpg",
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
