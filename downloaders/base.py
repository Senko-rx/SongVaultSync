from pathlib import Path
from typing import Protocol


class Downloader(Protocol):
    def download(self, query: str, track_id: str, out_dir: Path) -> Path:
        ...
