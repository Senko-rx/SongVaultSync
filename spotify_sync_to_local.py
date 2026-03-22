from http.server import HTTPServer
import requests
import base64
import urllib.parse
import json
import os
from dotenv import load_dotenv
import webbrowser
from handler import Handler

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
SCOPE = "user-library-read"

class SpotifySyncToLocal:

    def _get_access_token(self):
        server = HTTPServer(("127.0.0.1", 8888), Handler)
        server.auth_code = None
        auth_url = "https://accounts.spotify.com/authorize"
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE
        }

        url = auth_url + "?" + urllib.parse.urlencode(params)

        webbrowser.open(url)

        # Wait for redirect
        while server.auth_code is None:
            server.handle_request()

        token_url = "https://accounts.spotify.com/api/token"

        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": server.auth_code,
            "redirect_uri": REDIRECT_URI
        }

        response = requests.post(token_url, headers=headers, data=data)
        token_info = response.json()

        access_token = token_info["access_token"]

        print("Access token received! Requesting songs from Spotify")

        return access_token

    def _fetch_song_list(self, access_token):
        # Fetch liked songs (paginated)
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        url = "https://api.spotify.com/v1/me/tracks?limit=50"

        songs = []

        while url:
            res = requests.get(url, headers=headers).json()

            for item in res["items"]:
                track = item["track"]
                songs.append({
                    "name": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                })

            url = res["next"]

        for s in songs:
            artist_string = ", ".join(s["artists"])
            print(f"{artist_string} - {s['name']}")

        with open('list_data.json', 'w') as f:
            json.dump(songs, f)

        print("\nTotal:", len(songs))

    def sync(self):
        access_token = self._get_access_token()
        self._fetch_song_list(access_token)