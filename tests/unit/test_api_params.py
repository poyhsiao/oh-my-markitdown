"""Tests for /convert/audio endpoint parameters - Whisper Performance Optimization Phase 1 Task 1.2

These tests verify that the transcribe_audio_file function accepts the new optimization parameters
with correct default values.
"""

import pytest
import inspect
from fastapi import Query
from api.main import transcribe_audio_file
from api.constants import QUALITY_PRESETS, DEFAULT_BATCH_SIZE


class TestAudioEndpointParameters:
    """Test /convert/audio endpoint parameter defaults and validation."""

    def test_default_quality_mode_is_balanced(self):
        """Test quality_mode default is 'balanced'."""
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters.get("quality_mode")
        assert param is not None, "quality_mode parameter not found"
        actual_default = param.default.default if hasattr(param.default, 'default') else param.default
        assert actual_default == "balanced", f"Expected 'balanced', got '{actual_default}'"

    def test_default_device_is_auto(self):
        """Test device default is None (optional, uses env var)."""
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters.get("device")
        assert param is not None, "device parameter not found"
        actual_default = param.default.default if hasattr(param.default, 'default') else param.default
        assert actual_default is None, f"Expected None, got '{actual_default}'"

    def test_default_batch_size(self):
        """Test batch_size default matches DEFAULT_BATCH_SIZE constant."""
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters.get("batch_size")
        assert param is not None, "batch_size parameter not found"
        actual_default = param.default.default if hasattr(param.default, 'default') else param.default
        assert actual_default == DEFAULT_BATCH_SIZE, f"Expected {DEFAULT_BATCH_SIZE}, got {actual_default}"

    def test_valid_quality_modes(self):
        """Test all valid quality modes are accepted."""
        valid_modes = ["speed", "balanced", "quality"]
        for mode in valid_modes:
            assert mode in QUALITY_PRESETS, f"Quality mode '{mode}' not in QUALITY_PRESETS"

    def test_speed_preset_beam_size(self):
        """Test speed preset has beam_size=1."""
        assert QUALITY_PRESETS["speed"]["beam_size"] == 1

    def test_balanced_preset_beam_size(self):
        """Test balanced preset has beam_size=3."""
        assert QUALITY_PRESETS["balanced"]["beam_size"] == 3

    def test_quality_preset_beam_size(self):
        """Test quality preset has beam_size=5."""
        assert QUALITY_PRESETS["quality"]["beam_size"] == 5

    def test_invalid_quality_mode(self):
        """Test invalid quality mode raises KeyError when accessed."""
        with pytest.raises(KeyError):
            _ = QUALITY_PRESETS["invalid_mode"]

    def test_preset_temperature_is_zero(self):
        """Test all presets have temperature=0.0."""
        for preset_name, preset_config in QUALITY_PRESETS.items():
            assert preset_config["temperature"] == 0.0, (
                f"Preset '{preset_name}' temperature should be 0.0, got {preset_config['temperature']}"
            )


class TestModelSizeParameter:
    """Test model_size parameter default changed from 'base' to 'auto'."""

    def test_model_size_default_is_auto(self):
        """Test model_size default is 'auto' (changed from 'base')."""
        sig = inspect.signature(transcribe_audio_file)
        param = sig.parameters.get("model_size")
        assert param is not None, "model_size parameter not found"
        actual_default = param.default.default if hasattr(param.default, 'default') else param.default
        assert actual_default == "auto", f"Expected 'auto', got '{actual_default}'"


class TestNewParametersExist:
    """Test all 7 new parameters exist in the function signature."""

    def test_quality_mode_parameter_exists(self):
        """Test quality_mode parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "quality_mode" in sig.parameters

    def test_beam_size_parameter_exists(self):
        """Test beam_size parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "beam_size" in sig.parameters

    def test_temperature_parameter_exists(self):
        """Test temperature parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "temperature" in sig.parameters

    def test_use_batched_parameter_exists(self):
        """Test use_batched parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "use_batched" in sig.parameters

    def test_batch_size_parameter_exists(self):
        """Test batch_size parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "batch_size" in sig.parameters

    def test_device_parameter_exists(self):
        """Test device parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "device" in sig.parameters

    def test_cpu_threads_parameter_exists(self):
        """Test cpu_threads parameter exists."""
        sig = inspect.signature(transcribe_audio_file)
        assert "cpu_threads" in sig.parameters