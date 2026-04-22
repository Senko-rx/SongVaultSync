from http.server import BaseHTTPRequestHandler
import urllib.parse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        received_state = params.get("state", [None])[0]
        expected_state = getattr(self.server, "expected_state", None)

        if expected_state and received_state != expected_state:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"State mismatch. Possible CSRF. Please try again.")
            return

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorised. You can close this window.")
            print("Code received!")

    def log_message(self, format, *args):
        pass
