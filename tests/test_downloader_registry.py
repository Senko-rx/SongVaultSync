import pytest

from downloaders import DOWNLOADERS, get_downloader
from downloaders.ytdlp_downloader import YtDlpDownloader


def test_ytdlp_is_registered():
    assert "ytdlp" in DOWNLOADERS


def test_get_downloader_returns_ytdlp_instance():
    dl = get_downloader("ytdlp")
    assert isinstance(dl, YtDlpDownloader)


def test_get_downloader_raises_for_unknown_name():
    with pytest.raises(ValueError, match="Unknown downloader"):
        get_downloader("nonexistent")


def test_each_call_returns_fresh_instance():
    dl1 = get_downloader("ytdlp")
    dl2 = get_downloader("ytdlp")
    assert dl1 is not dl2
