"""Unit tests for model pre-warm functionality."""
import pytest
from unittest.mock import patch, MagicMock


class TestModelPreWarm:
    """Test model pre-warming at startup."""

    @patch("api.main.get_model")
    def test_prewarm_loads_all_models(self, mock_get_model):
        """sync_prewarm_models should load all models in PRE_WARM_MODELS."""
        from api.main import sync_prewarm_models
        sync_prewarm_models()
        assert mock_get_model.call_count >= 2
        call_args = [call[0][0] for call in mock_get_model.call_args_list]
        assert "tiny" in call_args
        assert "base" in call_args

    @patch("api.main.get_model")
    def test_prewarm_uses_cpu_and_int8(self, mock_get_model):
        """Pre-warmed models should use CPU and int8 by default."""
        from api.main import sync_prewarm_models
        sync_prewarm_models()
        for call in mock_get_model.call_args_list:
            kwargs = call[1] if call[1] else {}
            assert kwargs.get("device", "cpu") == "cpu"
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
