import time
import requests
from settings import MAX_RETRIES, BACKOFF_BASE
from errors import SpotifyApiError


class SpotifyClient:
    def __init__(self, access_token: str):
        self._headers = {"Authorization": f"Bearer {access_token}"}

    def get(self, url: str, params: dict | None = None) -> dict:
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=self._headers, params=params, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                time.sleep(BACKOFF_BASE ** attempt)
                continue

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", BACKOFF_BASE ** attempt))
                time.sleep(retry_after)
                continue

            if response.status_code >= 500:
                last_error = SpotifyApiError(f"Server error {response.status_code}")
                time.sleep(BACKOFF_BASE ** attempt)
                continue

            if not response.ok:
                raise SpotifyApiError(f"Spotify API error {response.status_code}: {response.text}")

            return response.json()

        raise SpotifyApiError(f"Request failed after {MAX_RETRIES} attempts: {last_error}")
