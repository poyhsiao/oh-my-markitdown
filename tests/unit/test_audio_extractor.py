"""Unit tests for audio_extractor module."""

import pytest
from unittest.mock import MagicMock, patch
import ffmpeg

from api.audio_extractor import (
    extract_audio_from_video,
    get_audio_info,
    validate_video_file,
    AudioExtractionError,
)


class TestExtractAudioFromVideo:
    """Tests for extract_audio_from_video function."""

    @patch("api.audio_extractor.ffmpeg")
    @patch("os.path.exists")
    def test_extract_success(self, mock_exists, mock_ffmpeg, tmp_path):
        mock_exists.return_value = True

        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.return_value = None

        video_path = str(tmp_path / "test.mp4")
        output_path = str(tmp_path / "test.wav")

        with patch("os.path.exists") as mock_out_exists:
            mock_out_exists.side_effect = lambda p: p == video_path or p == output_path
            result = extract_audio_from_video(video_path, output_path)

        assert result == output_path

    def test_extract_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_audio_from_video("/nonexistent/video.mp4")

    @patch("api.audio_extractor.ffmpeg")
    @patch("os.path.exists")
    def test_extract_ffmpeg_error(self, mock_exists, mock_ffmpeg, tmp_path):
        mock_exists.return_value = True

        mock_output = MagicMock()
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.side_effect = ffmpeg.Error(
            stderr=b"FFmpeg error: Invalid codec",
            stdout=b""
        )
        mock_ffmpeg.input.return_value.output.return_value = mock_output

        with pytest.raises(AudioExtractionError) as exc_info:
            extract_audio_from_video(str(tmp_path / "test.mp4"))

        assert "FFmpeg error" in str(exc_info.value)

    @patch("api.audio_extractor.ffmpeg")
    @patch("os.path.exists")
    def test_extract_with_custom_params(self, mock_exists, mock_ffmpeg, tmp_path):
        mock_exists.return_value = True

        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_output
        mock_output.run.return_value = None

        video_path = str(tmp_path / "test.mp4")
        output_path = str(tmp_path / "test.wav")

        with patch("os.path.exists") as mock_out_exists:
            mock_out_exists.side_effect = lambda p: p == video_path or p == output_path
            result = extract_audio_from_video(
                video_path,
                output_path,
                sample_rate=22050,
                channels=2,
                codec="pcm_s16le",
                threads=8,
            )

        mock_ffmpeg.input.assert_called_once()
        mock_input.output.assert_called_once()


class TestGetAudioInfo:
    """Tests for get_audio_info function."""

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_get_info_success(self, mock_probe):
        mock_probe.return_value = {
            "streams": [{
                "codec_type": "audio",
                "sample_rate": "16000",
                "channels": 1,
                "codec_name": "pcm_s16le"
            }],
            "format": {
                "duration": "120.5",
                "bit_rate": "256000"
            }
        }

        info = get_audio_info("/path/to/audio.wav")

        assert info["sample_rate"] == 16000
        assert info["channels"] == 1
        assert info["duration"] == 120.5
        assert info["codec"] == "pcm_s16le"
        assert info["bit_rate"] == 256000

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_get_info_no_audio_stream(self, mock_probe):
        mock_probe.return_value = {
            "streams": [{"codec_type": "video"}],
            "format": {}
        }

        with pytest.raises(AudioExtractionError, match="No audio stream found"):
            get_audio_info("/path/to/video.mp4")

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_get_info_ffmpeg_error(self, mock_probe):
        mock_probe.side_effect = ffmpeg.Error(stderr=b"Probe error", stdout=b"")

        with pytest.raises(AudioExtractionError):
            get_audio_info("/path/to/audio.wav")


class TestValidateVideoFile:
    """Tests for validate_video_file function."""

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_validate_has_audio(self, mock_probe):
        mock_probe.return_value = {
            "streams": [
                {"codec_type": "video"},
                {"codec_type": "audio"}
            ]
        }

        assert validate_video_file("/path/to/video.mp4") is True

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_validate_no_audio(self, mock_probe):
        mock_probe.return_value = {
            "streams": [{"codec_type": "video"}]
        }

        assert validate_video_file("/path/to/video.mp4") is False

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_validate_error(self, mock_probe):
        mock_probe.side_effect = Exception("Probe error")

        assert validate_video_file("/path/to/video.mp4") is False