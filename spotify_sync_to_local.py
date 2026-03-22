# Program that pulls songs from spotify API, sets them into a list, then uses that list (.json) to fetch the songs from a mp3 downloader and sets them into a folder, then zips the folder
import requests
import base64
import urllib.parse
import json
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
SCOPE = "user-library-read"

auth_url = "https://accounts.spotify.com/authorize"

params = {
    "client_id": CLIENT_ID,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE
}

url = auth_url + "?" + urllib.parse.urlencode(params)

print("\n👉 Open this URL in your browser:\n")
print(url)

redirect_response = input("\nPaste the FULL redirect URL here:\n")

code = urllib.parse.parse_qs(
    urllib.parse.urlparse(redirect_response).query
)["code"][0]

token_url = "https://accounts.spotify.com/api/token"

auth_header = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
).decode()

headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI
}

response = requests.post(token_url, headers=headers, data=data)
token_info = response.json()

access_token = token_info["access_token"]

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