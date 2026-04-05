"""Unit tests for TranscriptionService."""
import pytest
from unittest.mock import patch


class TestTranscriptionService:
    @patch("api.transcription_service.DeviceDetector")
    def test_service_initializes_detector(self, mock_detector):
        from api.transcription_service import TranscriptionService

        service = TranscriptionService()
        mock_detector.assert_called_once()
        assert service is not None