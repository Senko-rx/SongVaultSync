import secrets
import urllib.parse
from http.server import BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    """Receives Spotify's OAuth redirect on the local callback server."""

    def _respond(self, status: int, message: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(message)

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" not in params and "error" not in params:
            self._respond(404, b"Not found.")  # e.g. the browser asking for /favicon.ico
            return

        received_state = params.get("state", [""])[0]
        expected_state = getattr(self.server, "expected_state", None) or ""
        if not expected_state or not secrets.compare_digest(received_state, expected_state):
            self._respond(400, b"State mismatch. Possible CSRF. Please try again.")
            return

        if "error" in params:
            # e.g. the user clicked "Cancel" on Spotify's consent page.
            self.server.auth_error = params["error"][0]
            self._respond(400, b"Authorisation was not granted. You can close this window.")
            return

        self.server.auth_code = params["code"][0]
        self._respond(200, b"Authorised. You can close this window.")
        print("Code received!")

    def log_message(self, format, *args):
        pass
