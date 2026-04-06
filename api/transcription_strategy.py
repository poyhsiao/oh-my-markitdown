"""TranscriptionStrategy — auto-configuration for optimal transcription."""

from dataclasses import dataclass

from api.constants import (
    DEFAULT_CPU_THREADS,
    DEFAULT_MAX_WORKERS,
    QUALITY_PRESETS,
)


@dataclass
class TranscriptionStrategy:
    """Configuration for a transcription session."""

    backend: str  # "faster-whisper" | "whisper-cpp"
    device: str
    compute_type: str
    use_batched: bool
    batch_size: int
    beam_size: int
    temperature: float
    cpu_threads: int
    max_workers: int

    @classmethod
    def auto_configure(
        cls,
        device: str,
        audio_duration: float,
        quality_mode: str = "standard",
        beam_size: int | None = None,
        temperature: float | None = None,
        use_batched: bool | None = None,
        batch_size: int = 8,
        cpu_threads: int | None = None,
    ) -> "TranscriptionStrategy":
        """Auto-configure optimal strategy based on device and audio."""
        preset = QUALITY_PRESETS.get(quality_mode, QUALITY_PRESETS["standard"])

        if device == "mps":
            backend = "whisper-cpp"
            compute_type = "int8" if quality_mode == "fast" else "float16"
            resolved_use_batched = False
            max_workers = DEFAULT_MAX_WORKERS
        elif device in ("cuda", "rocm"):
            backend = "faster-whisper"
            compute_type = "float16"
            resolved_use_batched = True if use_batched is None else use_batched
            max_workers = 1
        else:
            backend = "faster-whisper"
            compute_type = "int8"
            resolved_use_batched = False
            max_workers = DEFAULT_MAX_WORKERS if audio_duration > 90 else 1

        return cls(
            backend=backend,
            device=device,
            compute_type=compute_type,
            use_batched=resolved_use_batched,
            batch_size=batch_size,
            beam_size=beam_size if beam_size is not None else preset["beam_size"],
            temperature=temperature if temperature is not None else preset["temperature"],
            cpu_threads=cpu_threads or DEFAULT_CPU_THREADS,
            max_workers=max_workers,
        )
