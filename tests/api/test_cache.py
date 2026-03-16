"""Tests for ModelCache in whisper_transcribe.py"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MockWhisperModel:
    """Mock WhisperModel for testing."""
    def __init__(self, name):
        self.name = name


class TestModelCache:
    """Test ModelCache LRU implementation."""

    def test_cache_initialization(self):
        """Test cache initializes with correct max_size."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        assert cache._max_size == 2
        assert len(cache._cache) == 0

    def test_cache_get_miss(self):
        """Test cache get returns None for missing key."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_set_and_get(self):
        """Test cache stores and retrieves models."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        model = MockWhisperModel("test_model")
        
        cache.set("key1", model)
        result = cache.get("key1")
        
        assert result is model

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        
        cache.set("key1", MockWhisperModel("model1"))
        cache.set("key2", MockWhisperModel("model2"))
        cache.set("key3", MockWhisperModel("model3"))
        
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_access_order(self):
        """Test cache access updates LRU order."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        
        cache.set("key1", MockWhisperModel("model1"))
        cache.set("key2", MockWhisperModel("model2"))
        
        cache.get("key1")
        cache.set("key3", MockWhisperModel("model3"))
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is None

    def test_cache_clear(self):
        """Test cache clear removes all items."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        cache.set("key1", MockWhisperModel("model1"))
        cache.set("key2", MockWhisperModel("model2"))
        
        count = cache.clear()
        
        assert count == 2
        assert len(cache._cache) == 0

    def test_cache_remove(self):
        """Test cache remove specific key."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        cache.set("key1", MockWhisperModel("model1"))
        
        result = cache.remove("key1")
        
        assert result is True
        assert cache.get("key1") is None

    def test_cache_remove_nonexistent(self):
        """Test remove returns False for nonexistent key."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=2)
        result = cache.remove("nonexistent")
        
        assert result is False

    def test_cache_get_info(self):
        """Test cache info returns correct metadata."""
        from api.whisper_transcribe import ModelCache
        
        cache = ModelCache(max_size=3)
        cache.set("key1", MockWhisperModel("model1"))
        
        info = cache.get_info()
        
        assert info["max_size"] == 3
        assert info["current_size"] == 1
        assert "key1" in info["cached_models"]
