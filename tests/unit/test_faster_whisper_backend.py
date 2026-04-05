"""Unit tests for FasterWhisperBackend."""
import pytest
from unittest.mock import MagicMock, patch


class TestFasterWhisperBackendInit:
    def test_default_device_is_cpu(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        backend = FasterWhisperBackend()
        assert backend.device == "cpu"
        assert backend.name == "faster-whisper"
        assert backend.supports_batched is True

    def test_cpu_supported_compute_types(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        backend = FasterWhisperBackend(device="cpu")
        assert "int8" in backend.supported_compute_types

    def test_cuda_supported_compute_types(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        backend = FasterWhisperBackend(device="cuda")
        assert "float16" in backend.supported_compute_types
        assert "int8" in backend.supported_compute_types


class TestFasterWhisperBackendLoadModel:
    @patch("api.backends.faster_whisper_backend.WhisperModel")
    def test_load_model_creates_instance(self, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model
        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")
        mock_whisper_model.assert_called_once()
        assert backend._base_model is not None

    @patch("api.backends.faster_whisper_backend.WhisperModel")
    @patch("api.backends.faster_whisper_backend.BatchedInferencePipeline")
    def test_load_model_with_batched(self, mock_batched, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        mock_base = MagicMock()
        mock_batched_pipeline = MagicMock()
        mock_whisper_model.return_value = mock_base
        mock_batched.return_value = mock_batched_pipeline
        backend = FasterWhisperBackend(device="cuda")
        backend.load_model("base", "float16", use_batched=True)
        mock_whisper_model.assert_called_once()
        mock_batched.assert_called_once()
        assert backend._batched_model is not None


class TestFasterWhisperBackendTranscribe:
    @patch("api.backends.faster_whisper_backend.WhisperModel")
    @patch("api.backends.faster_whisper_backend._model_cache")
    def test_transcribe_calls_model_transcribe(self, mock_cache, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), {"language": "en"})
        mock_whisper_model.return_value = mock_model
        mock_cache.get.return_value = None  # Cache miss
        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")
        segments, info = backend.transcribe("/tmp/test.wav", "en")
        mock_model.transcribe.assert_called_once()


class TestFasterWhisperBackendUnload:
    @patch("api.backends.faster_whisper_backend.WhisperModel")
    def test_unload_clears_models(self, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model
        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")
        backend.unload()
        assert backend._base_model is None
        assert backend._batched_model is None