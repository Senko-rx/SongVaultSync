# Maybe: Create url list of websites to fetch the song from
# Try to fetch the song from x and create a way to validate if the song is correct
# Download the song on the local machine

import yt_dlp
import json
import os
import subprocess
import sys
from tqdm import tqdm

def download_song(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'webm/%(title)s.%(ext)s',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch1:{query}"])


with open('list_data.json', 'r', encoding='utf-8') as f:
    songs = json.load(f)

counter = 0

for song in songs:
    print(song)
    artist_string = " ".join(song["artists"])
    query = f"{artist_string} {song['name']}"
    download_song(query)
    counter += 1
    if counter >= 5:
        break


# After full fetch of files from Youtube, we convert them to mp3
# Thanks to https://github.com/ooutama/WebmToMp3/blob/main/WebmToMp3.py for most of the following code
# TODO: Check if album cover/thumbnail is also taken into mp3 file, otherwise add them separately

WEBM_DIR="webm/"
MP3_DIR="mp3/"


if not os.path.isdir(WEBM_DIR):
    print(f'The webm path "{WEBM_DIR}" does not exist.')
    sys.exit()
elif not os.path.isdir(MP3_DIR):
    os.makedirs(MP3_DIR)

for file in tqdm(os.listdir(WEBM_DIR)):
    webmFile = os.path.join(WEBM_DIR, file)
    mp3File = os.path.join(MP3_DIR, file).replace(
        "webm", "mp3")

    command = f"ffmpeg -i \"{webmFile}\" -vn -ab 128k -ar 44100 -y \"{mp3File}\""
    result = subprocess.call(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )

    if result == 0:
        print(f"Converted: {file} to mp3")
    else:
        print(f"Failed to convert: {file}")
