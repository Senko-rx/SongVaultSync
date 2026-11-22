from track_utils import dedupe_tracks


def _t(track_id, name="Song"):
    return {"id": track_id, "name": name}


def test_dedupe_keeps_first_occurrence_order():
    groups = [[_t("a"), _t("b")], [_t("b"), _t("c")]]
    assert [t["id"] for t in dedupe_tracks(groups)] == ["a", "b", "c"]


def test_dedupe_keeps_all_tracks_without_id():
    # Spotify local files have id=None; they must not collapse into one.
    groups = [[_t(None, "Local 1"), _t(None, "Local 2")]]
    assert [t["name"] for t in dedupe_tracks(groups)] == ["Local 1", "Local 2"]


def test_dedupe_empty_input():
    assert dedupe_tracks([]) == []
