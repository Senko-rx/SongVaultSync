from pathlib import Path

import pytest
from mutagen.id3 import APIC, ID3, TIT2

from car_export import MARKER_FILE, CarExportError, ascii_name, export_car


def _library_file(path: Path, title: str) -> Path:
    """A fake library mp3 tagged the way the main pipeline tags: ID3v2.4 with cover art."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfb" + b"\x00" * 512)
    tags = ID3()
    tags["TIT2"] = TIT2(encoding=3, text=title)
    tags["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=b"\xff\xd8\xff" + b"0" * 5000)
    tags.save(str(path))
    return path


def _track(track_id, name, artists=("Artist",)):
    return {"id": track_id, "name": name, "artists": list(artists), "album": "Album"}


@pytest.fixture
def library(tmp_path):
    tracks = [_track(f"t{i}", f"Song {i}") for i in range(5)]
    available = {
        t["id"]: _library_file(tmp_path / "mp3" / f"Artist - Song {i}.mp3", t["name"]) for i, t in enumerate(tracks)
    }
    return tracks, available


def _files(car: Path) -> list[str]:
    return sorted(str(p.relative_to(car)) for p in car.rglob("*.mp3"))


def test_each_playlist_becomes_a_numbered_folder_in_playlist_order(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Liked Songs", tracks[:2]), ("Road Trip", [tracks[4], tracks[2]])], available, car)
    assert _files(car) == [
        "01 Liked Songs/001 Artist - Song 0.mp3",
        "01 Liked Songs/002 Artist - Song 1.mp3",
        "02 Road Trip/001 Artist - Song 4.mp3",
        "02 Road Trip/002 Artist - Song 2.mp3",
    ]


def test_car_copies_use_id3v23_with_v1_no_art_and_playlist_track_numbers(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Mix", [tracks[3], tracks[1]])], available, car)

    copy = car / "01 Mix" / "002 Artist - Song 1.mp3"
    tags = ID3(str(copy))
    assert tags.version[:2] == (2, 3)
    assert not tags.getall("APIC")
    assert str(tags["TIT2"]) == "Song 1"
    assert str(tags["TRCK"]) == "2"
    assert copy.read_bytes()[-128:-125] == b"TAG"  # ID3v1 block at the end of the file


def test_library_files_are_not_modified(tmp_path, library):
    tracks, available = library
    before = available["t0"].read_bytes()
    export_car([("Mix", tracks[:1])], available, tmp_path / "car")
    assert available["t0"].read_bytes() == before


def test_large_playlists_are_split_into_folders_of_max_size(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Big", tracks)], available, car, max_files_per_folder=2)
    assert sorted(p.name for p in car.iterdir() if p.is_dir()) == ["01 Big (1)", "01 Big (2)", "01 Big (3)"]
    assert _files(car)[-1] == "01 Big (3)/001 Artist - Song 4.mp3"


def test_tracks_without_a_file_and_duplicates_are_skipped(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Mix", [tracks[0], _track("missing", "Gone"), tracks[0]])], available, car)
    assert _files(car) == ["01 Mix/001 Artist - Song 0.mp3"]


def test_names_are_plain_ascii():
    assert ascii_name("Beyoncé – Halo “Live”") == "Beyonce - Halo 'Live'"
    assert ascii_name("音楽", fallback="Track") == "Track"
    assert ascii_name('AC/DC: Back?') == "AC_DC_ Back_"


def test_refuses_to_write_into_a_non_empty_folder_it_did_not_create(tmp_path, library):
    tracks, available = library
    car = tmp_path / "stick"
    car.mkdir()
    (car / "holiday photos.jpg").write_bytes(b"precious")
    with pytest.raises(CarExportError, match="not empty"):
        export_car([("Mix", tracks[:1])], available, car)
    assert (car / "holiday photos.jpg").read_bytes() == b"precious"


def test_rerun_with_no_changes_rewrites_nothing(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Mix", tracks[:2])], available, car)
    report = export_car([("Mix", tracks[:2])], available, car)
    assert report.files_written == 0
    assert report.folders_unchanged == 1


def test_changed_playlist_folder_is_rebuilt_and_removed_playlists_deleted(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Mix", tracks[:2]), ("Old", tracks[2:3])], available, car)
    report = export_car([("Mix", [tracks[1], tracks[0], tracks[3]])], available, car)

    assert _files(car) == [
        "01 Mix/001 Artist - Song 1.mp3",
        "01 Mix/002 Artist - Song 0.mp3",
        "01 Mix/003 Artist - Song 3.mp3",
    ]
    assert report.folders_removed == 1
    assert (car / MARKER_FILE).exists()


def test_leaves_unknown_folders_alone_even_inside_its_own_export(tmp_path, library):
    tracks, available = library
    car = tmp_path / "car"
    export_car([("Mix", tracks[:1])], available, car)
    (car / "My Own Stuff").mkdir()
    (car / "My Own Stuff" / "song.mp3").write_bytes(b"mine")
    export_car([("Other", tracks[1:2])], available, car)
    assert (car / "My Own Stuff" / "song.mp3").read_bytes() == b"mine"


def test_warns_when_exceeding_device_limits(tmp_path, library):
    tracks, available = library
    report = export_car([("Mix", tracks)], available, tmp_path / "car", max_total_files=3)
    assert any("3" in warning and "files" in warning for warning in report.warnings)
