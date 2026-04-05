"""Transcription Backend Protocol — unified interface for all backends."""
from typing import Protocol, Iterator, runtime_checkable


@runtime_checkable
class TranscriptionBackend(Protocol):
    """Unified interface for all transcription backends."""

    name: str
    device: str
    supported_compute_types: list[str]
    supports_batched: bool

    def load_model(self, model_size: str, compute_type: str, **kwargs) -> None:
        """Load transcription model."""
        ...

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
        """Transcribe audio file."""
        ...

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
        """Transcribe audio file with batching."""
        ...

    def unload(self) -> None:
        """Unload model and free resources."""
        ...