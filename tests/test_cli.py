from pathlib import Path

import pytest

from cli import build_parser


def _parse(*argv):
    return build_parser().parse_args(list(argv))


def test_defaults():
    args = _parse()
    assert args.output_dir == Path(".")
    assert args.format == "mp3"
    assert args.bitrate == "128k"


def test_output_options_are_parsed():
    args = _parse("--output-dir", "~/Music", "--format", "opus", "--bitrate", "192k")
    assert args.output_dir == Path("~/Music").expanduser()
    assert args.format == "opus"
    assert args.bitrate == "192k"


@pytest.mark.parametrize("bad", ["192", "fast", "5k", "9999k", "-128k"])
def test_rejects_invalid_bitrate(bad, capsys):
    with pytest.raises(SystemExit):
        _parse("--bitrate", bad)
    assert "bitrate" in capsys.readouterr().err


def test_rejects_unknown_format():
    with pytest.raises(SystemExit):
        _parse("--format", "flac")


def test_retry_failed_cannot_be_combined_with_other_sources():
    with pytest.raises(SystemExit):
        _parse("--retry-failed", "--all")


def test_workers_default_and_range():
    assert _parse().workers == 1
    assert _parse("--workers", "4").workers == 4
    for bad in ("0", "9", "x"):
        with pytest.raises(SystemExit):
            _parse("--workers", bad)


def test_source_accepts_liked_and_spotify_ids():
    assert _parse("--source", "liked", "--source", "37i9dQZF1DXcBWIGoYBM5M").sources == [
        "liked",
        "37i9dQZF1DXcBWIGoYBM5M",
    ]


@pytest.mark.parametrize("bad", ["../me/tracks", "abc?x=1", "https://open.spotify.com/playlist/x"])
def test_source_rejects_non_ids(bad):
    with pytest.raises(SystemExit):
        _parse("--source", bad)
