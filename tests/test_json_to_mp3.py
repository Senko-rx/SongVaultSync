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
        return orchestrator, orchestrator.json_to_mp3(songs_file)


def test_names_mp3_by_artist_and_title(songs_file):
    orch, available = _run(songs_file, FakeDownloader())
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
    _, available = _run(songs_file, downloader)
    assert downloader.calls == []
    assert "t1" in available


def test_renames_legacy_id_named_file_instead_of_downloading(songs_file):
    Path("mp3").mkdir()
    Path("mp3/t1.mp3").write_bytes(b"legacy")
    downloader = FakeDownloader()
    _, available = _run(songs_file, downloader)
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

    _, available = _run(songs_file, FakeDownloader(), convert=_fail, mp3_only=True)
    assert Path("webm/t1.webm").exists()
    assert available == {}


def test_failed_download_is_not_available(songs_file):
    _, available = _run(songs_file, FakeDownloader(fail=True))
    assert available == {}


def test_opus_format_writes_opus_files_in_opus_dir(songs_file):
    _, available = _run(songs_file, FakeDownloader(), audio_format="opus")
    assert available["t1"] == Path("opus") / "Artist - Song.opus"


def test_output_dir_holds_all_generated_folders(songs_file, tmp_path):
    out = tmp_path / "library"
    _, available = _run(songs_file, FakeDownloader(), output_dir=out)
    assert available["t1"] == out / "mp3" / "Artist - Song.mp3"
    assert (out / "webm" / "t1.webm").exists()


def test_bitrate_is_passed_to_converter(songs_file):
    seen = {}

    def _convert(src, dst, bitrate):
        seen["bitrate"] = bitrate
        _fake_convert(src, dst)

    _run(songs_file, FakeDownloader(), convert=_convert, bitrate="256k")
    assert seen["bitrate"] == "256k"
