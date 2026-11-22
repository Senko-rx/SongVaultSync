from pathlib import Path

from playlist_writer import write_playlists


def _track(track_id, name, duration_ms=180_000):
    return {"id": track_id, "name": name, "artists": ["Artist"], "duration_ms": duration_ms}


def test_writes_m3u8_with_relative_paths_and_extinf(tmp_path):
    mp3_dir = tmp_path / "mp3"
    available = {"a": mp3_dir / "Artist - One.mp3"}
    [path] = write_playlists([("My Mix", [_track("a", "One")])], available, tmp_path / "playlists")

    assert path.name == "My Mix.m3u8"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#EXTM3U"
    assert lines[1] == "#EXTINF:180,Artist - One"
    assert lines[2] == "../mp3/Artist - One.mp3"


def test_skips_tracks_without_a_file(tmp_path):
    available = {"a": tmp_path / "mp3" / "a.mp3"}
    tracks = [_track("a", "One"), _track("missing", "Two")]
    [path] = write_playlists([("Mix", tracks)], available, tmp_path / "playlists")
    assert "Two" not in path.read_text(encoding="utf-8")


def test_skips_playlists_with_no_available_tracks(tmp_path):
    assert write_playlists([("Empty", [_track("x", "X")])], {}, tmp_path / "playlists") == []


def test_sanitizes_and_deduplicates_playlist_names(tmp_path):
    available = {"a": tmp_path / "mp3" / "a.mp3"}
    groups = [("Rock/Metal", [_track("a", "One")]), ("Rock/Metal", [_track("a", "One")])]
    paths = write_playlists(groups, available, tmp_path / "playlists")
    assert [p.name for p in paths] == ["Rock_Metal.m3u8", "Rock_Metal (2).m3u8"]


def test_overwrites_existing_playlist_on_rerun(tmp_path):
    available = {"a": Path(tmp_path / "mp3" / "a.mp3")}
    out = tmp_path / "playlists"
    write_playlists([("Mix", [_track("a", "One")])], available, out)
    write_playlists([("Mix", [_track("a", "One")])], available, out)
    assert [p.name for p in out.iterdir()] == ["Mix.m3u8"]


def test_extinf_label_omits_dash_when_track_has_no_artists(tmp_path):
    track = {"id": None, "name": "Local File", "artists": [], "duration_ms": 2000}
    available = {"local:Local File": tmp_path / "mp3" / "Local File.mp3"}
    [path] = write_playlists([("Mix", [track])], available, tmp_path / "playlists")
    assert "#EXTINF:2,Local File" in path.read_text(encoding="utf-8").splitlines()
