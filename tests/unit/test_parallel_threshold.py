"""Unit tests for dynamic parallel chunking strategy."""
import pytest
from api.constants import (
    PARALLEL_MIN_CHUNKS,
    PARALLEL_MAX_WORKERS_TABLE,
)


class TestParallelThreshold:
    """Test parallel chunking threshold configuration."""

    def test_parallel_min_chunks_exists(self):
        """PARALLEL_MIN_CHUNKS should be defined."""
        assert isinstance(PARALLEL_MIN_CHUNKS, int)
        assert PARALLEL_MIN_CHUNKS >= 2

    def test_parallel_max_workers_table_exists(self):
        """PARALLEL_MAX_WORKERS_TABLE should be defined."""
        assert isinstance(PARALLEL_MAX_WORKERS_TABLE, list)
        assert len(PARALLEL_MAX_WORKERS_TABLE) >= 2


class TestDynamicMaxWorkers:
    """Test dynamic max_workers calculation."""

    def test_get_dynamic_max_workers(self):
        """get_dynamic_max_workers should return appropriate workers based on chunk count."""
        from api.chunking import get_dynamic_max_workers

        # 1 chunk: no parallel needed
        assert get_dynamic_max_workers(1) == 1

        # 2-3 chunks: sequential (overhead > benefit)
        assert get_dynamic_max_workers(2) == 1
        assert get_dynamic_max_workers(3) == 1

        # 4-6 chunks: 2 workers
        assert get_dynamic_max_workers(4) == 2
        assert get_dynamic_max_workers(6) == 2

        # 7+ chunks: 4 workers
        assert get_dynamic_max_workers(7) == 4
        assert get_dynamic_max_workers(30) == 4

    def test_get_dynamic_max_workers_respects_max(self):
        """Should never exceed MAX_MAX_WORKERS."""
        from api.chunking import get_dynamic_max_workers
        from api.constants import MAX_MAX_WORKERS

        assert get_dynamic_max_workers(100) <= MAX_MAX_WORKERS
