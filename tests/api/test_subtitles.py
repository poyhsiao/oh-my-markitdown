"""Tests for YouTube subtitle extraction functions.

Updated to mock new SDK modules instead of subprocess calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os


class TestCheckAvailableSubtitles:
    """Test check_available_subtitles function."""

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_has_manual_subtitles(self, mock_get_client):
        """Test detection of manually uploaded subtitles."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo, SubtitleTrack

        # Mock YouTube client
        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo(
            manual=[
                SubtitleTrack(lang="zh-Hant", name="Traditional Chinese"),
                SubtitleTrack(lang="en", name="English"),
            ],
            auto=[],
        )
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        assert result["has_manual"] is True
        assert result["has_auto"] is False
        assert "zh-Hant" in result["available_langs"]
        assert "en" in result["available_langs"]

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_has_auto_subtitles(self, mock_get_client):
        """Test detection of auto-generated subtitles."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo, SubtitleTrack

        # Mock YouTube client
        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo(
            manual=[],
            auto=[
                SubtitleTrack(lang="zh-Hant", name="Traditional Chinese", is_auto=True),
                SubtitleTrack(lang="en", name="English", is_auto=True),
            ],
        )
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        assert result["has_manual"] is False
        assert result["has_auto"] is True
        assert len(result["available_langs"]) > 0

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_no_subtitles(self, mock_get_client):
        """Test video with no subtitles."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo

        # Mock YouTube client with no subtitles
        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo()
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        assert result["has_manual"] is False
        assert result["has_auto"] is False
        assert result["available_langs"] == []
        assert result["recommended_lang"] is None

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_language_priority(self, mock_get_client):
        """Test language priority selection."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo, SubtitleTrack

        # Mock with multiple languages
        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo(
            manual=[
                SubtitleTrack(lang="en", name="English"),
                SubtitleTrack(lang="zh-Hant", name="Traditional Chinese"),
                SubtitleTrack(lang="ja", name="Japanese"),
            ],
            auto=[],
        )
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        # zh-Hant should be recommended (highest priority that's available)
        assert result["recommended_lang"] == "zh-Hant"

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_fallback_to_first_available(self, mock_get_client):
        """Test fallback to first available when no priority match."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo, SubtitleTrack

        # Mock with languages not in priority list
        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo(
            manual=[
                SubtitleTrack(lang="es", name="Spanish"),
                SubtitleTrack(lang="fr", name="French"),
            ],
            auto=[],
        )
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        # Should fallback to first available
        assert result["recommended_lang"] == "es"

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_exception_handling(self, mock_get_client):
        """Test handling of exceptions."""
        from api.whisper_transcribe import check_available_subtitles

        # Mock client raising exception
        mock_get_client.side_effect = Exception("Network error")

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        # Should return empty result on exception
        assert result["has_manual"] is False
        assert result["has_auto"] is False
        assert result["available_langs"] == []

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_both_manual_and_auto_subtitles(self, mock_get_client):
        """Test when video has both manual and auto subtitles."""
        from api.whisper_transcribe import check_available_subtitles
        from api.youtube_client import SubtitleInfo, SubtitleTrack

        mock_client = Mock()
        mock_client.list_subtitles.return_value = SubtitleInfo(
            manual=[
                SubtitleTrack(lang="zh-Hant", name="Traditional Chinese"),
            ],
            auto=[
                SubtitleTrack(lang="en", name="English", is_auto=True),
            ],
        )
        mock_get_client.return_value = mock_client

        result = check_available_subtitles("https://youtube.com/watch?v=test")

        assert result["has_manual"] is True
        assert result["has_auto"] is True
        # Manual subtitles should be prioritized
        assert result["recommended_lang"] == "zh-Hant"


class TestParseVttToText:
    """Test _parse_vtt_to_text function."""

    def test_parse_basic_vtt(self):
        """Test parsing basic VTT file."""
        from api.whisper_transcribe import _parse_vtt_to_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as f:
            f.write("""WEBVTT

00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
This is a test
""")
            f.flush()

            result = _parse_vtt_to_text(f.name)

            assert "Hello world" in result
            assert "This is a test" in result
            assert "-->" not in result  # Timestamps removed
            assert "WEBVTT" not in result  # Header removed

            os.unlink(f.name)

    def test_parse_vtt_with_note_blocks(self):
        """Test parsing VTT with NOTE blocks."""
        from api.whisper_transcribe import _parse_vtt_to_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as f:
            f.write("""WEBVTT

NOTE This is a note

00:00:01.000 --> 00:00:04.000
Actual content here
""")
            f.flush()

            result = _parse_vtt_to_text(f.name)

            assert "Actual content here" in result
            assert "NOTE" not in result

            os.unlink(f.name)

    def test_parse_vtt_with_positioning(self):
        """Test parsing VTT with positioning tags."""
        from api.whisper_transcribe import _parse_vtt_to_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as f:
            f.write("""WEBVTT

00:00:01.000 --> 00:00:04.000 position:50% align:center
Text with positioning
""")
            f.flush()

            result = _parse_vtt_to_text(f.name)

            assert "Text with positioning" in result
            assert "position:" not in result
            assert "align:" not in result

            os.unlink(f.name)

    def test_parse_vtt_with_cue_identifiers(self):
        """Test parsing VTT with numeric cue identifiers."""
        from api.whisper_transcribe import _parse_vtt_to_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as f:
            f.write("""WEBVTT

1
00:00:01.000 --> 00:00:04.000
First cue

2
00:00:05.000 --> 00:00:08.000
Second cue
""")
            f.flush()

            result = _parse_vtt_to_text(f.name)

            assert "First cue" in result
            assert "Second cue" in result

            os.unlink(f.name)

    def test_parse_empty_vtt(self):
        """Test parsing empty VTT file."""
        from api.whisper_transcribe import _parse_vtt_to_text

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as f:
            f.write("WEBVTT\n")
            f.flush()

            result = _parse_vtt_to_text(f.name)

            assert result == ""

            os.unlink(f.name)


class TestTranscribeYouTubeVideo:
    """Test transcribe_youtube_video function with hybrid strategy."""

    @patch('api.whisper_transcribe.download_and_convert_subtitles')
    @patch('api.whisper_transcribe.check_available_subtitles')
    @patch('api.whisper_transcribe._get_video_title')
    def test_fast_path_with_subtitles(self, mock_title, mock_check, mock_download):
        """Test fast path when subtitles are available."""
        from api.whisper_transcribe import transcribe_youtube_video

        # Mock subtitle check
        mock_check.return_value = {
            "has_manual": True,
            "has_auto": False,
            "available_langs": ["zh-Hant"],
            "recommended_lang": "zh-Hant"
        }

        # Mock subtitle download
        mock_download.return_value = (
            "Test transcript content",
            {
                "source": "youtube_subtitles",
                "language": "zh-Hant",
                "is_auto_generated": False,
                "duration": 300
            }
        )

        # Mock title
        mock_title.return_value = "Test Video"

        result = transcribe_youtube_video(
            "https://youtube.com/watch?v=test",
            prefer_subtitles=True
        )

        assert result["success"] is True
        assert result["metadata"]["source"] == "youtube_subtitles"
        assert result["metadata"]["language"] == "zh-Hant"
        assert result["metadata"]["is_auto_generated"] is False
        assert "processing_time_ms" in result["metadata"]
        
        # Verify subtitle functions were called
        mock_check.assert_called_once()
        mock_download.assert_called_once()
        mock_title.assert_called_once()

    @patch('api.whisper_transcribe.transcribe_audio')
    @patch('api.whisper_transcribe.download_youtube_audio')
    @patch('api.whisper_transcribe.check_available_subtitles')
    def test_slow_path_without_subtitles(self, mock_check, mock_download_audio, mock_transcribe):
        """Test slow path (Whisper) when no subtitles available."""
        from api.whisper_transcribe import transcribe_youtube_video

        # Mock no subtitles
        mock_check.return_value = {
            "has_manual": False,
            "has_auto": False,
            "available_langs": [],
            "recommended_lang": None
        }

        # Mock audio download
        mock_download_audio.return_value = ("/tmp/test.mp3", "Test Video")

        # Mock transcription
        mock_transcribe.return_value = (
            "Whisper transcript",
            {
                "language": "zh",
                "duration": 300,
                "model": "base"
            }
        )

        with patch('api.whisper_transcribe.os.path.exists', return_value=True):
            with patch('api.whisper_transcribe.os.unlink'):
                result = transcribe_youtube_video(
                    "https://youtube.com/watch?v=test",
                    prefer_subtitles=True
                )

        assert result["success"] is True
        assert result["metadata"]["source"] == "whisper"
        assert result["metadata"]["model"] == "base"
        
        # Verify fallback to Whisper
        mock_check.assert_called_once()
        mock_download_audio.assert_called_once()
        mock_transcribe.assert_called_once()

    @patch('api.whisper_transcribe.transcribe_audio')
    @patch('api.whisper_transcribe.download_youtube_audio')
    def test_force_whisper_path(self, mock_download_audio, mock_transcribe):
        """Test forcing Whisper path with prefer_subtitles=False."""
        from api.whisper_transcribe import transcribe_youtube_video

        mock_download_audio.return_value = ("/tmp/test.mp3", "Test Video")
        mock_transcribe.return_value = (
            "Whisper transcript",
            {
                "language": "zh",
                "duration": 300,
                "model": "base"
            }
        )

        with patch('api.whisper_transcribe.os.path.exists', return_value=True):
            with patch('api.whisper_transcribe.os.unlink'):
                result = transcribe_youtube_video(
                    "https://youtube.com/watch?v=test",
                    prefer_subtitles=False  # Force Whisper
                )

        assert result["success"] is True
        assert result["metadata"]["source"] == "whisper"
        
        mock_download_audio.assert_called_once()
        mock_transcribe.assert_called_once()

    @patch('api.whisper_transcribe.transcribe_audio')
    @patch('api.whisper_transcribe.download_youtube_audio')
    def test_fast_mode_optimizations(self, mock_download_audio, mock_transcribe):
        """Test fast_mode enables optimizations."""
        from api.whisper_transcribe import transcribe_youtube_video

        mock_download_audio.return_value = ("/tmp/test.mp3", "Test Video")
        mock_transcribe.return_value = (
            "Whisper transcript",
            {"language": "zh", "model": "base"}
        )

        with patch('api.whisper_transcribe.os.path.exists', return_value=True):
            with patch('api.whisper_transcribe.os.unlink'):
                result = transcribe_youtube_video(
                    "https://youtube.com/watch?v=test",
                    prefer_subtitles=False,
                    fast_mode=True
                )

        # Verify fast mode audio quality was passed
        mock_download_audio.assert_called_once()
        call_args = mock_download_audio.call_args
        assert call_args.kwargs.get('audio_quality') == "64K"

        # Verify cpu_threads was passed for fast mode
        mock_transcribe.assert_called_once()
        transcribe_args = mock_transcribe.call_args
        assert transcribe_args.kwargs.get('cpu_threads') == 8

    @patch('api.whisper_transcribe.transcribe_audio')
    @patch('api.whisper_transcribe.download_youtube_audio')
    @patch('api.whisper_transcribe.check_available_subtitles')
    def test_subtitle_failure_fallback_to_whisper(self, mock_check, mock_download_audio, mock_transcribe):
        """Test fallback to Whisper when subtitle extraction fails."""
        from api.whisper_transcribe import transcribe_youtube_video

        # Mock subtitle check returns available, but download fails
        mock_check.return_value = {
            "has_manual": True,
            "has_auto": False,
            "available_langs": ["zh-Hant"],
            "recommended_lang": "zh-Hant"
        }

        # Mock audio download and transcription
        mock_download_audio.return_value = ("/tmp/test.mp3", "Test Video")
        mock_transcribe.return_value = (
            "Whisper transcript",
            {"language": "zh", "model": "base"}
        )

        # Make subtitle download fail by raising exception
        with patch('api.whisper_transcribe.download_and_convert_subtitles', side_effect=Exception("Download failed")):
            with patch('api.whisper_transcribe.os.path.exists', return_value=True):
                with patch('api.whisper_transcribe.os.unlink'):
                    result = transcribe_youtube_video(
                        "https://youtube.com/watch?v=test",
                        prefer_subtitles=True
                    )

        # Should fall back to Whisper
        assert result["success"] is True
        assert result["metadata"]["source"] == "whisper"

    @patch('api.whisper_transcribe.transcribe_audio')
    @patch('api.whisper_transcribe.download_youtube_audio')
    def test_cleanup_on_success(self, mock_download_audio, mock_transcribe):
        """Test temp file cleanup after successful transcription."""
        from api.whisper_transcribe import transcribe_youtube_video

        mock_download_audio.return_value = ("/tmp/test.mp3", "Test Video")
        mock_transcribe.return_value = (
            "Whisper transcript",
            {"language": "zh", "model": "base"}
        )

        with patch('api.whisper_transcribe.os.path.exists', return_value=True) as mock_exists:
            with patch('api.whisper_transcribe.os.unlink') as mock_unlink:
                result = transcribe_youtube_video(
                    "https://youtube.com/watch?v=test",
                    prefer_subtitles=False
                )

        # Verify cleanup was called
        mock_exists.assert_called()
        mock_unlink.assert_called_once_with("/tmp/test.mp3")


class TestDownloadYoutubeAudio:
    """Test download_youtube_audio function with SDK."""

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_default_audio_quality(self, mock_get_client):
        """Test download with default audio quality (128K)."""
        from api.whisper_transcribe import download_youtube_audio

        mock_client = Mock()
        mock_client.download_audio.return_value = ("/tmp/test123.mp3", "Test Video")
        mock_get_client.return_value = mock_client

        path, title = download_youtube_audio("https://youtube.com/watch?v=test")

        assert title == "Test Video"
        assert "test123.mp3" in path
        mock_client.download_audio.assert_called_once_with(
            "https://youtube.com/watch?v=test", "/tmp", "128K"
        )

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_low_quality_audio(self, mock_get_client):
        """Test download with low quality audio for fast mode."""
        from api.whisper_transcribe import download_youtube_audio

        mock_client = Mock()
        mock_client.download_audio.return_value = ("/tmp/test123.mp3", "Test Video")
        mock_get_client.return_value = mock_client

        path, title = download_youtube_audio(
            "https://youtube.com/watch?v=test", 
            audio_quality="64K"
        )

        mock_client.download_audio.assert_called_once_with(
            "https://youtube.com/watch?v=test", "/tmp", "64K"
        )

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_returns_title_and_path(self, mock_get_client):
        """Test function returns title and audio path."""
        from api.whisper_transcribe import download_youtube_audio

        mock_client = Mock()
        mock_client.download_audio.return_value = ("/tmp/abc123.mp3", "My Video Title")
        mock_get_client.return_value = mock_client

        path, title = download_youtube_audio("https://youtube.com/watch?v=test")

        assert title == "My Video Title"
        assert "abc123.mp3" in path


class TestFormatTranscriptAsMarkdown:
    """Test format_transcript_as_markdown function."""

    def test_subtitle_source_format(self):
        """Test markdown format with subtitle source."""
        from api.whisper_transcribe import format_transcript_as_markdown

        result = format_transcript_as_markdown(
            title="Test Video",
            transcript="Test transcript",
            metadata={
                "source": "youtube_subtitles",
                "language": "zh-Hant",
                "is_auto_generated": False,
                "processing_time_ms": 2500
            },
            include_metadata=True
        )

        assert "# Test Video" in result
        assert "YouTube Subtitles" in result
        assert "zh-Hant" in result
        assert "Manual" in result
        assert "2.5s" in result

    def test_whisper_source_format(self):
        """Test markdown format with Whisper source."""
        from api.whisper_transcribe import format_transcript_as_markdown

        result = format_transcript_as_markdown(
            title="Test Video",
            transcript="Test transcript",
            metadata={
                "source": "whisper",
                "language": "zh",
                "model": "base",
                "duration": 300,
                "processing_time_ms": 120000
            },
            include_metadata=True
        )

        assert "Whisper AI" in result
        assert "Model" in result
        assert "base" in result
        assert "120.0s" in result

    def test_auto_generated_subtitle_format(self):
        """Test markdown format with auto-generated subtitles."""
        from api.whisper_transcribe import format_transcript_as_markdown

        result = format_transcript_as_markdown(
            title="Test Video",
            transcript="Test transcript",
            metadata={
                "source": "youtube_subtitles",
                "language": "en",
                "is_auto_generated": True,
                "processing_time_ms": 1500
            },
            include_metadata=True
        )

        assert "Auto-generated" in result

    def test_without_metadata(self):
        """Test markdown without metadata."""
        from api.whisper_transcribe import format_transcript_as_markdown

        result = format_transcript_as_markdown(
            title="Test Video",
            transcript="Test transcript",
            metadata={"source": "whisper"},
            include_metadata=False
        )

        assert "# Test Video" in result
        assert "## Transcription Info" not in result
        assert "Test transcript" in result

    def test_processing_time_milliseconds(self):
        """Test processing time display for small values."""
        from api.whisper_transcribe import format_transcript_as_markdown

        result = format_transcript_as_markdown(
            title="Test Video",
            transcript="Test transcript",
            metadata={
                "source": "youtube_subtitles",
                "language": "en",
                "processing_time_ms": 500
            },
            include_metadata=True
        )

        assert "500ms" in result


class TestGetVideoTitle:
    """Test _get_video_title function with SDK."""

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_returns_title_on_success(self, mock_get_client):
        """Test successful title retrieval."""
        from api.whisper_transcribe import _get_video_title
        from api.youtube_client import VideoInfo

        mock_client = Mock()
        mock_client.get_video_info.return_value = VideoInfo(
            id="test123",
            title="My Awesome Video",
        )
        mock_get_client.return_value = mock_client

        title = _get_video_title("https://youtube.com/watch?v=test")

        assert title == "My Awesome Video"

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_returns_unknown_on_failure(self, mock_get_client):
        """Test returns 'Unknown' on YouTubeClientError."""
        from api.whisper_transcribe import _get_video_title
        from api.youtube_client import YouTubeClientError

        mock_client = Mock()
        mock_client.get_video_info.side_effect = YouTubeClientError("Video not found")
        mock_get_client.return_value = mock_client

        title = _get_video_title("https://youtube.com/watch?v=test")

        assert title == "Unknown"

    @patch('api.whisper_transcribe._get_youtube_client')
    def test_returns_unknown_on_exception(self, mock_get_client):
        """Test returns 'Unknown' on generic exception."""
        from api.whisper_transcribe import _get_video_title

        mock_get_client.side_effect = Exception("Network error")

        title = _get_video_title("https://youtube.com/watch?v=test")

        assert title == "Unknown"


class TestIncludeTimestamps:
    """Test include_timestamps parameter in format_multiline_output."""

    def test_format_multiline_output_without_timestamps(self):
        """Test format_multiline_output with include_timestamps=False."""
        from api.subtitles import format_multiline_output

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello world"},
            {"start": 2.0, "end": 4.0, "text": "This is a test"},
        ]

        result = format_multiline_output(
            segments,
            output_format="markdown",
            include_timestamps=False
        )

        assert "markdown" in result
        assert "Hello world" in result["markdown"]
        assert "This is a test" in result["markdown"]
        assert "[0:00]" not in result["markdown"]
        assert "[0:02]" not in result["markdown"]

    def test_format_multiline_output_with_timestamps(self):
        """Test format_multiline_output with include_timestamps=True."""
        from api.subtitles import format_multiline_output

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello world"},
            {"start": 2.0, "end": 4.0, "text": "This is a test"},
        ]

        result = format_multiline_output(
            segments,
            output_format="markdown",
            include_timestamps=True
        )

        assert "markdown" in result
        assert "Hello world" in result["markdown"]
        assert "This is a test" in result["markdown"]
        assert "[0:00]" in result["markdown"]
        assert "[0:02]" in result["markdown"]

    def test_format_multiline_output_default_no_timestamps(self):
        """Test format_multiline_output defaults to no timestamps."""
        from api.subtitles import format_multiline_output

        segments = [
            {"start": 0.0, "end": 2.0, "text": "Test text"},
        ]

        result = format_multiline_output(
            segments,
            output_format="markdown"
        )

        assert "markdown" in result
        assert "Test text" in result["markdown"]
        assert "[0:00]" not in result["markdown"]

    @patch('api.whisper_transcribe.transcribe_with_timestamps')
    def test_transcribe_with_formats_without_timestamps(self, mock_transcribe):
        """Test transcribe_with_formats passes include_timestamps=False correctly."""
        from api.whisper_transcribe import transcribe_with_formats

        mock_transcribe.return_value = (
            "Transcript text",
            [
                {"start": 0.0, "end": 2.0, "text": "Hello"},
                {"start": 2.0, "end": 4.0, "text": "World"},
            ]
        )

        result, metadata = transcribe_with_formats(
            audio_path="/tmp/test.mp3",
            output_formats="markdown",
            include_timestamps=False
        )

        assert "markdown" in result
        assert "[0:00]" not in result["markdown"]

    @patch('api.whisper_transcribe.transcribe_with_timestamps')
    def test_transcribe_with_formats_with_timestamps(self, mock_transcribe):
        """Test transcribe_with_formats passes include_timestamps=True correctly."""
        from api.whisper_transcribe import transcribe_with_formats

        mock_transcribe.return_value = (
            "Transcript text",
            [
                {"start": 0.0, "end": 2.0, "text": "Hello"},
                {"start": 2.0, "end": 4.0, "text": "World"},
            ]
        )

        result, metadata = transcribe_with_formats(
            audio_path="/tmp/test.mp3",
            output_formats="markdown",
            include_timestamps=True
        )

        assert "markdown" in result
        assert "[0:00]" in result["markdown"]