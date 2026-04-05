"""Faster-Whisper backend implementation. Supports CPU, CUDA, and ROCm devices."""
from typing import Iterator, Any

from faster_whisper import WhisperModel
from faster_whisper import BatchedInferencePipeline

from api.backends.protocol import TranscriptionBackend
from api.whisper_transcribe import _model_cache, ModelCache


class FasterWhisperBackend(TranscriptionBackend):
    """Faster-Whisper backend for CPU, CUDA, and ROCm."""

    def __init__(self, device: str = "cpu", model_cache: ModelCache | None = None):
        self.name = "faster-whisper"
        self.device = device
        self.supported_compute_types = self._get_supported_compute_types()
        self.supports_batched = True
        self._model_cache = model_cache or _model_cache
        self._base_model: WhisperModel | None = None
        self._batched_model: Any = None

    def _get_supported_compute_types(self) -> list[str]:
        if self.device == "cpu":
            return ["int8", "float32"]
        return ["float16", "int8", "int8_float16"]

    def load_model(
        self,
        model_size: str,
        compute_type: str,
        cpu_threads: int = 4,
        use_batched: bool = False,
        **kwargs,
    ) -> None:
        cache_key = f"{model_size}_{self.device}_{compute_type}_{cpu_threads}_{'batched' if use_batched else 'standard'}"
        cached = self._model_cache.get(cache_key)
        if cached is not None:
            if use_batched:
                self._batched_model = cached  # type: ignore[assignment]
            else:
                self._base_model = cached
            return

        base_model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )

        if use_batched:
            batched_model = BatchedInferencePipeline(model=base_model)
            self._batched_model = batched_model
            self._model_cache.set(cache_key, batched_model)  # type: ignore[arg-type]
        else:
            self._base_model = base_model
            self._model_cache.set(cache_key, base_model)

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
        if self._base_model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        segments, info = self._base_model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            vad_parameters=vad_params if vad_filter else None,
            word_timestamps=word_timestamps,
        )
        return segments, info  # type: ignore[return-value]

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
        if self._batched_model is None:
            raise RuntimeError("Batched model not loaded. Call load_model(use_batched=True) first.")

        segments, info = self._batched_model.transcribe(
            audio_path,
            language=language,
            batch_size=batch_size,
            chunk_length=chunk_length_s,
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            vad_parameters=vad_params if vad_filter else None,
            word_timestamps=word_timestamps,
        )
        return segments, info  # type: ignore[return-value]

    def unload(self) -> None:
        self._base_model = None
        self._batched_model = None