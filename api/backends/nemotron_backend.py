"""Nemotron ASR backend — NVIDIA NeMo nvidia/nemotron-3.5-asr-streaming-0.6b."""
from typing import TYPE_CHECKING

from api.backends.protocol import TranscriptionBackend

if TYPE_CHECKING:
    from api.backends._nemo_loader import ASRModel
    from api.whisper_transcribe import ModelCache

DEFAULT_MODEL = "nvidia/nemotron-3.5-asr-streaming-0.6b"


class NemotronAsrBackend(TranscriptionBackend):
    """NeMo Nemotron ASR backend for CPU and CUDA devices."""

    def __init__(self, device: str = "cpu", model_cache: "ModelCache | None" = None):
        self.name = "nemotron-asr"
        self.device = device
        self.supported_compute_types = self._get_supported_compute_types()
        self.supports_batched = False
        self._model_cache = model_cache
        self._model: "ASRModel | None" = None

    def _get_supported_compute_types(self) -> list[str]:
        if self.device == "cpu":
            return ["float32"]
        return ["float16", "float32"]

    def load_model(
        self,
        model_size: str | None = None,
        compute_type: str = "float32",
    ) -> None:
        from api.backends._nemo_loader import _get_asr_model

        model_name = model_size or DEFAULT_MODEL
        cache_key = f"{model_name}_{self.device}_{compute_type}"

        if self._model_cache and self._model_cache.get(cache_key) is not None:
            self._model = self._model_cache.get(cache_key)
            return

        ASRModel = _get_asr_model()
        model = ASRModel.from_pretrained(model_name)
        if self.device != "cpu":
            import torch

            model = model.to(torch.device(self.device))
            model.eval()
        else:
            model.eval()

        if self._model_cache:
            self._model_cache.set(cache_key, model)
        self._model = model

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[str, dict]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        transcribe_kwargs: dict = {
            "timestamps": word_timestamps,
        }
        if language:
            transcribe_kwargs["source_lang"] = language

        hypotheses = self._model.transcribe([audio_path], **transcribe_kwargs)
        hypothesis = hypotheses[0]

        transcript = hypothesis.text or ""
        segments = []
        if word_timestamps and hypothesis.timestamp:
            for stamp in hypothesis.timestamp.get("word", []):
                segments.append({
                    "start": stamp["start"],
                    "end": stamp["end"],
                    "text": stamp["word"],
                })

        metadata: dict = {
            "language": language or "auto",
            "duration": None,
            "segments_count": len(segments),
            "model": DEFAULT_MODEL,
            "device": self.device,
            "backend": "nemotron-asr",
            "word_timestamps": word_timestamps,
        }
        if segments:
            metadata["segments"] = segments

        return transcript, metadata

    def unload(self) -> None:
        self._model = None
