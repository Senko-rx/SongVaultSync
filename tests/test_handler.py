import io
from unittest.mock import MagicMock

from handler import Handler


def _request(path, expected_state="good"):
    handler = Handler.__new__(Handler)
    handler.path = path
    handler.server = MagicMock(expected_state=expected_state, auth_code=None, auth_error=None)
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.do_GET()
    return handler


def test_valid_code_is_accepted():
    handler = _request("/callback?code=abc&state=good")
    assert handler.server.auth_code == "abc"
    handler.send_response.assert_called_with(200)


def test_state_mismatch_is_rejected():
    handler = _request("/callback?code=abc&state=bad")
    assert handler.server.auth_code is None
    handler.send_response.assert_called_with(400)


def test_denied_consent_records_error_and_responds():
    handler = _request("/callback?error=access_denied&state=good")
    assert handler.server.auth_error == "access_denied"
    handler.send_response.assert_called_with(400)


def test_unrelated_request_gets_a_response():
    handler = _request("/favicon.ico")
    handler.send_response.assert_called_with(404)
