# We run local server so that we can automate the fetching of the code from the callback response
from http.server import BaseHTTPRequestHandler
import urllib.parse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"You can close this window.")
            print("Code received!")