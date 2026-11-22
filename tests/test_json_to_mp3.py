import json
from pathlib import Path
from unittest.mock import patch

import pytest

from errors import ConversionError, DownloadError
from json_to_mp3 import JsonToMp3

TRACK = {"id": "t1", "name": "Song", "artists": ["Artist"], "duration_ms": 200_000}


class FakeDownloader:
    def __init__(self, fail=False):
        self.calls = []
        self._fail = fail

    def download(self, query, track_id, out_dir, duration_ms=None):
        self.calls.append((query, track_id, duration_ms))
        if self._fail:
            raise DownloadError("nope")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{track_id}.webm"
        path.write_bytes(b"audio")
        return path


def _fake_convert(src: Path, dst: Path, bitrate: str = "128k") -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(b"mp3")


@pytest.fixture
def songs_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "list.json"
    path.write_text(json.dumps([TRACK]), encoding="utf-8")
    return str(path)


def _run(songs_file, downloader, convert=_fake_convert, **kwargs):
    with patch("json_to_mp3.convert_audio", side_effect=convert), patch("json_to_mp3.embed"):
        orchestrator = JsonToMp3(downloader, **kwargs)
        return orchestrator.json_to_mp3(songs_file)


def test_names_mp3_by_artist_and_title(songs_file):
    available = _run(songs_file, FakeDownloader()).available
    assert available["t1"].name == "Artist - Song.mp3"
    assert available["t1"].exists()


def test_passes_duration_to_downloader(songs_file):
    downloader = FakeDownloader()
    _run(songs_file, downloader)
    assert downloader.calls[0][2] == 200_000


def test_skips_tracks_that_already_exist(songs_file):
    Path("mp3").mkdir()
    Path("mp3/Artist - Song.mp3").write_bytes(b"old")
    downloader = FakeDownloader()
    available = _run(songs_file, downloader).available
    assert downloader.calls == []
    assert "t1" in available


def test_renames_legacy_id_named_file_instead_of_downloading(songs_file):
    Path("mp3").mkdir()
    Path("mp3/t1.mp3").write_bytes(b"legacy")
    downloader = FakeDownloader()
    available = _run(songs_file, downloader).available
    assert downloader.calls == []
    assert available["t1"].read_bytes() == b"legacy"
    assert not Path("mp3/t1.mp3").exists()


def test_mp3_only_deletes_source_audio_after_conversion(songs_file):
    _run(songs_file, FakeDownloader(), mp3_only=True)
    assert not Path("webm/t1.webm").exists()


def test_keeps_source_audio_by_default(songs_file):
    _run(songs_file, FakeDownloader())
    assert Path("webm/t1.webm").exists()


def test_keeps_source_audio_when_conversion_fails_in_mp3_only_mode(songs_file):
    def _fail(src, dst, bitrate):
        raise ConversionError("bad")

    available = _run(songs_file, FakeDownloader(), convert=_fail, mp3_only=True).available
    assert Path("webm/t1.webm").exists()
    assert available == {}


def test_failed_download_is_not_available(songs_file):
    available = _run(songs_file, FakeDownloader(fail=True)).available
    assert available == {}


def test_opus_format_writes_opus_files_in_opus_dir(songs_file):
    available = _run(songs_file, FakeDownloader(), audio_format="opus").available
    assert available["t1"] == Path("opus") / "Artist - Song.opus"


def test_output_dir_holds_all_generated_folders(songs_file, tmp_path):
    out = tmp_path / "library"
    available = _run(songs_file, FakeDownloader(), output_dir=out).available
    assert available["t1"] == out / "mp3" / "Artist - Song.mp3"
    assert (out / "webm" / "t1.webm").exists()


def test_bitrate_is_passed_to_converter(songs_file):
    seen = {}

    def _convert(src, dst, bitrate):
        seen["bitrate"] = bitrate
        _fake_convert(src, dst)

    _run(songs_file, FakeDownloader(), convert=_convert, bitrate="256k")
    assert seen["bitrate"] == "256k"


def test_failed_tracks_are_returned_with_error(songs_file):
    result = _run(songs_file, FakeDownloader(fail=True))
    [failed] = result.failed
    assert failed["id"] == "t1"
    assert failed["error"] == "nope"


def _write_songs(path, count):
    songs = [{"id": f"t{i}", "name": f"Song {i}", "artists": ["Artist"]} for i in range(count)]
    Path(path).write_text(json.dumps(songs), encoding="utf-8")


def test_workers_download_concurrently(songs_file):
    import threading

    _write_songs(songs_file, 2)
    barrier = threading.Barrier(2, timeout=5)

    class BarrierDownloader(FakeDownloader):
        def download(self, *args, **kwargs):
            barrier.wait()  # only passes if both downloads are in flight at once
            return super().download(*args, **kwargs)

    result = _run(songs_file, BarrierDownloader(), workers=2)
    assert sorted(result.available) == ["t0", "t1"]


def test_parallel_run_reports_same_results_as_sequential(songs_file):
    _write_songs(songs_file, 6)
    result = _run(songs_file, FakeDownloader(), workers=3)
    assert sorted(result.available) == [f"t{i}" for i in range(6)]
    assert result.failed == []


def test_failed_conversion_leaves_no_partial_file(songs_file):
    def _partial_then_fail(src, dst, bitrate):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"half")
        raise ConversionError("killed")

    _run(songs_file, FakeDownloader(), convert=_partial_then_fail)
    assert list(Path("mp3").iterdir()) == []


def test_tagging_error_keeps_track_with_warning(songs_file, capsys):
    with patch("json_to_mp3.convert_audio", side_effect=_fake_convert), \
         patch("json_to_mp3.embed", side_effect=ValueError("corrupt header")):
        result = JsonToMp3(FakeDownloader()).json_to_mp3(songs_file)
    assert result.available["t1"].exists()
    captured = capsys.readouterr()
    assert "corrupt header" in captured.out + captured.err


def test_tracks_without_id_get_distinct_temp_names(songs_file):
    songs = [{"id": None, "name": "a/b", "artists": []}, {"id": None, "name": "a?b", "artists": []}]
    Path(songs_file).write_text(json.dumps(songs), encoding="utf-8")
    downloader = FakeDownloader()
    _run(songs_file, downloader)
    temp_names = [call[1] for call in downloader.calls]
    assert len(set(temp_names)) == 2


def test_legacy_rename_only_applies_to_spotify_ids(songs_file):
    # An ID-less track's "legacy" name is just its title, which may belong to another file.
    Path(songs_file).write_text(json.dumps([{"id": None, "name": "Song", "artists": ["X"]}]), encoding="utf-8")
    Path("mp3").mkdir()
    Path("mp3/Song.mp3").write_bytes(b"someone else")
    _run(songs_file, FakeDownloader())
    assert Path("mp3/Song.mp3").read_bytes() == b"someone else"


def test_unexpected_worker_error_is_reported_as_failure_not_crash(songs_file):
    class ExplodingDownloader(FakeDownloader):
        def download(self, *args, **kwargs):
            raise OSError("disk full")

    result = _run(songs_file, ExplodingDownloader(), workers=2)
    assert result.failed[0]["error"] == "OSError: disk full"


def test_file_names_are_remembered_across_runs(songs_file):
    a = {"id": "aaa", "name": "Song", "artists": ["Artist"]}
    b = {"id": "bbb", "name": "Song", "artists": ["Artist"]}
    Path(songs_file).write_text(json.dumps([a, b]), encoding="utf-8")
    first = _run(songs_file, FakeDownloader()).available

    Path(songs_file).write_text(json.dumps([b]), encoding="utf-8")  # e.g. --retry-failed or --source subset
    second = _run(songs_file, FakeDownloader()).available
    assert second["bbb"] == first["bbb"] != first["aaa"]
