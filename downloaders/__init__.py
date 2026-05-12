from downloaders.ytdlp_downloader import YtDlpDownloader

DOWNLOADERS = {
    "ytdlp": YtDlpDownloader,
}


def get_downloader(name: str, mp3_only: bool = False):
    if name not in DOWNLOADERS:
        raise ValueError(f"Unknown downloader '{name}'. Available: {list(DOWNLOADERS)}")
    return DOWNLOADERS[name](mp3_only=mp3_only)
