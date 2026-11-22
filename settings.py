# Folder names inside the output directory. Converted files go in a folder named
# after their format (mp3/ or opus/).
SOURCE_AUDIO_DIR = "webm"
PLAYLISTS_DIR = "playlists"

AUDIO_BITRATE = "128k"
SAMPLE_RATE = 44100

SPOTIFY_SCOPES = " ".join([
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
])

MAX_RETRIES = 5
BACKOFF_BASE = 2

# A search result is accepted only if its length is within this many seconds
# of the Spotify track length. Guards against live versions, loops and covers.
DURATION_TOLERANCE_SECONDS = 15
SEARCH_CANDIDATES = 5
