import json

from sources import LIKED_SONGS_NAME, load_catalog_groups, source_name


def test_load_catalog_groups_keeps_playlist_names(tmp_path):
    catalog = {
        "liked_songs": {"tracks": [{"id": "a", "name": "A"}]},
        "playlists": [{"name": "Road Trip", "tracks": [{"id": "b", "name": "B"}]}],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")

    groups = load_catalog_groups(str(path))

    assert [name for name, _ in groups] == [LIKED_SONGS_NAME, "Road Trip"]
    assert groups[1][1] == [{"id": "b", "name": "B"}]


def test_load_catalog_groups_tolerates_missing_sections(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text("{}", encoding="utf-8")
    assert load_catalog_groups(str(path)) == [(LIKED_SONGS_NAME, [])]


def test_source_name_resolves_ids():
    names = {"pl1": "Chill"}
    assert source_name("liked", names) == LIKED_SONGS_NAME
    assert source_name("pl1", names) == "Chill"
    assert source_name("unknown", names) == "unknown"


def test_failed_tracks_round_trip_without_error_field(tmp_path):
    from sources import RETRY_GROUP_NAME, load_failed_groups, save_failed

    path = tmp_path / "failed.json"
    save_failed(path, [{"id": "a", "name": "A", "error": "timeout"}])

    [(name, tracks)] = load_failed_groups(path)
    assert name == RETRY_GROUP_NAME
    assert tracks == [{"id": "a", "name": "A"}]


def test_save_failed_with_no_failures_removes_stale_file(tmp_path):
    from sources import save_failed

    path = tmp_path / "failed.json"
    path.write_text("[]", encoding="utf-8")
    save_failed(path, [])
    assert not path.exists()


def test_load_failed_groups_explains_missing_file(tmp_path):
    import pytest

    from sources import load_failed_groups

    with pytest.raises(FileNotFoundError, match="Nothing to retry"):
        load_failed_groups(tmp_path / "failed.json")
