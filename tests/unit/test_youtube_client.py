"""Unit tests for YouTubeClient module."""

import pytest
from unittest.mock import MagicMock, patch
import yt_dlp

from api.youtube_client import (
    YouTubeClient,
    VideoInfo,
    SubtitleInfo,
    SubtitleTrack,
    YouTubeClientError,
    VideoNotFoundError,
    DownloadError,
    InfoExtractionError,
)


class TestVideoInfo:
    """Tests for VideoInfo dataclass."""

    def test_duration_formatted_hours(self):
        info = VideoInfo(id="test", title="Test", duration=3661)
        assert info.duration_formatted == "1:01:01"

    def test_duration_formatted_minutes(self):
        info = VideoInfo(id="test", title="Test", duration=125)
        assert info.duration_formatted == "0:02:05"

    def test_duration_formatted_none(self):
        info = VideoInfo(id="test", title="Test")
        assert info.duration_formatted == "Unknown"


class TestSubtitleTrack:
    """Tests for SubtitleTrack dataclass."""

    def test_str_manual(self):
        track = SubtitleTrack(lang="zh-Hant", name="Traditional Chinese")
        assert str(track) == "zh-Hant - Traditional Chinese"

    def test_str_auto(self):
        track = SubtitleTrack(lang="en", name="English", is_auto=True)
        assert str(track) == "en - English (auto)"


class TestSubtitleInfo:
    """Tests for SubtitleInfo dataclass."""

    def test_has_subtitles_true(self):
        info = SubtitleInfo(
            manual=[SubtitleTrack(lang="en", name="English")]
        )
        assert info.has_subtitles is True

    def test_has_subtitles_false(self):
        info = SubtitleInfo()
        assert info.has_subtitles is False

    def test_available_langs(self):
        info = SubtitleInfo(
            manual=[
                SubtitleTrack(lang="en", name="English"),
                SubtitleTrack(lang="zh-Hant", name="Traditional Chinese"),
            ],
            auto=[SubtitleTrack(lang="ja", name="Japanese", is_auto=True)]
        )
        assert info.available_langs == ["en", "zh-Hant", "ja"]

    def test_get_best_track_manual_priority(self):
        info = SubtitleInfo(
            manual=[SubtitleTrack(lang="zh-Hant", name="Traditional Chinese")],
            auto=[SubtitleTrack(lang="en", name="English", is_auto=True)]
        )
        track = info.get_best_track(["en", "zh-Hant"])
        assert track.lang == "zh-Hant"
        assert track.is_auto is False

    def test_get_best_track_fallback_auto(self):
        info = SubtitleInfo(
            auto=[SubtitleTrack(lang="en", name="English", is_auto=True)]
        )
        track = info.get_best_track(["en", "zh-Hant"])
        assert track.lang == "en"
        assert track.is_auto is True

    def test_get_best_track_none(self):
        info = SubtitleInfo()
        track = info.get_best_track(["en"])
        assert track is None


class TestYouTubeClient:
    """Tests for YouTubeClient class."""

    @pytest.fixture
    def client(self):
        return YouTubeClient()

    def test_init_defaults(self, client):
        assert client.proxy is None
        assert client.cookies_file is None

    def test_init_custom(self):
        client = YouTubeClient(
            timeout=100,
            proxy="http://proxy:8080",
            cookies_file="/path/to/cookies.txt"
        )
        assert client.timeout == 100
        assert client.proxy == "http://proxy:8080"
        assert client.cookies_file == "/path/to/cookies.txt"

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_get_video_info_success(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.return_value = {
            "id": "abc123",
            "title": "Test Video",
            "duration": 120,
            "thumbnail": "https://example.com/thumb.jpg",
            "uploader": "TestChannel",
            "description": "Test description"
        }
        mock_ydl_class.return_value = mock_ydl

        info = client.get_video_info("https://youtube.com/watch?v=abc123")

        assert info.id == "abc123"
        assert info.title == "Test Video"
        assert info.duration == 120
        assert info.thumbnail == "https://example.com/thumb.jpg"

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_get_video_info_not_found(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.side_effect = \
            yt_dlp.utils.DownloadError("Video not found")
        mock_ydl_class.return_value = mock_ydl

        with pytest.raises(VideoNotFoundError):
            client.get_video_info("https://youtube.com/watch?v=invalid")

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_get_video_info_none_result(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.return_value = None
        mock_ydl_class.return_value = mock_ydl

        with pytest.raises(VideoNotFoundError):
            client.get_video_info("https://youtube.com/watch?v=test")

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_list_subtitles_success(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.return_value = {
            "id": "test",
            "subtitles": {
                "en": [{"name": "English"}],
                "zh-Hant": [{"name": "Traditional Chinese"}]
            },
            "automatic_captions": {
                "ja": [{"name": "Japanese", "ext": "vtt"}]
            }
        }
        mock_ydl_class.return_value = mock_ydl

        info = client.list_subtitles("https://youtube.com/watch?v=test")

        assert len(info.manual) == 2
        assert len(info.auto) == 1
        assert "en" in info.available_langs
        assert "zh-Hant" in info.available_langs
        assert "ja" in info.available_langs

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_list_subtitles_error(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.side_effect = Exception("Error")
        mock_ydl_class.return_value = mock_ydl

        info = client.list_subtitles("https://youtube.com/watch?v=test")

        assert info.has_subtitles is False
        assert len(info.manual) == 0
        assert len(info.auto) == 0

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_download_subtitles_success(self, mock_ydl_class, client, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.return_value = {
            "id": "test123"
        }
        mock_ydl_class.return_value = mock_ydl

        expected_file = tmp_path / "test123.zh-Hant.vtt"
        expected_file.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nTest subtitle\n")

        result = client.download_subtitles(
            "https://youtube.com/watch?v=test",
            "zh-Hant",
            str(tmp_path)
        )

        assert result is not None
        assert "test123" in result

    @patch("api.youtube_client.yt_dlp.YoutubeDL")
    def test_download_subtitles_error(self, mock_ydl_class, client):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.side_effect = Exception("Error")
        mock_ydl_class.return_value = mock_ydl

        result = client.download_subtitles(
            "https://youtube.com/watch?v=test",
            "en",
            "/tmp"
        )

        assert result is None