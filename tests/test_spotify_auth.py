import pytest

from errors import SpotifyAuthError
from spotify_sync_to_local import SpotifySyncToLocal, callback_address, load_credentials

ENV = {
    "CLIENT_ID": "id",
    "CLIENT_SECRET": "secret",
    "REDIRECT_URI": "http://127.0.0.1:8888/callback",
}


def _set_env(monkeypatch, values):
    for key in ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_load_credentials_returns_values(monkeypatch):
    _set_env(monkeypatch, ENV)
    assert load_credentials() == ("id", "secret", "http://127.0.0.1:8888/callback")


def test_load_credentials_names_every_missing_variable(monkeypatch):
    _set_env(monkeypatch, {"CLIENT_ID": "id"})
    with pytest.raises(SpotifyAuthError) as exc:
        load_credentials()
    assert "CLIENT_SECRET" in str(exc.value)
    assert "REDIRECT_URI" in str(exc.value)


def test_load_credentials_treats_blank_as_missing(monkeypatch):
    _set_env(monkeypatch, {**ENV, "CLIENT_SECRET": "  "})
    with pytest.raises(SpotifyAuthError, match="CLIENT_SECRET"):
        load_credentials()


def test_sync_init_fails_fast_without_credentials(monkeypatch):
    _set_env(monkeypatch, {})
    with pytest.raises(SpotifyAuthError):
        SpotifySyncToLocal()


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("http://127.0.0.1:8888/callback", ("127.0.0.1", 8888)),
        ("http://localhost:9000/cb", ("localhost", 9000)),
        ("http://127.0.0.1/callback", ("127.0.0.1", 80)),
    ],
)
def test_callback_address_parses_redirect_uri(uri, expected):
    assert callback_address(uri) == expected


@pytest.mark.parametrize("uri", ["https://127.0.0.1:8888/callback", "not a uri", "http:///callback"])
def test_callback_address_rejects_unusable_uri(uri):
    with pytest.raises(SpotifyAuthError):
        callback_address(uri)


@pytest.mark.parametrize("uri", ["http://0.0.0.0:8888/callback", "http://192.168.1.5:8888/callback"])
def test_callback_address_must_be_loopback(uri):
    with pytest.raises(SpotifyAuthError, match="127.0.0.1"):
        callback_address(uri)
