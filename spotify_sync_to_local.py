import base64
import os
import secrets
import urllib.parse
import webbrowser
from http.server import HTTPServer

import requests
from dotenv import load_dotenv

from errors import SpotifyAuthError
from handler import Handler
from settings import SPOTIFY_SCOPES
from spotify_client import SpotifyClient

load_dotenv()

REQUIRED_ENV_VARS = ("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")
TOKEN_URL = "https://accounts.spotify.com/api/token"
TOKEN_TIMEOUT_SECONDS = 30
DEFAULT_HTTP_PORT = 80


def load_credentials() -> tuple[str, str, str]:
    """Read Spotify app credentials from the environment, failing with every missing name."""
    values = {name: (os.environ.get(name) or "").strip() for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SpotifyAuthError(
            f"Missing required setting(s) in .env: {', '.join(missing)}. See .env.example."
        )
    return values["CLIENT_ID"], values["CLIENT_SECRET"], values["REDIRECT_URI"]


def callback_address(redirect_uri: str) -> tuple[str, int]:
    """Return the (host, port) the local callback server must listen on for REDIRECT_URI."""
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme != "http" or not parsed.hostname:
        raise SpotifyAuthError(
            f"REDIRECT_URI must be a plain http URL with a host, e.g. "
            f"http://127.0.0.1:8888/callback (got '{redirect_uri}')."
        )
    return parsed.hostname, parsed.port or DEFAULT_HTTP_PORT


class SpotifySyncToLocal:
    def __init__(self) -> None:
        self._client_id, self._client_secret, self._redirect_uri = load_credentials()
        self._callback_address = callback_address(self._redirect_uri)

    def _build_auth_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "scope": SPOTIFY_SCOPES,
            "state": state,
        }
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    def _wait_for_code(self) -> tuple[str, str]:
        state = secrets.token_urlsafe(16)
        server = HTTPServer(self._callback_address, Handler)
        server.auth_code = None
        server.expected_state = state

        webbrowser.open(self._build_auth_url(state))

        while server.auth_code is None:
            server.handle_request()

        return server.auth_code, state

    def _exchange_code(self, code: str) -> str:
        auth_header = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
        response = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
            },
            timeout=TOKEN_TIMEOUT_SECONDS,
        )
        try:
            token_info = response.json()
        except ValueError:
            token_info = {}
        if "access_token" not in token_info:
            detail = token_info.get("error_description") or token_info.get("error") or response.status_code
            raise SpotifyAuthError(f"Token exchange failed: {detail}")
        return token_info["access_token"]

    def get_access_token(self) -> str:
        code, _ = self._wait_for_code()
        access_token = self._exchange_code(code)
        print("Access token received!")
        return access_token

    def list_playlists(self, client: SpotifyClient) -> list[dict]:
        url = "https://api.spotify.com/v1/me/playlists?limit=50"
        playlists = []
        while url:
            data = client.get(url)
            for item in data["items"]:
                playlists.append({
                    "id": item["id"],
                    "name": item["name"],
                    "track_count": item["tracks"]["total"],
                    "owner": item["owner"]["display_name"],
                })
            url = data.get("next")
        return playlists

    def fetch_tracks(self, client: SpotifyClient, source: str) -> list[dict]:
        if source == "liked":
            url = "https://api.spotify.com/v1/me/tracks?limit=50"
        else:
            url = f"https://api.spotify.com/v1/playlists/{source}/tracks?limit=50"

        songs = []
        while url:
            data = client.get(url)
            for item in data["items"]:
                track = item.get("track")
                if track is None:
                    continue
                images = track.get("album", {}).get("images", [])
                songs.append({
                    "id": track["id"],
                    "name": track["name"],
                    "artists": [a["name"] for a in track["artists"]],
                    "album": track.get("album", {}).get("name", ""),
                    "album_cover_url": images[0]["url"] if images else "",
                    "duration_ms": track.get("duration_ms", 0),
                    "isrc": track.get("external_ids", {}).get("isrc", ""),
                })
            url = data.get("next")

        print(f"Fetched {len(songs)} tracks from '{source}'")
        return songs
