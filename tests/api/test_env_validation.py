"""
Tests for Environment Variable Validation on Startup

TDD: Write failing tests first, then implement to pass.

Requirements from spec:
- Environment variable validation on startup
- Invalid configs should fail with clear error messages
- Valid configs should start successfully
"""

import pytest
import os
from unittest.mock import patch


class TestEnvironmentValidation:
    """Test environment variable validation on startup."""

    def test_invalid_api_port_raises_error(self):
        """Test that non-numeric API_PORT raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'API_PORT': 'invalid'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'API_PORT' in str(exc_info.value)

    def test_negative_api_port_raises_error(self):
        """Test that negative API_PORT raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'API_PORT': '-1'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'API_PORT' in str(exc_info.value)

    def test_zero_api_port_raises_error(self):
        """Test that zero API_PORT raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'API_PORT': '0'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'API_PORT' in str(exc_info.value)

    def test_valid_api_port_passes(self):
        """Test that valid API_PORT passes validation."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'API_PORT': '8080'}):
            # Should not raise
            try:
                validate_environment()
            except ValueError as e:
                pytest.fail(f"Valid API_PORT should not raise: {e}")

    def test_invalid_max_upload_size_raises_error(self):
        """Test that non-numeric MAX_UPLOAD_SIZE raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'MAX_UPLOAD_SIZE': 'not_a_number'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'MAX_UPLOAD_SIZE' in str(exc_info.value)

    def test_negative_max_upload_size_raises_error(self):
        """Test that negative MAX_UPLOAD_SIZE raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'MAX_UPLOAD_SIZE': '-100'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'MAX_UPLOAD_SIZE' in str(exc_info.value)

    def test_valid_ocr_language_passes(self):
        """Test that valid OCR language combination passes validation."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'DEFAULT_OCR_LANG': 'chi_tra+eng'}):
            try:
                validate_environment()
            except ValueError as e:
                pytest.fail(f"Valid OCR language should not raise: {e}")

    def test_invalid_ocr_language_raises_error(self):
        """Test that invalid OCR language raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'DEFAULT_OCR_LANG': 'invalid_lang'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'OCR' in str(exc_info.value)

    def test_valid_whisper_model_passes(self):
        """Test that valid Whisper model size passes validation."""
        from api.config import validate_environment
        
        valid_models = ['tiny', 'base', 'small', 'medium', 'large']
        for model in valid_models:
            with patch.dict(os.environ, {'WHISPER_MODEL': model}):
                try:
                    validate_environment()
                except ValueError as e:
                    pytest.fail(f"Valid Whisper model '{model}' should not raise: {e}")

    def test_invalid_whisper_model_raises_error(self):
        """Test that invalid Whisper model raises validation error."""
        from api.config import validate_environment
        
        with patch.dict(os.environ, {'WHISPER_MODEL': 'huge'}):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()
            assert 'WHISPER_MODEL' in str(exc_info.value)

    def test_all_defaults_are_valid(self):
        """Test that all default values pass validation."""
        from api.config import validate_environment
        
        # Remove all custom env vars to test defaults
        env_keys_to_remove = [
            'API_PORT', 'API_PORT_INTERNAL', 'API_DEBUG', 'API_WORKERS',
            'MAX_UPLOAD_SIZE', 'UPLOAD_TIMEOUT', 'UPLOAD_CHUNK_SIZE', 'UPLOAD_BUFFER_SIZE',
            'DEFAULT_OCR_LANG', 'ENABLE_PLUGINS_BY_DEFAULT',
            'WHISPER_MODEL', 'WHISPER_DEVICE', 'WHISPER_COMPUTE_TYPE',
            'CONCURRENT_MAX_REQUESTS', 'CONCURRENT_QUEUE_TIMEOUT',
        ]
        
        env_copy = {k: v for k, v in os.environ.items() if k not in env_keys_to_remove}
        
        with patch.dict(os.environ, env_copy, clear=True):
            try:
                validate_environment()
            except ValueError as e:
                pytest.fail(f"Default values should all be valid: {e}")


class TestConfigModule:
    """Test that config module exports validation function."""

    def test_config_module_exists(self):
        """Test that api.config module exists."""
        import importlib
        try:
            importlib.import_module('api.config')
        except ImportError:
            pytest.fail("api.config module does not exist")

    def test_validate_environment_function_exists(self):
        """Test that validate_environment function exists."""
        from api.config import validate_environment
        assert callable(validate_environment)