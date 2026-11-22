import json
import sys

from car_export import CarExportError, export_car
from cli import parse_args
from converter import ensure_ffmpeg
from downloaders import get_downloader
from errors import SpotifyAuthError
from json_to_mp3 import JsonToMp3
from playlist_writer import write_playlists
from settings import PLAYLISTS_DIR
from sources import TrackGroup, fetch_spotify_groups, load_catalog_groups, load_failed_groups, save_failed
from track_utils import dedupe_tracks, track_key

LIST_FILE = "list_data.json"
FAILED_FILE = "failed.json"


def _collect_groups(args) -> list[TrackGroup]:
    if args.retry_failed:
        return load_failed_groups(args.output_dir / FAILED_FILE)
    if args.from_catalog:
        print(f"Loading tracks from {args.from_catalog}")
        return load_catalog_groups(args.from_catalog)
    return fetch_spotify_groups(args.sources, args.all)


def main() -> None:
    args = parse_args()
    ensure_ffmpeg()

    groups = _collect_groups(args)
    all_songs = dedupe_tracks(tracks for _, tracks in groups)
    print(f"\nTotal unique tracks: {len(all_songs)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    list_file = args.output_dir / LIST_FILE
    with open(list_file, "w", encoding="utf-8") as f:
        json.dump(all_songs, f, indent=2)

    orchestrator = JsonToMp3(
        get_downloader(args.downloader),
        embed_metadata=not args.no_metadata,
        mp3_only=args.mp3_only,
        output_dir=args.output_dir,
        audio_format=args.format,
        bitrate=args.bitrate,
        workers=args.workers,
    )
    result = orchestrator.json_to_mp3(str(list_file))

    failed_file = args.output_dir / FAILED_FILE
    save_failed(failed_file, result.failed, attempted_keys={track_key(t) for t in all_songs})
    if result.failed:
        print(f"Failed tracks saved to {failed_file}. Retry them with --retry-failed.")

    if args.retry_failed:
        print(
            "Playlists and the car export are not rebuilt on retry; "
            "rerun your usual sync to refresh them (existing files are skipped)."
        )
        return
    playlists_dir = args.output_dir / PLAYLISTS_DIR
    written = write_playlists(groups, result.available, playlists_dir)
    print(f"Wrote {len(written)} playlist file(s) to {playlists_dir}")
    if args.car is not None:
        _export_for_car(groups, result.available, args.car)


def _export_for_car(groups: list[TrackGroup], available: dict, car_dir) -> None:
    print(f"\nExporting car copy to {car_dir} ...")
    report = export_car(groups, available, car_dir)
    print(
        f"Car export: {report.files_written} file(s) written, {report.folders_unchanged} folder(s) unchanged, "
        f"{report.folders_removed} removed."
    )
    for warning in report.warnings:
        print(f"  Warning: {warning}")


if __name__ == "__main__":
    try:
        main()
    except (SpotifyAuthError, FileNotFoundError, CarExportError) as exc:
        sys.exit(f"Error: {exc}")
