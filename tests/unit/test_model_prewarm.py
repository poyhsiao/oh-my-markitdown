"""Unit tests for model pre-warm functionality."""
import pytest
from unittest.mock import patch, MagicMock


class TestModelPreWarm:
    """Test model pre-warming at startup."""

    @patch("api.main.get_model")
    def test_startup_pre_warms_models(self, mock_get_model):
        """Startup event should pre-warm tiny and base models."""
        from api.main import startup_event
        startup_event()
        # Should pre-warm at least tiny and base models
        assert mock_get_model.call_count >= 2
        call_args = [call[0][0] for call in mock_get_model.call_args_list]
        assert "tiny" in call_args
        assert "base" in call_args

    @patch("api.main.get_model")
    def test_pre_warm_uses_cpu_and_int8(self, mock_get_model):
        """Pre-warmed models should use CPU and int8 by default."""
        from api.main import startup_event
        startup_event()
        # Check that cpu_threads and compute_type are passed correctly
        for call in mock_get_model.call_args_list:
            kwargs = call[1] if call[1] else {}
            # device should be cpu (default)
            assert kwargs.get("device", "cpu") == "cpu"
            # compute_type should be int8 (default)
            assert kwargs.get("compute_type", "int8") == "int8"


class TestPreWarmConfig:
    """Test pre-warm configuration constants."""

    def test_pre_warm_models_list_exists(self):
        """PRE_WARM_MODELS should be defined in constants."""
        from api.constants import PRE_WARM_MODELS
        assert isinstance(PRE_WARM_MODELS, list)
        assert len(PRE_WARM_MODELS) >= 2

    def test_pre_warm_includes_tiny_and_base(self):
        """Pre-warm should include at least tiny and base."""
        from api.constants import PRE_WARM_MODELS
        model_names = [m[0] for m in PRE_WARM_MODELS]
        assert "tiny" in model_names
        assert "base" in model_names
