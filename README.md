# SpotiGrab - The perfect tool for migrating your Spotify lists to your your local music collection

SpotiGrab is an application designed to help users transfer their Spotify playlists and liked songs to their local music collection. With a user-friendly CLI and automatic integration with the Spotify Web API, SpotiGrab makes it easy for users to create their music libraries and enjoy their favorite tracks offline.

## What to expect
- **Playlist and Liked Songs Export**: SpotiGrab allows users to export their Spotify playlists and liked songs to a specified local directory.
- **Automatic Metadata Retrieval**: The application retrieves metadata for each track, including artist name, album name, and track title, to organize the downloaded music files properly. (TODO)
- **Batch Processing**: SpotiGrab processes tracks in batches to optimise performance and handle large playlists efficiently.
- **Error Handling**: The application includes error handling to manage issues such as network errors, API rate limits, and missing tracks gracefully.


## Getting Started

### Prerequisites

- Python 3 (3.14 was used during development)
- A Spotify Developer account
- Spotify application credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Senko-rx/SpotiGrab.git
cd SpotiGrab
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
   - Add redirect URIs: `http://127.0.0.1:8888/callback`

5. Run the program:
```bash
python3 spotigrab.py
```
## What it does

1. **Connect Accounts**: Authenticates your Spotify account using the provided credentials and retrieves an access token for API requests
2. **Select Data**: Chooses which playlist(s) to export
3. **Transfer**: Fetches the tracks' information from the selected playlist(s)
4. **Download**: Downloads the tracks to the specified local directory based on the fetched information, while retrieving metadata for proper organisation
5. **Transform**: Change the format of the downloaded files if necessary
6. **Complete**: You now have a local copy of your Spotify playlists and liked songs, organised with metadata for easy access and enjoyment offline

## Contributing
While this program was built for personal use, contributions are always welcome:

## Limitations
The app still needs to implement a proper rate limiter to respect Spotify's API limits:
- Automatic retry with exponential backoff
- Progress tracking for long-running transfers

## Future work
Coaming soon!

> ## Disclaimer
> I heavily encourage paying artists for their work. Please ensure that you have the necessary rights to download and use the music in accordance with Spotify's terms of service and copyright laws.
