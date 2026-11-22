from unittest.mock import MagicMock, patch

import pytest

from errors import ConversionError


def test_convert_calls_ffmpeg_with_list_args(tmp_path):
    src = tmp_path / "track.webm"
    src.touch()
    dst = tmp_path / "track.mp3"

    with patch("converter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        import converter
        converter.convert_to_mp3(src, dst)

    args = mock_run.call_args[0][0]
    assert isinstance(args, list), "ffmpeg must be called with a list, not a shell string"
    assert args[0] == "ffmpeg"
    assert str(src) in args
    assert str(dst) in args


def test_convert_handles_filename_with_spaces(tmp_path):
    src = tmp_path / "my track with spaces.webm"
    src.touch()
    dst = tmp_path / "my track with spaces.mp3"

    with patch("converter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        import converter
        converter.convert_to_mp3(src, dst)

    args = mock_run.call_args[0][0]
    assert str(src) in args


def test_convert_raises_on_nonzero_exit(tmp_path):
    src = tmp_path / "bad.webm"
    src.touch()
    dst = tmp_path / "bad.mp3"

    with patch("converter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        import converter
        with pytest.raises(ConversionError):
            converter.convert_to_mp3(src, dst)


def test_import_does_not_exit_when_ffmpeg_missing():
    import importlib

    import converter
    with patch("shutil.which", return_value=None):
        importlib.reload(converter)  # must not raise SystemExit


def test_ensure_ffmpeg_exits_when_missing():
    import converter
    with patch("converter.shutil.which", return_value=None):
        with pytest.raises(SystemExit):
            converter.ensure_ffmpeg()


def test_ensure_ffmpeg_passes_when_present():
    import converter
    with patch("converter.shutil.which", return_value="/usr/bin/ffmpeg"):
        converter.ensure_ffmpeg()
