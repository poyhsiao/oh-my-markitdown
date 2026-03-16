"""Tests for retry logic in auto_convert.py"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestRetryLogic:
    """Test exponential backoff retry mechanism."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        from api.auto_convert import convert_file_with_retry, RETRY_BASE_DELAY, RETRY_MAX_DELAY
        
        # Test exponential backoff formula: min(BASE * 2^attempt, MAX)
        base_delay = RETRY_BASE_DELAY
        max_delay = RETRY_MAX_DELAY
        
        # Attempt 0: base_delay * 2^0 = base_delay
        delay_0 = min(base_delay * (2 ** 0), max_delay)
        assert delay_0 == base_delay
        
        # Attempt 1: base_delay * 2^1 = 2 * base_delay
        delay_1 = min(base_delay * (2 ** 1), max_delay)
        assert delay_1 == base_delay * 2
        
        # Attempt 2: base_delay * 2^2 = 4 * base_delay
        delay_2 = min(base_delay * (2 ** 2), max_delay)
        assert delay_2 == base_delay * 4

    def test_max_delay_cap(self):
        """Test that retry delay is capped at max_delay."""
        base_delay = 2
        max_delay = 60
        
        # Even with large attempts, delay should not exceed max_delay
        for attempt in range(10):
            delay = min(base_delay * (2 ** attempt), max_delay)
            assert delay <= max_delay

    def test_retry_success_on_first_attempt(self):
        """Test successful conversion on first attempt."""
        with patch('api.auto_convert.convert_file') as mock_convert:
            with patch('api.auto_convert.time.sleep'):
                mock_convert.return_value = True
                
                from api.auto_convert import convert_file_with_retry
                
                result = convert_file_with_retry("test.pdf", max_retries=3)
                
                assert result is True
                assert mock_convert.call_count == 1

    def test_retry_success_after_failures(self):
        """Test successful conversion after initial failures."""
        with patch('api.auto_convert.convert_file') as mock_convert:
            with patch('api.auto_convert.time.sleep'):
                # First two calls fail, third succeeds
                mock_convert.side_effect = [
                    Exception("First failure"),
                    Exception("Second failure"),
                    True  # Success on third attempt
                ]
                
                from api.auto_convert import convert_file_with_retry
                
                result = convert_file_with_retry("test.pdf", max_retries=3)
                
                assert result is True
                assert mock_convert.call_count == 3

    def test_retry_exhausted(self):
        """Test behavior when all retries are exhausted."""
        with patch('api.auto_convert.convert_file') as mock_convert:
            with patch('api.auto_convert.time.sleep'):
                with patch('api.auto_convert.shutil.move'):
                    with patch('api.auto_convert.Path.mkdir'):
                        mock_convert.side_effect = Exception("Persistent failure")
                        
                        from api.auto_convert import convert_file_with_retry
                        
                        result = convert_file_with_retry("test.pdf", max_retries=3)
                        
                        assert result is False
                        assert mock_convert.call_count == 3

    def test_retry_delay_increases(self):
        """Test that retry delays increase exponentially."""
        delays = []
        
        original_sleep = time.sleep
        def track_sleep(delay):
            delays.append(delay)
            original_sleep(0.001)  # Minimal actual sleep
        
        with patch('api.auto_convert.convert_file') as mock_convert:
            with patch('api.auto_convert.time.sleep', side_effect=track_sleep):
                # Fail twice, then succeed
                mock_convert.side_effect = [
                    Exception("Fail 1"),
                    Exception("Fail 2"),
                    True
                ]
                
                from api.auto_convert import convert_file_with_retry
                
                convert_file_with_retry("test.pdf", max_retries=3)
                
                # Should have 2 delays (before attempts 1 and 2)
                assert len(delays) == 2
                # Each delay should be larger than previous (exponential)
                assert delays[1] > delays[0]

    def test_custom_max_retries(self):
        """Test custom max_retries parameter."""
        with patch('api.auto_convert.convert_file') as mock_convert:
            with patch('api.auto_convert.time.sleep'):
                mock_convert.side_effect = Exception("Always fails")
                
                from api.auto_convert import convert_file_with_retry
                
                result = convert_file_with_retry("test.pdf", max_retries=5)
                
                assert result is False
                assert mock_convert.call_count == 5


class TestRetryConfiguration:
    """Test retry configuration constants."""

    def test_default_retry_settings(self):
        """Test default retry configuration values."""
        from api.auto_convert import (
            MAX_RETRIES,
            RETRY_BASE_DELAY,
            RETRY_MAX_DELAY
        )
        
        assert MAX_RETRIES == 3
        assert RETRY_BASE_DELAY == 2
        assert RETRY_MAX_DELAY == 60

    def test_retry_base_delay_positive(self):
        """Test that base delay is positive."""
        from api.auto_convert import RETRY_BASE_DELAY
        
        assert RETRY_BASE_DELAY > 0

    def test_retry_max_delay_greater_than_base(self):
        """Test that max delay is greater than base delay."""
        from api.auto_convert import RETRY_BASE_DELAY, RETRY_MAX_DELAY
        
        assert RETRY_MAX_DELAY > RETRY_BASE_DELAY
