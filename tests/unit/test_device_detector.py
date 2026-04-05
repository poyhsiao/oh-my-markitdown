"""Unit tests for DeviceDetector."""
import pytest
from unittest.mock import patch

from api.device_detector import DeviceDetector


class TestDeviceDetectorDetect:
    @patch("api.device_detector._TORCH_AVAILABLE", True)
    @patch("api.device_detector.torch")
    def test_detect_cuda_when_available(self, mock_torch):
        mock_torch.cuda.is_available.return_value = True
        assert DeviceDetector.detect() == "cuda"

    @patch("api.device_detector._TORCH_AVAILABLE", True)
    @patch("api.device_detector.torch")
    def test_detect_cpu_when_cuda_not_available(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {}):
            with patch("api.device_detector.platform.system", return_value="Linux"):
                with patch("api.device_detector.platform.machine", return_value="x86_64"):
                    assert DeviceDetector.detect() == "cpu"

    @patch("api.device_detector._TORCH_AVAILABLE", True)
    @patch("api.device_detector.torch")
    def test_detect_mps_on_apple_silicon(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {}):
            with patch("api.device_detector.platform.system", return_value="Darwin"):
                with patch("api.device_detector.platform.machine", return_value="arm64"):
                    assert DeviceDetector.detect() == "mps"

    @patch("api.device_detector._TORCH_AVAILABLE", True)
    @patch("api.device_detector.torch")
    def test_detect_rocm_when_env_set(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {"ROCM_PATH": "/opt/rocm"}):
            with patch("api.device_detector.platform.system", return_value="Linux"):
                assert DeviceDetector.detect() == "rocm"


class TestDeviceDetectorBackend:
    def test_mps_returns_whisper_cpp_backend(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend

        assert DeviceDetector.get_backend_class("mps") == WhisperCppBackend

    def test_cuda_returns_faster_whisper_backend(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        assert DeviceDetector.get_backend_class("cuda") == FasterWhisperBackend

    def test_cpu_returns_faster_whisper_backend(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        assert DeviceDetector.get_backend_class("cpu") == FasterWhisperBackend

    def test_rocm_returns_faster_whisper_backend(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend

        assert DeviceDetector.get_backend_class("rocm") == FasterWhisperBackend

    def test_invalid_device_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported device"):
            DeviceDetector.get_backend_class("invalid")