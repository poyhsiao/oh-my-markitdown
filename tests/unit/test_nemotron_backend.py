"""Unit tests for NemotronAsrBackend."""
import pytest
from unittest.mock import MagicMock, patch


class TestNemotronAsrBackendInit:
    def test_default_device_is_cpu(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend()
        assert backend.device == "cpu"
        assert backend.name == "nemotron-asr"

    def test_cuda_device(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend(device="cuda")
        assert backend.device == "cuda"

    def test_supports_batched_is_false(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend()
        assert backend.supports_batched is False

    def test_cpu_supported_compute_types(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend(device="cpu")
        assert "float32" in backend.supported_compute_types

    def test_cuda_supported_compute_types(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend(device="cuda")
        assert "float16" in backend.supported_compute_types
        assert "float32" in backend.supported_compute_types


class TestNemotronAsrBackendLoadModel:
    @patch("api.backends._nemo_loader._get_asr_model")
    def test_load_model_creates_instance(self, mock_get_asr_model):
        from api.backends.nemotron_backend import NemotronAsrBackend

        mock_asr_model_cls = MagicMock()
        mock_model = MagicMock()
        mock_asr_model_cls.from_pretrained.return_value = mock_model
        mock_get_asr_model.return_value = mock_asr_model_cls
        backend = NemotronAsrBackend()
        backend.load_model("nvidia/nemotron-3.5-asr-streaming-0.6b", "float32")
        mock_asr_model_cls.from_pretrained.assert_called_once_with("nvidia/nemotron-3.5-asr-streaming-0.6b")
        assert backend._model is not None

    @patch("api.backends._nemo_loader._get_asr_model")
    def test_load_model_cuda_moves_to_device(self, mock_get_asr_model):
        from api.backends.nemotron_backend import NemotronAsrBackend

        mock_asr_model_cls = MagicMock()
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model  # chain: model.to(...).eval()
        mock_asr_model_cls.from_pretrained.return_value = mock_model
        mock_get_asr_model.return_value = mock_asr_model_cls
        backend = NemotronAsrBackend(device="cuda")
        backend.load_model("nvidia/nemotron-3.5-asr-streaming-0.6b", "float16")
        mock_model.to.assert_called_once()
        mock_model.eval.assert_called_once()


class TestNemotronAsrBackendTranscribe:
    @patch("api.backends._nemo_loader._get_asr_model")
    def test_transcribe_returns_text_and_metadata(self, mock_get_asr_model):
        from api.backends.nemotron_backend import NemotronAsrBackend

        mock_asr_model_cls = MagicMock()
        mock_model = MagicMock()
        mock_hypothesis = MagicMock()
        mock_hypothesis.text = "Hello world"
        mock_hypothesis.timestamp = {"word": []}
        mock_asr_model_cls.from_pretrained.return_value = mock_model
        mock_model.transcribe.return_value = [mock_hypothesis]
        mock_get_asr_model.return_value = mock_asr_model_cls
        backend = NemotronAsrBackend()
        backend.load_model("nvidia/nemotron-3.5-asr-streaming-0.6b", "float32")
        transcript, metadata = backend.transcribe("/tmp/test.wav", "en")
        assert transcript == "Hello world"
        assert "language" in metadata

    def test_transcribe_without_model_raises(self):
        from api.backends.nemotron_backend import NemotronAsrBackend

        backend = NemotronAsrBackend()
        with pytest.raises(RuntimeError, match="Model not loaded"):
            backend.transcribe("/tmp/test.wav", "en")

    @patch("api.backends._nemo_loader._get_asr_model")
    def test_transcribe_with_word_timestamps(self, mock_get_asr_model):
        from api.backends.nemotron_backend import NemotronAsrBackend

        mock_asr_model_cls = MagicMock()
        mock_model = MagicMock()
        mock_hypothesis = MagicMock()
        mock_hypothesis.text = "Hello world"
        mock_hypothesis.timestamp = {
            "word": [
                {"start": 0.0, "end": 0.5, "word": "Hello"},
                {"start": 0.5, "end": 1.0, "word": "world"},
            ]
        }
        mock_asr_model_cls.from_pretrained.return_value = mock_model
        mock_model.transcribe.return_value = [mock_hypothesis]
        mock_get_asr_model.return_value = mock_asr_model_cls
        backend = NemotronAsrBackend()
        backend.load_model("nvidia/nemotron-3.5-asr-streaming-0.6b", "float32")
        _, metadata = backend.transcribe("/tmp/test.wav", "en", word_timestamps=True)
        assert "segments" in metadata
        assert len(metadata["segments"]) == 2


class TestNemotronAsrBackendUnload:
    @patch("api.backends._nemo_loader._get_asr_model")
    def test_unload_clears_model(self, mock_get_asr_model):
        from api.backends.nemotron_backend import NemotronAsrBackend

        mock_asr_model_cls = MagicMock()
        mock_model = MagicMock()
        mock_asr_model_cls.from_pretrained.return_value = mock_model
        mock_get_asr_model.return_value = mock_asr_model_cls
        backend = NemotronAsrBackend()
        backend.load_model("nvidia/nemotron-3.5-asr-streaming-0.6b", "float32")
        backend.unload()
        assert backend._model is None
