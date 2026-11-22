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
