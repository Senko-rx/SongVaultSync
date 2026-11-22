import pytest
import responses as responses_lib

from errors import SpotifyApiError
from spotify_client import SpotifyClient

URL = "https://api.spotify.com/v1/me/tracks"


@responses_lib.activate
def test_success_on_first_attempt():
    responses_lib.add(responses_lib.GET, URL, json={"items": []}, status=200)
    client = SpotifyClient("token")
    data = client.get(URL)
    assert data == {"items": []}


@responses_lib.activate
def test_retries_on_429_and_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    responses_lib.add(responses_lib.GET, URL, status=429, headers={"Retry-After": "1"})
    responses_lib.add(responses_lib.GET, URL, json={"items": []}, status=200)
    client = SpotifyClient("token")
    data = client.get(URL)
    assert data == {"items": []}
    assert len(responses_lib.calls) == 2


@responses_lib.activate
def test_retries_on_500_with_backoff(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    responses_lib.add(responses_lib.GET, URL, status=500)
    responses_lib.add(responses_lib.GET, URL, status=500)
    responses_lib.add(responses_lib.GET, URL, json={"ok": True}, status=200)
    client = SpotifyClient("token")
    data = client.get(URL)
    assert data == {"ok": True}


@responses_lib.activate
def test_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    for _ in range(10):
        responses_lib.add(responses_lib.GET, URL, status=500)
    client = SpotifyClient("token")
    with pytest.raises(SpotifyApiError):
        client.get(URL)


@responses_lib.activate
def test_raises_immediately_on_4xx():
    responses_lib.add(responses_lib.GET, URL, status=401, json={"error": "unauthorized"})
    client = SpotifyClient("token")
    with pytest.raises(SpotifyApiError):
        client.get(URL)
