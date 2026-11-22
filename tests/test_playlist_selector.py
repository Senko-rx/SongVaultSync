from unittest.mock import patch

from playlist_selector import select_sources

PLAYLISTS = [
    {"id": "pl1", "name": "Chill Vibes", "track_count": 42, "owner": "me"},
    {"id": "pl2", "name": "Workout", "track_count": 30, "owner": "me"},
    {"id": "pl3", "name": "Focus", "track_count": 15, "owner": "me"},
]


def test_select_all():
    with patch("builtins.input", return_value="all"):
        result = select_sources(PLAYLISTS)
    assert result == ["liked", "pl1", "pl2", "pl3"]


def test_select_liked_only():
    with patch("builtins.input", return_value="0"):
        result = select_sources(PLAYLISTS)
    assert result == ["liked"]


def test_select_multiple_playlists():
    with patch("builtins.input", return_value="1,3"):
        result = select_sources(PLAYLISTS)
    assert result == ["pl1", "pl3"]


def test_select_liked_and_playlist():
    with patch("builtins.input", return_value="0,2"):
        result = select_sources(PLAYLISTS)
    assert result == ["liked", "pl2"]


def test_invalid_then_valid(capsys):
    inputs = iter(["abc", "1"])
    with patch("builtins.input", side_effect=inputs):
        result = select_sources(PLAYLISTS)
    assert result == ["pl1"]
    captured = capsys.readouterr()
    assert "Invalid" in captured.out


def test_out_of_range_then_valid(capsys):
    inputs = iter(["99", "0"])
    with patch("builtins.input", side_effect=inputs):
        result = select_sources(PLAYLISTS)
    assert result == ["liked"]
    captured = capsys.readouterr()
    assert "Invalid" in captured.out
