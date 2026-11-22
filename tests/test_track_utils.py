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


from track_utils import assign_filenames, safe_filename, track_key  # noqa: E402


def _song(track_id, name, artists=("Artist",)):
    return {"id": track_id, "name": name, "artists": list(artists)}


def test_safe_filename_replaces_forbidden_characters():
    assert safe_filename('AC/DC: "Back" <In> Black?*|\\') == "AC_DC_ _Back_ _In_ Black____"


def test_safe_filename_strips_trailing_dots_and_spaces():
    assert safe_filename("  Song...  ") == "Song"


def test_safe_filename_truncates_by_bytes_not_characters():
    # 255 bytes is the per-name limit on ext4; CJK characters are 3 bytes each in UTF-8.
    assert len(safe_filename("音" * 200).encode("utf-8")) <= 200
    assert len(safe_filename("x" * 500).encode("utf-8")) <= 200


def test_safe_filename_prefixes_windows_reserved_names():
    assert safe_filename("NUL") == "_NUL"
    assert safe_filename("com1") == "_com1"
    assert safe_filename("Console") == "Console"


def test_safe_filename_removes_invisible_and_bidi_characters():
    assert safe_filename("evil\u202egpj.mp3\u200b") == "evilgpj.mp3"
    assert safe_filename("line\nbreak") == "line_break"


def test_assign_filenames_uses_artist_and_title():
    names = assign_filenames([_song("a", "Song", ["Artist One", "Artist Two"])])
    assert names["a"] == "Artist One, Artist Two - Song"


def test_assign_filenames_suffixes_collisions_with_id():
    names = assign_filenames([_song("id_first", "Song"), _song("id_second", "Song")])
    assert names["id_first"] == "Artist - Song"
    assert names["id_second"] == "Artist - Song [id_secon]"


def test_assign_filenames_collision_is_case_insensitive():
    # Case-insensitive filesystems (macOS, Windows) treat these as the same file.
    names = assign_filenames([_song("a", "Song"), _song("b", "SONG")])
    assert names["a"] != names["b"]


def test_assign_filenames_falls_back_to_key_when_name_empty():
    names = assign_filenames([{"id": "abc", "name": "", "artists": []}])
    assert names["abc"] == "abc"


def test_track_key_prefers_id_then_name():
    assert track_key({"id": "abc", "name": "Song"}) == "abc"
    assert track_key({"id": None, "name": "Local Song"}) == "local:Local Song"


def test_tracks_without_id_but_different_artists_get_different_keys():
    a = {"id": None, "name": "Intro", "artists": ["Band A"]}
    b = {"id": None, "name": "Intro", "artists": ["Band B"]}
    assert track_key(a) != track_key(b)


def test_track_key_handles_missing_name():
    assert track_key({"id": None}) == "local:untitled"


def test_assign_filenames_keeps_existing_names_for_subset_runs():
    # Retrying only the second of two colliding tracks must not hand it the first one's file.
    first, second = _song("id_first", "Song"), _song("id_second", "Song")
    names = assign_filenames([first, second])
    assert assign_filenames([second], existing=names)["id_second"] == "Artist - Song [id_secon]"


def test_assign_filenames_new_track_avoids_names_already_taken():
    names = assign_filenames([_song("old", "Song")])
    later = assign_filenames([_song("new", "Song")], existing=names)
    assert later["new"] == "Artist - Song [new]"


def test_collision_suffix_survives_byte_limit():
    long_title = "x" * 400
    names = assign_filenames([_song("aaaa1111", long_title), _song("bbbb2222", long_title)])
    assert names["bbbb2222"].endswith("[bbbb2222]")
    assert len(names["bbbb2222"].encode("utf-8")) <= 200


def test_display_name_collapses_line_breaks():
    from track_utils import display_name

    assert display_name({"name": "Bad\nTitle\r#EXTINF", "artists": ["A"]}) == "A - Bad Title #EXTINF"
