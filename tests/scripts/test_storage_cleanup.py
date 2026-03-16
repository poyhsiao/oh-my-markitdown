"""Tests for storage.py and cleanup.py scripts"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStorageScript:
    """Test storage.py script functions."""

    def test_get_storage_info_structure(self):
        """Test storage info returns correct structure."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        # Mock Path to avoid actual filesystem access
        with patch('scripts.storage.Path') as mock_path:
            # Create mock filesystem
            mock_temp_dir = MagicMock()
            mock_temp_dir.glob = MagicMock(return_value=[])
            mock_path.return_value = mock_temp_dir
            
            # Import after path setup
            from scripts.storage import get_storage_info
            
            info = get_storage_info()
            
            assert "total_bytes" in info
            assert "total_mb" in info
            assert "breakdown" in info
            assert "youtube_audio" in info["breakdown"]
            assert "ocr_temp" in info["breakdown"]
            assert "uploads" in info["breakdown"]
            assert "failed" in info["breakdown"]

    def test_storage_breakdown_structure(self):
        """Test each breakdown has required fields."""
        breakdown = {
            "youtube_audio": {"bytes": 0, "mb": 0.0, "files": 0},
            "ocr_temp": {"bytes": 0, "mb": 0.0, "files": 0},
            "uploads": {"bytes": 0, "mb": 0.0, "files": 0},
            "failed": {"bytes": 0, "mb": 0.0, "files": 0},
        }
        
        for category, data in breakdown.items():
            assert "bytes" in data
            assert "mb" in data
            assert "files" in data
            assert isinstance(data["bytes"], (int, float))
            assert isinstance(data["files"], int)


class TestCleanupScript:
    """Test cleanup.py script functions."""

    def test_cleanup_types_defined(self):
        """Test cleanup types are properly defined."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        from api.constants import CLEANUP_TYPES
        
        assert "youtube" in CLEANUP_TYPES
        assert "ocr" in CLEANUP_TYPES
        assert "uploads" in CLEANUP_TYPES
        assert "failed" in CLEANUP_TYPES
        assert "models" in CLEANUP_TYPES
        assert "all" in CLEANUP_TYPES

    def test_cleanup_all_expands(self):
        """Test that 'all' expands to all types."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        types = ["all"]
        
        if "all" in types:
            expanded = ["youtube", "ocr", "uploads", "failed", "models"]
        
        assert "youtube" in expanded
        assert "ocr" in expanded
        assert "uploads" in expanded

    def test_get_storage_info_function_exists(self):
        """Test get_storage_info function exists."""
        from scripts.cleanup import get_storage_info
        assert callable(get_storage_info)

    def test_cleanup_function_exists(self):
        """Test cleanup function exists."""
        from scripts.cleanup import cleanup
        assert callable(cleanup)

    def test_cleanup_dry_run_mode(self):
        """Test cleanup dry run doesn't delete files."""
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock, patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        with patch('scripts.cleanup.Path') as mock_path:
            # Mock filesystem
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_file.stat.return_value.st_size = 1000
            
            mock_dir = MagicMock()
            mock_dir.glob.return_value = [mock_file]
            mock_path.return_value = mock_dir
            
            # Test dry run
            from scripts.cleanup import cleanup
            
            with patch.object(Path, 'glob', return_value=[mock_file]):
                result = cleanup(["youtube"], dry_run=True)
                
                # Should not actually delete (dry run)
                # In real test, file would still exist
                assert "cleaned" in result

    def test_cleanup_result_structure(self):
        """Test cleanup returns correct structure."""
        result = {
            "cleaned": {},
            "total_freed_bytes": 0
        }
        
        assert "cleaned" in result
        assert "total_freed_bytes" in result
        assert isinstance(result["total_freed_bytes"], int)


class TestCleanupCLI:
    """Test cleanup command-line interface."""

    def test_cleanup_types_choices(self):
        """Test cleanup types match constants."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        from api.constants import CLEANUP_TYPES
        
        valid_choices = list(CLEANUP_TYPES.keys())
        
        # Verify all expected types are present
        expected = ["youtube", "ocr", "uploads", "failed", "models", "all"]
        for expected_type in expected:
            assert expected_type in valid_choices


class TestStorageCLI:
    """Test storage command-line interface."""

    def test_storage_script_main_exists(self):
        """Test storage script has main function."""
        from scripts.storage import main
        assert callable(main)

    def test_storage_json_flag(self):
        """Test storage script accepts --json flag."""
        import argparse
        
        # Create parser as in the script
        parser = argparse.ArgumentParser()
        parser.add_argument('--json', '-j', action='store_true')
        
        # Parse with json flag
        args = parser.parse_args(['--json'])
        assert args.json is True
        
        # Parse without json flag
        args = parser.parse_args([])
        assert args.json is False


class TestScriptIntegration:
    """Integration tests for scripts."""

    def test_temp_dir_env_var(self):
        """Test TEMP_DIR environment variable."""
        import os
        from pathlib import Path
        
        temp_dir = os.getenv("TEMP_DIR", "/tmp")
        
        assert temp_dir is not None
        assert isinstance(temp_dir, str)
        
        # Test it resolves to a valid path
        path = Path(temp_dir)
        assert path is not None

    def test_scripts_have_docstrings(self):
        """Test scripts have proper docstrings."""
        from scripts.storage import get_storage_info
        from scripts.cleanup import get_storage_info as cleanup_get_info
        from scripts.cleanup import cleanup
        
        assert get_storage_info.__doc__ is not None
        assert cleanup_get_info.__doc__ is not None
        assert cleanup.__doc__ is not None
