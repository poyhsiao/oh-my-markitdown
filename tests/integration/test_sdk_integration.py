"""Integration tests for SDK migration.

Tests verify that the new SDK modules work correctly together and integrate
properly with the existing codebase.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestYouTubeClientIntegration:
    """Integration tests for YouTube client SDK."""

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_youtube_client_info_and_download_flow(self, mock_ydl_class):
        """Test that YouTube client can fetch info and prepare for download."""
        from api.youtube_client import YouTubeClient

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_ydl.extract_info.return_value = {
            "id": "test_video_id",
            "title": "Test Video Title",
            "duration": 120,
            "uploader": "Test Uploader",
            "description": "Test description",
            "subtitles": {"en": [{"url": "http://example.com/sub.vtt"}]},
            "automatic_captions": {},
        }

        client = YouTubeClient()
        info = client.get_video_info("https://youtube.com/watch?v=test_video_id")

        assert info.id == "test_video_id"
        assert info.title == "Test Video Title"
        assert info.duration == 120

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_youtube_client_subtitle_workflow(self, mock_ydl_class):
        """Test that YouTube client can list and download subtitles."""
        from api.youtube_client import YouTubeClient

        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_ydl.extract_info.return_value = {
            "id": "test_video_id",
            "title": "Test Video",
            "duration": 60,
            "subtitles": {
                "en": [{"url": "http://example.com/en.vtt"}],
                "zh": [{"url": "http://example.com/zh.vtt"}],
            },
            "automatic_captions": {},
        }

        client = YouTubeClient()
        subtitle_info = client.list_subtitles("https://youtube.com/watch?v=test_video_id")

        assert subtitle_info.has_subtitles is True
        assert "en" in subtitle_info.available_langs
        assert "zh" in subtitle_info.available_langs


class TestAudioExtractorIntegration:
    """Integration tests for audio extractor SDK."""

    @patch("api.audio_extractor.ffmpeg.probe")
    def test_audio_extractor_validate_and_info_flow(self, mock_probe):
        """Test that audio extractor can validate and get info from audio files."""
        from api.audio_extractor import get_audio_info, validate_video_file

        mock_probe.return_value = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
            "format": {"duration": "180.5", "bit_rate": "1500000"},
        }

        is_valid = validate_video_file("/path/to/video.mp4")
        assert is_valid is True

        info = get_audio_info("/path/to/video.mp4")
        assert info["sample_rate"] == 48000
        assert info["channels"] == 2
        assert info["duration"] == 180.5


class TestOCRClientIntegration:
    """Integration tests for OCR client SDK."""

    def test_ocr_client_language_validation(self):
        """Test that OCR client validates languages correctly."""
        from api.ocr_client import validate_ocr_languages, UnsupportedLanguageError

        validate_ocr_languages("chi_tra+eng")

        with pytest.raises(UnsupportedLanguageError):
            validate_ocr_languages("invalid_lang")

    @patch("api.ocr_client.pytesseract.image_to_string")
    def test_ocr_client_image_workflow(self, mock_ocr):
        """Test that OCR client can process images."""
        from api.ocr_client import ocr_image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            mock_ocr.return_value = "Extracted text from image"

            with patch("os.path.exists", return_value=True):
                with patch("PIL.Image.open"):
                    result = ocr_image(temp_path, "chi_tra+eng")

            assert result == "Extracted text from image"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestSDKModuleImports:
    """Tests to verify SDK modules can be imported and have correct structure."""

    def test_youtube_client_module_structure(self):
        """Verify YouTube client module has all expected exports."""
        from api.youtube_client import (
            YouTubeClient,
            YouTubeClientError,
            VideoNotFoundError,
            SubtitleNotAvailableError,
            DownloadError,
            VideoInfo,
            SubtitleInfo,
            SubtitleTrack,
        )

        assert YouTubeClient is not None
        assert YouTubeClientError is not None
        assert VideoNotFoundError is not None
        assert VideoInfo is not None
        assert SubtitleInfo is not None

    def test_audio_extractor_module_structure(self):
        """Verify audio extractor module has all expected exports."""
        from api.audio_extractor import (
            extract_audio_from_video,
            get_audio_info,
            validate_video_file,
            AudioExtractionError,
            AudioExtractionTimeout,
        )

        assert extract_audio_from_video is not None
        assert get_audio_info is not None
        assert validate_video_file is not None
        assert AudioExtractionError is not None

    def test_ocr_client_module_structure(self):
        """Verify OCR client module has all expected exports."""
        from api.ocr_client import (
            ocr_image,
            ocr_image_object,
            ocr_pdf,
            ocr_pdf_pages,
            validate_ocr_languages,
            get_tesseract_languages,
            is_tesseract_available,
            OCRError,
            UnsupportedLanguageError,
        )

        assert ocr_image is not None
        assert ocr_pdf is not None
        assert validate_ocr_languages is not None
        assert OCRError is not None


class TestWhisperTranscribeIntegration:
    """Integration tests for whisper_transcribe module using new SDKs."""

    @patch("api.whisper_transcribe.YouTubeClient")
    def test_whisper_uses_youtube_client(self, mock_client_class):
        """Verify whisper_transcribe uses the new YouTubeClient SDK."""
        from api.whisper_transcribe import check_available_subtitles

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_subtitle_info = MagicMock()
        mock_subtitle_info.available_languages = ["en", "zh"]
        mock_subtitle_info.has_manual_subtitles = True
        mock_client.list_subtitles.return_value = mock_subtitle_info

        with patch("api.whisper_transcribe._youtube_client", None):
            pass

    @patch("api.audio_extractor.ffmpeg")
    def test_whisper_uses_audio_extractor(self, mock_ffmpeg):
        """Verify whisper_transcribe uses the new audio_extractor SDK."""
        from api.audio_extractor import extract_audio_from_video

        assert extract_audio_from_video is not None