import pytest

from spotify_sync_to_local import SpotifySyncToLocal

ITEM = {
    "track": {
        "id": "t1",
        "name": "Song",
        "artists": [{"name": "A"}, {"name": "B"}],
        "album": {
            "name": "Album",
            "images": [{"url": "https://img/1.jpg"}],
            "artists": [{"name": "A"}],
            "release_date": "2019-03-15",
        },
        "duration_ms": 200000,
        "track_number": 7,
        "external_ids": {"isrc": "USRC17607839"},
    }
}


class FakeClient:
    def __init__(self, pages):
        self._pages = list(pages)

    def get(self, url, params=None):
        return self._pages.pop(0)


@pytest.fixture
def sync(monkeypatch):
    monkeypatch.setenv("CLIENT_ID", "id")
    monkeypatch.setenv("CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")
    return SpotifySyncToLocal()


def test_fetch_tracks_captures_extended_metadata(sync):
    client = FakeClient([{"items": [ITEM], "next": None}])
    [track] = sync.fetch_tracks(client, "liked")
    assert track["album_artists"] == ["A"]
    assert track["track_number"] == 7
    assert track["release_date"] == "2019-03-15"
    assert track["isrc"] == "USRC17607839"
    assert track["duration_ms"] == 200000


def test_fetch_tracks_follows_pagination_and_skips_null_tracks(sync):
    client = FakeClient([
        {"items": [ITEM, {"track": None}], "next": "page2"},
        {"items": [ITEM], "next": None},
    ])
    assert len(sync.fetch_tracks(client, "playlist123")) == 2


def test_fetch_tracks_skips_podcast_episodes(sync):
    episode = {"track": {"type": "episode", "id": "e1", "name": "Episode", "duration_ms": 1}}
    client = FakeClient([{"items": [episode, ITEM], "next": None}])
    assert [t["id"] for t in sync.fetch_tracks(client, "playlist123")] == ["t1"]
