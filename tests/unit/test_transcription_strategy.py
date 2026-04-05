"""Tests for TranscriptionStrategy auto-configuration."""

from api.transcription_strategy import TranscriptionStrategy


class TestTranscriptionStrategy:
    """Test suite for TranscriptionStrategy auto-configuration."""

    def test_cuda_speed_mode(self):
        """CUDA with speed mode uses beam_size=1, batched=True, compute_type=float16."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            quality_mode="speed",
        )
        assert strategy.backend == "faster-whisper"
        assert strategy.device == "cuda"
        assert strategy.compute_type == "float16"
        assert strategy.use_batched is True
        assert strategy.beam_size == 1

    def test_cuda_balanced_mode(self):
        """CUDA with balanced mode uses beam_size=3."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            quality_mode="balanced",
        )
        assert strategy.beam_size == 3

    def test_cuda_quality_mode(self):
        """CUDA with quality mode uses beam_size=5."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            quality_mode="quality",
        )
        assert strategy.beam_size == 5

    def test_mps_uses_whisper_cpp(self):
        """MPS device uses whisper-cpp backend with batched=False."""
        strategy = TranscriptionStrategy.auto_configure(
            device="mps",
            audio_duration=60,
            quality_mode="balanced",
        )
        assert strategy.backend == "whisper-cpp"
        assert strategy.use_batched is False
        assert strategy.max_workers == 4

    def test_mps_speed_mode_uses_int8(self):
        """MPS with speed mode uses int8 compute type."""
        strategy = TranscriptionStrategy.auto_configure(
            device="mps",
            audio_duration=60,
            quality_mode="speed",
        )
        assert strategy.compute_type == "int8"

    def test_cpu_long_audio_uses_parallel(self):
        """CPU with long audio (>90s) uses parallel workers."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=600,
            quality_mode="balanced",
        )
        assert strategy.max_workers == 4

    def test_cpu_short_audio_no_parallel(self):
        """CPU with short audio (<=90s) uses single worker."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=30,
            quality_mode="balanced",
        )
        assert strategy.max_workers == 1

    def test_rocm_uses_faster_whisper(self):
        """ROCm device uses faster-whisper backend with batched=True."""
        strategy = TranscriptionStrategy.auto_configure(
            device="rocm",
            audio_duration=60,
            quality_mode="balanced",
        )
        assert strategy.backend == "faster-whisper"
        assert strategy.use_batched is True

    def test_explicit_beam_size_overrides_preset(self):
        """Explicit beam_size parameter overrides preset value."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            quality_mode="speed",
            beam_size=7,
        )
        assert strategy.beam_size == 7

    def test_explicit_temperature_overrides_preset(self):
        """Explicit temperature parameter overrides preset value."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            quality_mode="balanced",
            temperature=0.5,
        )
        assert strategy.temperature == 0.5

    def test_default_quality_is_balanced(self):
        """Default quality mode is balanced when not specified."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
        )
        assert strategy.beam_size == 3
        assert strategy.temperature == 0.0

    def test_cpu_uses_faster_whisper(self):
        """CPU device uses faster-whisper backend."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=60,
            quality_mode="balanced",
        )
        assert strategy.backend == "faster-whisper"

    def test_cpu_uses_int8_compute_type(self):
        """CPU device uses int8 compute type."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=60,
            quality_mode="balanced",
        )
        assert strategy.compute_type == "int8"

    def test_explicit_use_batched_overrides_default(self):
        """Explicit use_batched parameter overrides default for CUDA."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            use_batched=False,
        )
        assert strategy.use_batched is False

    def test_batch_size_passed_through(self):
        """Batch size parameter is passed through to strategy."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=60,
            batch_size=16,
        )
        assert strategy.batch_size == 16

    def test_cpu_threads_passed_through(self):
        """CPU threads parameter is passed through to strategy."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=60,
            cpu_threads=4,
        )
        assert strategy.cpu_threads == 4

    def test_default_cpu_threads_when_not_specified(self):
        """Default CPU threads is used when not specified."""
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=60,
        )
        assert strategy.cpu_threads == 8
