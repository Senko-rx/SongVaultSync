from pathlib import Path
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
        converter.convert_audio(src, dst)

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
        converter.convert_audio(src, dst)

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
            converter.convert_audio(src, dst)


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


def _run_convert(tmp_path, dst_name, returncodes, bitrate="192k"):
    import converter

    src = tmp_path / "in.webm"
    src.touch()
    results = [MagicMock(returncode=code) for code in returncodes]
    with patch("converter.subprocess.run", side_effect=results) as mock_run:
        converter.convert_audio(src, tmp_path / dst_name, bitrate=bitrate)
    return [call.args[0] for call in mock_run.call_args_list]


def test_mp3_uses_requested_bitrate(tmp_path):
    [args] = _run_convert(tmp_path, "out.mp3", [0])
    assert args[args.index("-b:a") + 1] == "192k"


def test_opus_remuxes_without_reencoding_when_possible(tmp_path):
    [args] = _run_convert(tmp_path, "out.opus", [0])
    assert args[args.index("-c:a") + 1] == "copy"


def test_opus_falls_back_to_encoding_when_remux_fails(tmp_path):
    first, second = _run_convert(tmp_path, "out.opus", [1, 0])
    assert first[first.index("-c:a") + 1] == "copy"
    assert second[second.index("-c:a") + 1] == "libopus"
    assert second[second.index("-b:a") + 1] == "192k"


def test_unsupported_extension_raises(tmp_path):
    import converter

    with pytest.raises(ConversionError, match="Unsupported"):
        converter.convert_audio(tmp_path / "in.webm", tmp_path / "out.wav")


def test_ffmpeg_does_not_read_stdin_and_has_timeout(tmp_path):
    import subprocess

    import converter

    src = tmp_path / "in.webm"
    src.touch()
    with patch("converter.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        converter.convert_audio(src, tmp_path / "out.mp3")
    args, kwargs = mock_run.call_args
    assert "-nostdin" in args[0]
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["timeout"] > 0


def test_ffmpeg_timeout_becomes_conversion_error(tmp_path):
    import subprocess

    import converter

    with patch("converter.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 1)):
        with pytest.raises(ConversionError, match="timed out"):
            converter.convert_audio(tmp_path / "in.webm", tmp_path / "out.mp3")


def test_ffmpeg_gets_absolute_paths(tmp_path, monkeypatch):
    import converter

    monkeypatch.chdir(tmp_path)
    with patch("converter.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        converter.convert_audio(Path("-weird/in.webm"), Path("-weird/out.mp3"))
    args = mock_run.call_args[0][0]
    assert not any(arg.startswith("-weird") for arg in args)
