"""E2E tests for audio transcription API."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestAudioTranscribeE2E:
    """End-to-end tests for audio transcription API."""

    @pytest.mark.asyncio
    async def test_transcribe_short_audio_returns_markdown(self, api_client):
        """Test that short audio returns markdown output."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny"},
            )

        assert response.status_code == 200
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_transcribe_with_quality_mode_speed(self, api_client):
        """Test transcription with speed quality mode."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "quality_mode": "speed"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_transcribe_with_json_format(self, api_client):
        """Test transcription with JSON return format."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "return_format": "json"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]

    @pytest.mark.asyncio
    async def test_backward_compat_without_new_params(self, api_client):
        """Test backward compatibility without new parameters."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "zh", "model_size": "base"},
            )

        assert response.status_code == 200