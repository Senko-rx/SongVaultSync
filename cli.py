"""Command-line interface definition for songvaultsync."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SongVaultSync: sync your Spotify playlists to local mp3 files."
    )
    parser.add_argument(
        "--from-catalog",
        metavar="FILE",
        help="Skip Spotify auth and download from an existing catalog.json export.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        metavar="PLAYLIST_ID|liked",
        help="Source to download: 'liked' or a Spotify playlist ID. Repeatable.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download liked songs and all playlists.",
    )
    parser.add_argument(
        "--downloader",
        default="ytdlp",
        help="Downloader backend to use (default: ytdlp).",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip embedding metadata and album art into mp3 files.",
    )
    parser.add_argument(
        "--mp3-only",
        action="store_true",
        help="Delete the downloaded source audio after converting, keeping only the mp3.",
    )
    return parser
