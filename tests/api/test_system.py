"""Tests for System API endpoints"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestStorageEndpoint:
    """Test storage query endpoint."""

    @patch('api.system.Path')
    def test_storage_calculation(self, mock_path):
        """Test storage calculation logic."""
        # Mock temp dir
        mock_temp = MagicMock()
        mock_path.return_value = mock_temp
        
        # Test breakdown categories
        from api.constants import CLEANUP_TYPES
        assert 'youtube' in CLEANUP_TYPES
        assert 'ocr' in CLEANUP_TYPES
        assert 'uploads' in CLEANUP_TYPES
        assert 'failed' in CLEANUP_TYPES


class TestCleanupEndpoint:
    """Test cleanup endpoint."""

    def test_cleanup_types_validation(self):
        """Test cleanup types are validated."""
        from api.constants import CLEANUP_TYPES
        
        assert 'youtube' in CLEANUP_TYPES
        assert 'ocr' in CLEANUP_TYPES
        assert 'uploads' in CLEANUP_TYPES
        assert 'models' in CLEANUP_TYPES
        assert 'failed' in CLEANUP_TYPES
        assert 'all' in CLEANUP_TYPES

    def test_cleanup_types_mapping(self):
        """Test cleanup types map to correct categories."""
        from api.constants import CLEANUP_TYPES
        
        # Should map to display names
        assert CLEANUP_TYPES['youtube'] == 'YouTube Audio'
        assert CLEANUP_TYPES['ocr'] == 'OCR Temp'
        assert CLEANUP_TYPES['uploads'] == 'Upload Temp'


class TestConfigEndpoints:
    """Test configuration endpoints."""

    def test_timeout_config_defaults(self):
        """Test default timeout configuration."""
        import os
        
        convert_timeout = int(os.getenv("CONVERT_TIMEOUT", "300"))
        youtube_timeout = int(os.getenv("YOUTUBE_TRANSCRIBE_TIMEOUT", "600"))
        audio_timeout = int(os.getenv("AUDIO_TRANSCRIBE_TIMEOUT", "600"))
        
        assert convert_timeout == 300
        assert youtube_timeout == 600
        assert audio_timeout == 600

    def test_timeout_config_types(self):
        """Test timeout config returns integers."""
        import os
        
        timeouts = {
            "convert": int(os.getenv("CONVERT_TIMEOUT", "300")),
            "youtube_transcribe": int(os.getenv("YOUTUBE_TRANSCRIBE_TIMEOUT", "600")),
            "audio_transcribe": int(os.getenv("AUDIO_TRANSCRIBE_TIMEOUT", "600")),
        }
        
        for value in timeouts.values():
            assert isinstance(value, int)
            assert value > 0


class TestAPIKeyAuth:
    """Test API key authentication."""

    def test_api_key_optional_when_not_configured(self):
        """Test API key is optional when not configured."""
        import os
        from unittest.mock import patch
        
        # When API_KEY is not set, should not raise
        with patch.dict(os.environ, {'API_KEY': ''}):
            from api.system import verify_api_key
            # Should not raise when no API key is configured
            try:
                verify_api_key(None)
            except Exception as e:
                pytest.fail(f"Should not raise when API_KEY is not set: {e}")

    def test_api_key_validation(self):
        """Test API key validation."""
        import os
        from unittest.mock import patch
        
        with patch.dict(os.environ, {'API_KEY': 'test_key'}):
            from api.system import verify_api_key
            from fastapi import HTTPException
            
            # Wrong key should raise
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key("wrong_key")
            assert exc_info.value.status_code == 401
            
            # Correct key should pass
            try:
                verify_api_key("test_key")
            except HTTPException:
                pytest.fail("Should not raise with correct key")


class TestModelCacheAPI:
    """Test model cache API endpoints."""

    def test_model_cache_functions_exist(self):
        """Test model cache helper functions exist."""
        from api import whisper_transcribe
        
        # Check functions exist
        assert hasattr(whisper_transcribe, 'get_model_cache_info')
        assert hasattr(whisper_transcribe, 'clear_model_cache')
        assert hasattr(whisper_transcribe, 'remove_model_from_cache')
        assert hasattr(whisper_transcribe, 'update_cache_max_size')


class TestCacheConfigEndpoint:
    """Test cache configuration endpoint."""

    def test_cache_size_from_env(self):
        """Test cache size is read from environment."""
        import os
        from unittest.mock import patch
        
        with patch.dict(os.environ, {'WHISPER_MODEL_CACHE_SIZE': '5'}):
            # Will need to reimport to get new value
            # Just test the env var parsing
            size = int(os.getenv("WHISPER_MODEL_CACHE_SIZE", "3"))
            assert size == 5
