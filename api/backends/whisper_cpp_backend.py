"""Whisper.cpp backend implementation for Apple Silicon (MPS)."""
from typing import Iterator

try:
    from whispercpp import Whisper
except ImportError:
    Whisper = None

from api.backends.protocol import TranscriptionBackend
from api.whisper_transcribe import _model_cache, ModelCache


class WhisperCppBackend(TranscriptionBackend):
    """Whisper.cpp backend for Apple Silicon (MPS)."""

    def __init__(self, device: str = "mps", model_cache: ModelCache | None = None):
        self.name = "whisper-cpp"
        self.device = device
        self.supported_compute_types = ["float16", "int8"]
        self.supports_batched = False
        self._model_cache = model_cache or _model_cache
        self._model = None

    def load_model(self, model_size: str, compute_type: str = "int8", **kwargs) -> None:
        if Whisper is None:
            raise ImportError("whispercpp is not installed. Install with: pip install whispercpp>=2.0.0")

        cache_key = f"whispercpp_{model_size}_{compute_type}"
        cached = self._model_cache.get(cache_key)
        if cached is not None:
            self._model = cached
            return

        self._model = Whisper(model_size)
        self._model_cache.set(cache_key, self._model)

    def transcribe(
        self,
        audio_path: str,
        language: str | None,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        result = self._model.transcribe(audio_path)
        segments = iter(result.get("segments", []))
        info = {
            "language": language or "auto",
            "language_probability": 1.0,
            "duration": result.get("duration", 0),
        }
        return segments, info

    def transcribe_batched(
        self,
        audio_path: str,
        language: str | None,
        batch_size: int = 8,
        chunk_length_s: int = 30,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        raise NotImplementedError(
            "WhisperCppBackend does not support batched inference. "
            "Use parallel chunking via ThreadPoolExecutor instead."
        )

    def unload(self) -> None:
        self._model = None