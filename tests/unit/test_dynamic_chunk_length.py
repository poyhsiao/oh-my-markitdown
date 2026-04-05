"""Unit tests for dynamic chunk length optimization."""
import pytest
from api.chunking import get_dynamic_chunk_duration


class TestDynamicChunkDuration:
    """Test dynamic chunk duration calculation."""

    def test_short_audio_uses_60s_chunks(self):
        """Audio < 300s should use 60s chunks."""
        assert get_dynamic_chunk_duration(60) == 60
        assert get_dynamic_chunk_duration(120) == 60
        assert get_dynamic_chunk_duration(299) == 60

    def test_medium_audio_uses_90s_chunks(self):
        """Audio 300-1800s should use 90s chunks."""
        assert get_dynamic_chunk_duration(300) == 90
        assert get_dynamic_chunk_duration(600) == 90
        assert get_dynamic_chunk_duration(1800) == 90

    def test_long_audio_uses_120s_chunks(self):
        """Audio > 1800s should use 120s chunks."""
        assert get_dynamic_chunk_duration(1801) == 120
        assert get_dynamic_chunk_duration(3600) == 120

    def test_zero_duration_uses_default(self):
        """Zero duration should use default 60s."""
        assert get_dynamic_chunk_duration(0) == 60
