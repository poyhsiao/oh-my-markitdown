"""Unit tests for device detection module."""

import pytest
import os
from unittest.mock import patch, MagicMock

# Check if torch is available for GPU-related tests
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class TestDetectDevice:
    """Test device detection functions."""
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_detect_device_cpu_fallback(self):
        """Test CPU fallback when no GPU available."""
        from api.device_utils import detect_device
        
        with patch('torch.cuda.is_available', return_value=False):
            with patch('torch.backends.mps.is_available', return_value=False):
                device = detect_device()
                assert device == "cpu"
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_detect_device_cuda_priority(self):
        """Test CUDA has highest priority."""
        with patch('torch.cuda.is_available', return_value=True):
            mock_mps = MagicMock()
            mock_mps.is_available = MagicMock(return_value=True)
            
            with patch('torch.backends.mps', mock_mps):
                from api.device_utils import detect_device
                device = detect_device()
                assert device == "cuda"
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_detect_device_mps_fallback(self):
        """Test MPS when CUDA unavailable."""
        with patch('torch.cuda.is_available', return_value=False):
            mock_mps = MagicMock()
            mock_mps.is_available = MagicMock(return_value=True)
            mock_mps.is_built = MagicMock(return_value=True)
            
            with patch('torch.backends.mps', mock_mps):
                from api.device_utils import detect_device
                device = detect_device()
                assert device == "mps"

    def test_detect_device_without_torch(self):
        """Test CPU detection when torch is not available."""
        if TORCH_AVAILABLE:
            pytest.skip("This test verifies behavior when torch is not installed")
        
        from api.device_utils import detect_device
        device = detect_device()
        assert device == "cpu"


class TestGetComputeType:
    """Test compute type selection."""
    
    def test_compute_type_for_cpu(self):
        """Test compute type for CPU."""
        from api.device_utils import get_compute_type_for_device
        
        assert get_compute_type_for_device("cpu") == "int8"
    
    def test_compute_type_for_cuda(self):
        """Test compute type for CUDA."""
        from api.device_utils import get_compute_type_for_device
        
        assert get_compute_type_for_device("cuda") == "float16"
    
    def test_compute_type_for_mps(self):
        """Test compute type for MPS."""
        from api.device_utils import get_compute_type_for_device
        
        assert get_compute_type_for_device("mps") == "float16"


class TestGetDeviceInfo:
    """Test device information retrieval."""
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_get_device_info_basic(self):
        """Test basic device info structure."""
        from api.device_utils import get_device_info
        
        with patch('torch.cuda.is_available', return_value=False):
            mock_mps = MagicMock()
            mock_mps.is_available = MagicMock(return_value=False)
            
            with patch('torch.backends.mps', mock_mps):
                info = get_device_info()
                
                assert "device" in info
                assert "cuda_available" in info
                assert "mps_available" in info
                assert "cpu_count" in info
                assert "recommended_compute_type" in info
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_get_device_info_cuda_details(self):
        """Test CUDA device details."""
        with patch('torch.cuda.is_available', return_value=True):
            with patch('torch.cuda.get_device_name', return_value="NVIDIA RTX 3080"):
                with patch('torch.cuda.device_count', return_value=1):
                    with patch('torch.cuda.get_device_properties') as mock_props:
                        mock_props.return_value = MagicMock(total_memory=10 * 1024**3)
                        
                        from api.device_utils import get_device_info
                        info = get_device_info()
                        
                        assert info["cuda_available"] == True
                        assert info["cuda_device_name"] == "NVIDIA RTX 3080"
                        assert info["cuda_device_count"] == 1

    def test_get_device_info_without_torch(self):
        """Test device info when torch is not available."""
        if TORCH_AVAILABLE:
            pytest.skip("This test verifies behavior when torch is not installed")
        
        from api.device_utils import get_device_info
        info = get_device_info()
        
        assert info["device"] == "cpu"
        assert info["cuda_available"] == False
        assert info["mps_available"] == False


class TestValidateDevice:
    """Test device validation."""
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_validate_auto_device(self):
        """Test auto device resolves to available device."""
        from api.device_utils import validate_device
        
        with patch('torch.cuda.is_available', return_value=False):
            mock_mps = MagicMock()
            mock_mps.is_available = MagicMock(return_value=False)
            
            with patch('torch.backends.mps', mock_mps):
                device = validate_device("auto")
                assert device == "cpu"
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_validate_cuda_unavailable(self):
        """Test CUDA validation when unavailable."""
        from api.device_utils import validate_device
        
        with patch('torch.cuda.is_available', return_value=False):
            with pytest.raises(ValueError, match="CUDA requested but not available"):
                validate_device("cuda")
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")
    def test_validate_mps_unavailable(self):
        """Test MPS validation when unavailable."""
        from api.device_utils import validate_device
        
        mock_mps = MagicMock()
        mock_mps.is_available = MagicMock(return_value=False)
        
        with patch('torch.backends.mps', mock_mps):
            with pytest.raises(ValueError, match="MPS requested but not available"):
                validate_device("mps")
    
    def test_validate_cpu_always_valid(self):
        """Test CPU is always valid."""
        from api.device_utils import validate_device
        
        device = validate_device("cpu")
        assert device == "cpu"


class TestThreadDetection:
    """Test CPU thread detection (will be in device_utils)."""
    
    def test_auto_detect_threads(self):
        """Test automatic thread detection."""
        from api.device_utils import get_recommended_threads
        
        with patch('os.cpu_count', return_value=8):
            threads = get_recommended_threads()
            assert threads == 8
    
    def test_thread_limit(self):
        """Test thread count is limited."""
        from api.device_utils import get_recommended_threads
        
        with patch('os.cpu_count', return_value=16):
            threads = get_recommended_threads()
            # Should be capped at 8
            assert threads == 8
    
    def test_minimum_threads(self):
        """Test minimum thread count."""
        from api.device_utils import get_recommended_threads
        
        with patch('os.cpu_count', return_value=1):
            threads = get_recommended_threads()
            assert threads >= 1