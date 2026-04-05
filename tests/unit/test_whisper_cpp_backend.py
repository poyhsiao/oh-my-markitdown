"""Unit tests for WhisperCppBackend."""
import pytest
from unittest.mock import MagicMock, patch


class TestWhisperCppBackendInit:
    def test_default_device_is_mps(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        backend = WhisperCppBackend()
        assert backend.device == "mps"
        assert backend.name == "whisper-cpp"
        assert backend.supports_batched is False

    def test_supported_compute_types(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        backend = WhisperCppBackend()
        assert "float16" in backend.supported_compute_types
        assert "int8" in backend.supported_compute_types


class TestWhisperCppBackendLoadModel:
    @patch("api.backends.whisper_cpp_backend._model_cache")
    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_load_model_creates_instance(self, mock_whisper, mock_cache):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        mock_cache.get.return_value = None
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        backend = WhisperCppBackend()
        backend.load_model("base", "int8")
        mock_whisper.assert_called_once()
        assert backend._model is not None


class TestWhisperCppBackendTranscribe:
    @patch("api.backends.whisper_cpp_backend._model_cache")
    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_transcribe_calls_model_transcribe(self, mock_whisper, mock_cache):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        mock_cache.get.return_value = None
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test transcript", "segments": [], "duration": 0}
        mock_whisper.return_value = mock_model
        backend = WhisperCppBackend()
        backend.load_model("base", "int8")
        result = backend.transcribe("/tmp/test.wav", "en")
        mock_model.transcribe.assert_called_once()


class TestWhisperCppBackendUnload:
    @patch("api.backends.whisper_cpp_backend._model_cache")
    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_unload_clears_model(self, mock_whisper, mock_cache):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        mock_cache.get.return_value = None
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        backend = WhisperCppBackend()
        backend.load_model("base", "int8")
        backend.unload()
        assert backend._model is None


class TestWhisperCppBackendNoBatched:
    def test_transcribe_batched_raises_not_implemented(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        backend = WhisperCppBackend()
        with pytest.raises(NotImplementedError, match="does not support batched"):
            backend.transcribe_batched("/tmp/test.wav", "en")