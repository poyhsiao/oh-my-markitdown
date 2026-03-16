"""Tests for api/constants.py"""

import pytest
from api.constants import (
    SUPPORTED_EXTENSIONS,
    OCR_LANGUAGES,
    SUPPORTED_LANGUAGES,
    CLEANUP_TYPES,
    WHISPER_MODEL_CACHE_SIZE,
)


class TestConstants:
    """Test centralized constants."""

    def test_supported_extensions(self):
        """Test supported file extensions."""
        assert '.pdf' in SUPPORTED_EXTENSIONS
        assert '.docx' in SUPPORTED_EXTENSIONS
        assert '.mp3' in SUPPORTED_EXTENSIONS
        assert len(SUPPORTED_EXTENSIONS) > 10

    def test_ocr_languages(self):
        """Test OCR language codes."""
        assert 'chi_tra' in OCR_LANGUAGES
        assert 'chi_sim' in OCR_LANGUAGES
        assert 'eng' in OCR_LANGUAGES
        assert 'jpn' in OCR_LANGUAGES
        assert OCR_LANGUAGES['chi_tra'] == '繁體中文'

    def test_supported_languages(self):
        """Test Whisper transcription languages."""
        assert 'zh' in SUPPORTED_LANGUAGES
        assert 'en' in SUPPORTED_LANGUAGES
        assert 'ja' in SUPPORTED_LANGUAGES

    def test_cleanup_types(self):
        """Test cleanup type constants."""
        assert 'youtube' in CLEANUP_TYPES
        assert 'ocr' in CLEANUP_TYPES
        assert 'uploads' in CLEANUP_TYPES
        assert 'all' in CLEANUP_TYPES

    def test_whisper_cache_size(self):
        """Test Whisper model cache size."""
        assert isinstance(WHISPER_MODEL_CACHE_SIZE, int)
        assert WHISPER_MODEL_CACHE_SIZE > 0
        assert WHISPER_MODEL_CACHE_SIZE == 3
