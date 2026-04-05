"""Unit tests for synchronous model pre-warm."""
import pytest
from unittest.mock import patch, MagicMock, call


class TestSyncPreWarm:
    """Test synchronous model pre-warming."""

    @patch("api.main.get_model")
    def test_sync_prewarm_loads_all_models(self, mock_get_model):
        """sync_prewarm_models should load all models in PRE_WARM_MODELS."""
        from api.main import sync_prewarm_models
        from api.constants import PRE_WARM_MODELS

        sync_prewarm_models()

        assert mock_get_model.call_count == len(PRE_WARM_MODELS)
        for i, (model_size, device, compute_type, cpu_threads) in enumerate(PRE_WARM_MODELS):
            mock_get_model.assert_any_call(
                model_size, device, compute_type, cpu_threads=cpu_threads
            )

    @patch("api.main.get_model")
    def test_sync_prewarm_continues_on_failure(self, mock_get_model):
        """sync_prewarm_models should continue if one model fails."""
        from api.main import sync_prewarm_models

        mock_get_model.side_effect = [
            Exception("Download failed"),
            MagicMock(),
        ]

        sync_prewarm_models()
        assert mock_get_model.call_count == 2
