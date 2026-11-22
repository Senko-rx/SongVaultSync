from unittest.mock import MagicMock, patch

import pytest
from yt_dlp.utils import MaxDownloadsReached

from downloaders.ytdlp_downloader import YtDlpDownloader, duration_filter
from errors import DownloadError


def test_duration_filter_accepts_close_match():
    accept = duration_filter(expected_ms=200_000, tolerance_s=15)
    assert accept({"duration": 210}, incomplete=False) is None


def test_duration_filter_rejects_far_match_with_reason():
    accept = duration_filter(expected_ms=200_000, tolerance_s=15)
    reason = accept({"duration": 600, "title": "10 hour loop"}, incomplete=False)
    assert isinstance(reason, str) and "10 hour loop" in reason


def test_duration_filter_accepts_unknown_duration():
    accept = duration_filter(expected_ms=200_000, tolerance_s=15)
    assert accept({}, incomplete=False) is None


def _fake_ydl(out_dir, side_effect=None, create_file=True):
    ydl = MagicMock()

    def _download(urls):
        if create_file:
            (out_dir / "t1.webm").touch()
        if side_effect:
            raise side_effect

    ydl.download.side_effect = _download
    ctx = MagicMock()
    ctx.__enter__.return_value = ydl
    return ctx, ydl


def test_download_with_duration_searches_candidates_and_filters(tmp_path):
    ctx, ydl = _fake_ydl(tmp_path, side_effect=MaxDownloadsReached())
    with patch("downloaders.ytdlp_downloader.yt_dlp.YoutubeDL", return_value=ctx) as cls:
        result = YtDlpDownloader().download("A Song", "t1", tmp_path, duration_ms=200_000)

    opts = cls.call_args[0][0]
    assert callable(opts["match_filter"])
    assert opts["max_downloads"] == 1
    assert ydl.download.call_args[0][0][0].startswith("ytsearch5:")
    assert result == tmp_path / "t1.webm"


def test_download_without_duration_takes_first_result(tmp_path):
    ctx, ydl = _fake_ydl(tmp_path)
    with patch("downloaders.ytdlp_downloader.yt_dlp.YoutubeDL", return_value=ctx) as cls:
        YtDlpDownloader().download("A Song", "t1", tmp_path)

    assert "match_filter" not in cls.call_args[0][0]
    assert ydl.download.call_args[0][0][0].startswith("ytsearch1:")


def test_download_raises_when_no_candidate_matches_duration(tmp_path):
    ctx, _ = _fake_ydl(tmp_path, create_file=False)
    with patch("downloaders.ytdlp_downloader.yt_dlp.YoutubeDL", return_value=ctx):
        with pytest.raises(DownloadError, match="length"):
            YtDlpDownloader().download("A Song", "t1", tmp_path, duration_ms=200_000)
