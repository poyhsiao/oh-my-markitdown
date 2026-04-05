"""
Tests for auto model selection functionality.
"""

import pytest
from api.whisper_transcribe import get_recommended_model
from api.constants import MODEL_SELECTION_THRESHOLDS


class TestGetRecommendedModel:
    """Test cases for get_recommended_model function."""

    def test_tiny_model_for_short_audio(self):
        """Test that tiny model is recommended for audio under 2 minutes."""
        assert get_recommended_model(60) == "tiny"
        assert get_recommended_model(119) == "tiny"
        assert get_recommended_model(0) == "tiny"

    def test_base_model_for_medium_audio(self):
        """Test that base model is recommended for audio between 2-10 minutes."""
        assert get_recommended_model(120) == "base"
        assert get_recommended_model(300) == "base"
        assert get_recommended_model(599) == "base"

    def test_small_model_for_long_audio(self):
        """Test that small model is recommended for audio between 10-30 minutes."""
        assert get_recommended_model(600) == "small"
        assert get_recommended_model(1200) == "small"
        assert get_recommended_model(1799) == "small"

    def test_medium_model_for_very_long_audio(self):
        """Test that medium model is recommended for audio over 30 minutes."""
        assert get_recommended_model(1800) == "medium"
        assert get_recommended_model(3600) == "medium"
        assert get_recommended_model(7200) == "medium"

    def test_threshold_values(self):
        """Test that threshold values from constants are respected."""
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["tiny"] - 1) == "tiny"
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["tiny"]) == "base"
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["base"] - 1) == "base"
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["base"]) == "small"
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["small"] - 1) == "small"
        assert get_recommended_model(MODEL_SELECTION_THRESHOLDS["small"]) == "medium"

    def test_float_durations(self):
        """Test that float durations are handled correctly."""
        assert get_recommended_model(60.5) == "tiny"
        assert get_recommended_model(120.5) == "base"
        assert get_recommended_model(600.5) == "small"
        assert get_recommended_model(1800.5) == "medium"

    def test_zero_duration(self):
        """Test that zero duration returns tiny model."""
        assert get_recommended_model(0) == "tiny"

    def test_negative_duration(self):
        """Test that negative duration returns tiny model (edge case)."""
        assert get_recommended_model(-1) == "tiny"