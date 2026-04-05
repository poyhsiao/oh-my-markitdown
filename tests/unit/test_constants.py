"""Tests for api/constants.py - Whisper Performance Optimization"""

import pytest
from api.constants import (
    DEFAULT_VAD_MIN_SILENCE_MS,
    DEFAULT_VAD_THRESHOLD,
    DEFAULT_VAD_SPEECH_PAD_MS,
    DEFAULT_CPU_THREADS,
    QUALITY_PRESETS,
    DEFAULT_CHUNK_BEAM_SIZE,
    DEFAULT_CHUNK_TEMPERATURE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LENGTH_S,
    DEFAULT_MAX_WORKERS,
    MIN_MAX_WORKERS,
    MAX_MAX_WORKERS,
)


class TestVADParameters:
    """Test VAD (Voice Activity Detection) parameters."""

    def test_cpu_threads_default_is_8(self):
        """Test DEFAULT_CPU_THREADS is 8."""
        assert DEFAULT_CPU_THREADS == 8

    def test_vad_min_silence_ms_is_500(self):
        """Test DEFAULT_VAD_MIN_SILENCE_MS is 500."""
        assert DEFAULT_VAD_MIN_SILENCE_MS == 500

    def test_vad_threshold_is_0_5(self):
        """Test DEFAULT_VAD_THRESHOLD is 0.5."""
        assert DEFAULT_VAD_THRESHOLD == 0.5

    def test_vad_speech_pad_ms_is_300(self):
        """Test DEFAULT_VAD_SPEECH_PAD_MS is 300."""
        assert DEFAULT_VAD_SPEECH_PAD_MS == 300


class TestQualityPresets:
    """Test Whisper quality presets."""

    def test_speed_preset(self):
        """Test speed preset has correct values."""
        assert QUALITY_PRESETS["speed"] == {"beam_size": 1, "temperature": 0.0}

    def test_balanced_preset(self):
        """Test balanced preset has beam_size=3."""
        assert QUALITY_PRESETS["balanced"]["beam_size"] == 3

    def test_quality_preset(self):
        """Test quality preset has beam_size=5."""
        assert QUALITY_PRESETS["quality"]["beam_size"] == 5

    def test_all_presets_have_required_keys(self):
        """Test all presets have required keys."""
        required_keys = {"beam_size", "temperature"}
        for preset_name, preset_config in QUALITY_PRESETS.items():
            assert required_keys.issubset(preset_config.keys()), (
                f"Preset '{preset_name}' missing required keys"
            )


class TestChunkConfiguration:
    """Test chunk configuration parameters."""

    def test_default_chunk_beam_size(self):
        """Test DEFAULT_CHUNK_BEAM_SIZE is 1."""
        assert DEFAULT_CHUNK_BEAM_SIZE == 1

    def test_default_chunk_temperature(self):
        """Test DEFAULT_CHUNK_TEMPERATURE is 0.0."""
        assert DEFAULT_CHUNK_TEMPERATURE == 0.0

    def test_default_batch_size(self):
        """Test DEFAULT_BATCH_SIZE is 8."""
        assert DEFAULT_BATCH_SIZE == 8


class TestWorkerConfiguration:
    """Test worker configuration parameters."""

    def test_default_max_workers(self):
        """Test DEFAULT_MAX_WORKERS is 4."""
        assert DEFAULT_MAX_WORKERS == 4