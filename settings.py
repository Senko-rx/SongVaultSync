WEBM_DIR = "webm/"
MP3_DIR = "mp3/"

AUDIO_BITRATE = "128k"
SAMPLE_RATE = 44100

SPOTIFY_SCOPES = " ".join([
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
])

MAX_RETRIES = 5
BACKOFF_BASE = 2
