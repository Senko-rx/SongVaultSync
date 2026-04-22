from http.server import HTTPServer
import requests
import base64
import urllib.parse
import json
import os
import secrets
import webbrowser
from dotenv import load_dotenv
from handler import Handler
from spotify_client import SpotifyClient
from settings import SPOTIFY_SCOPES

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")


class SpotifySyncToLocal:

    def _build_auth_url(self, state: str) -> str:
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SPOTIFY_SCOPES,
            "state": state,
        }
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    def _wait_for_code(self) -> tuple[str, str]:
        state = secrets.token_urlsafe(16)
        server = HTTPServer(("127.0.0.1", 8888), Handler)
        server.auth_code = None
        server.expected_state = state

        webbrowser.open(self._build_auth_url(state))

        while server.auth_code is None:
            server.handle_request()

        return server.auth_code, state

    def _exchange_code(self, code: str) -> str:
        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
        )
        token_info = response.json()
        if "access_token" not in token_info:
            raise RuntimeError(f"Token exchange failed: {token_info}")
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

    def sync(self, sources: list[str] | None = None) -> list[dict]:
        access_token = self.get_access_token()
        client = SpotifyClient(access_token)

        if sources is None:
            sources = ["liked"]

        all_songs: list[dict] = []
        seen_ids: set[str] = set()
        for source in sources:
            for track in self.fetch_tracks(client, source):
                if track["id"] not in seen_ids:
                    seen_ids.add(track["id"])
                    all_songs.append(track)

        with open("list_data.json", "w") as f:
            json.dump(all_songs, f, indent=2)

        print(f"\nTotal unique tracks: {len(all_songs)}")
        return all_songs
