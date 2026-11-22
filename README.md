# SongVaultSync - The perfect tool for migrating your Spotify lists to your local music collection

SongVaultSync is an application designed to help users transfer their Spotify playlists and liked songs to their local music collection. With a user-friendly CLI and automatic integration with the Spotify Web API, SongVaultSync makes it easy for users to create their music libraries and enjoy their favorite tracks offline.

> ## Disclaimer
> This software is provided “as is”, without warranties of any kind, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, non‑infringement, or any warranty that the software will operate without error. 
> To the maximum extent permitted by applicable law, the authors and contributors shall not be liable for any damages whatsoever arising out of the use of or inability to use the software, including but not limited to direct, indirect, incidental, special, consequential, or punitive damages.
> This tool may interact with third‑party services (e.g., Spotify’s API) and may be used with external content from sources such as media platforms. You are solely responsible for ensuring that your use of the software complies with all applicable laws, terms of service of third‑party providers, and copyrights. 
> You should not use this software to violate the rights of others, including downloading material you are not authorised to access. By using this software, you agree that you assume all risks associated with its use.
> The authors and distributors of this software do not endorse or encourage the violation of copyright laws or the terms of service of any service provider, and you should seek appropriate permissions from content owners before obtaining or using any copyrighted material.

# Notes from the developer
I heavily encourage paying artists for their work. Please ensure that you have the necessary rights to download and use the music in accordance with Spotify's, YouTube’s and any other parties you may want to use to download your music's terms of service and copyright laws.
This program is meant to be used as a baseline and example for learning and implementing your own audio API interactions, so that you can sync your spotify collection with your local music collection, not as a tool for piracy!


## What to expect
- **Playlist and Liked Songs Export**: SongVaultSync allows users to export their Spotify playlists and liked songs to a specified local directory.
- **Automatic Metadata**: Each file is tagged with title, artists, album, album artist, track number, release date, ISRC and cover art (ID3 for mp3, Vorbis comments for opus), and named `Artist - Title`.
- **Playlist Files**: Every synced source (Liked Songs and each playlist) is written as an `.m3u8` playlist that any music player can open.
- **Wrong-Song Protection**: Search results are only accepted if their length is within 15 seconds of the Spotify track, which filters out live versions, extended mixes and loops.
- **Resumable and Parallel**: Tracks that already exist are skipped, failures are saved for `--retry-failed`, and `--workers` downloads several tracks at once.
- **Error Handling**: The application includes error handling to manage issues such as network errors, API rate limits, and missing tracks gracefully.


## Getting Started

### Prerequisites

- Python 3.11 or newer (3.14 was used during development)
- A Spotify Developer account
- Spotify application credentials
- FFMPEG

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Senko-rx/SongVaultSync.git
cd SongVaultSync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with your Spotify app credentials, following .env.example:
```env
CLIENT_ID={your_client_id_here}
CLIENT_SECRET={your_client_secret_here}
REDIRECT_URI=http://127.0.0.1:8888/callback
```

4. Configure your Spotify app:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Add redirect URIs: `http://127.0.0.1:8888/callback` (it must match `REDIRECT_URI` exactly; the local callback server listens on that host and port)

5. Run the program:
```bash
python3 songvaultsync.py
```

6. Follow the steps the program presents

## Usage

```bash
python3 songvaultsync.py                          # pick sources from an interactive menu
python3 songvaultsync.py --all                    # liked songs + every playlist
python3 songvaultsync.py --source liked --source <PLAYLIST_ID>
python3 songvaultsync.py --all --output-dir ~/Music/Spotify --format opus --workers 4
python3 songvaultsync.py --retry-failed           # retry only what failed last time
```

| Option | Description |
|--------|-------------|
| `--all` | Download liked songs and all playlists |
| `--source liked\|PLAYLIST_ID` | Download a specific source; repeatable |
| `--from-catalog FILE` | Skip Spotify login and download from a `catalog.json` export (see below) |
| `--retry-failed` | Retry only the tracks recorded in `failed.json` by the previous run |
| `--output-dir DIR` | Where to put everything (default: current directory) |
| `--format mp3\|opus` | Output format (default: mp3). `opus` keeps YouTube's audio without re-encoding when possible |
| `--bitrate 192k` | Encoding bitrate, 32k-320k (default: 128k) |
| `--workers N` | Download N tracks in parallel, 1-8 (default: 1) |
| `--mp3-only` | Delete the downloaded source audio after converting, keeping only the converted file |
| `--no-metadata` | Don't embed tags or cover art |
| `--downloader NAME` | Downloader backend (default: `ytdlp`) |

`--all`, `--source`, `--from-catalog` and `--retry-failed` are mutually exclusive.

### Offline catalog

`python3 export_catalog.py` saves your liked songs and all playlists to `catalog.json`. Later, `python3 songvaultsync.py --from-catalog catalog.json` downloads from that file without logging in to Spotify.

### Output layout

```
<output-dir>/
├── mp3/              # or opus/ — "Artist - Title.mp3", fully tagged
├── playlists/        # "Liked Songs.m3u8", "<Playlist name>.m3u8"
├── webm/             # downloaded source audio (removed per track with --mp3-only)
├── failed.json       # only present if some tracks failed
└── list_data.json    # the track list used for the last run
```

Upgrading from an older version that named files `<spotify_id>.mp3`? Those files are renamed to `Artist - Title.mp3` automatically on the next run instead of being downloaded again.

## What it does

1. **Connect Accounts**: Authenticates your Spotify account using the provided credentials and retrieves an access token for API requests
2. **Select Data**: Chooses which playlist(s) to export
3. **Transfer**: Fetches the tracks' information from the selected playlist(s)
4. **Download**: Downloads the tracks to the specified local directory based on the fetched information, while retrieving metadata for proper organisation
5. **Transform**: Change the format of the downloaded files if necessary
6. **Complete**: You now have a local copy of your Spotify playlists and liked songs, organised with metadata for easy access and enjoyment offline

## Contributing
While this program was built for personal use, contributions are always welcome.

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests   # unit tests
ruff check .                # lint (the same checks CI runs)
```

## Limitations
The previous limitations noted here have been resolved with the latest commits. New ones that have been identified include:
- The program should have built-in support for multiple music sources, so that users can easily switch between them without needing to change the code. This would allow users to download their music from different platforms, including their own music server, without needing to modify the code.

## Future work
- The implementation of adding multiple playlists to the transfer queue -> Done
- The implementation of a progress bar for long-running transfers -> Done
- The ability to easily change the places you download/sync your music from -> Modularisation of code to implement yourself, but not yet implemented
- Eventually a guide on how to setup your own music server and use this tool to fetch your spotify collection and pull its songs from your music server, so that you can have your music collection available on all your devices without needing to download it on each of them. -> Slowely in the works

