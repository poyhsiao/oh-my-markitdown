"""Integration tests for Whisper transcription pipeline with real tiny model."""
import pytest
from pathlib import Path

pytestmark = [pytest.mark.integration, pytest.mark.slow]

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestTranscribePipeline:
    """Integration tests with real tiny model."""

    def test_transcribe_short_audio(self):
        """Transcribe 5s audio with real tiny model."""
        from api.whisper_transcribe import transcribe_audio

        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        text, metadata = transcribe_audio(
            str(audio_path),
            language="en",
            model_size="tiny",
        )

        assert isinstance(text, str)
        assert isinstance(metadata, dict)
        assert "transcription_time_ms" in metadata
        assert metadata["transcription_time_ms"] > 0

    def test_transcribe_audio_returns_metadata(self):
        """Metadata should include performance metrics."""
        from api.whisper_transcribe import transcribe_audio

        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        _, metadata = transcribe_audio(
            str(audio_path),
            language="en",
            model_size="tiny",
        )

        assert "transcription_time_ms" in metadata
        assert "model_load_time_ms" in metadata
        assert "realtime_factor" in metadata
        assert "audio_duration_seconds" in metadata
        assert "backend" in metadata

    def test_transcribe_audio_chunked(self):
        """Transcribe 120s audio with chunking."""
        from api.whisper_transcribe import transcribe_audio_chunked

        audio_path = FIXTURES_DIR / "120s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        text, metadata = transcribe_audio_chunked(
            str(audio_path),
            language="en",
            model_size="tiny",
            enable_chunking=True,
        )

        assert isinstance(text, str)
        assert metadata.get("chunking_enabled") is True
        assert metadata.get("total_chunks", 0) >= 1


class TestBackendSwitching:
    """Test backend selection."""

    def test_device_detector_returns_cpu(self):
        """DeviceDetector should return cpu in test environment."""
        from api.device_detector import DeviceDetector

        device = DeviceDetector.detect()
        assert device in ("cpu", "mps")

    def test_strategy_auto_configures_cpu(self):
        """TranscriptionStrategy should configure CPU correctly."""
        from api.transcription_strategy import TranscriptionStrategy

        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=300,
            quality_mode="balanced",
        )

        assert strategy.backend == "faster-whisper"
        assert strategy.device == "cpu"
        assert strategy.compute_type == "int8"
        assert strategy.beam_size == 3


class TestBatchedInference:
    """Test BatchedInferencePipeline integration."""

    def test_faster_whisper_backend_supports_batched(self):
        """FasterWhisperBackend should support batched inference."""
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        backend = FasterWhisperBackend(device="cpu")
        assert backend.supports_batched is True

    def test_whisper_cpp_backend_does_not_support_batched(self):
        """WhisperCppBackend should not support batched inference."""
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        backend = WhisperCppBackend()
        assert backend.supports_batched is False
        with pytest.raises(NotImplementedError):
            backend.transcribe_batched("/tmp/test.wav", "en")
