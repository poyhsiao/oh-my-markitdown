"""Device detection for optimal backend selection."""
import os
import platform

try:
    import torch  # type: ignore[import-untyped]

    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False


class DeviceDetector:
    """Detect available compute devices and route to appropriate backends."""

    @staticmethod
    def detect() -> str:
        """Detect primary compute device. Priority: CUDA > ROCm > MPS > CPU."""
        if _TORCH_AVAILABLE and torch.cuda.is_available():  # type: ignore[union-attr]
            return "cuda"

        if os.environ.get("ROCM_PATH") or os.environ.get("HIP_VISIBLE_DEVICES"):
            return "rocm"

        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return "mps"

        return "cpu"

    @staticmethod
    def get_available_devices() -> list[str]:
        """Returns all available devices in priority order."""
        devices = []

        if _TORCH_AVAILABLE and torch.cuda.is_available():  # type: ignore[union-attr]
            devices.append("cuda")

        if os.environ.get("ROCM_PATH"):
            devices.append("rocm")

        if platform.system() == "Darwin" and platform.machine() == "arm64":
            devices.append("mps")

        devices.append("cpu")

        return devices

    @staticmethod
    def get_backend_class(device: str) -> type:
        """Get backend class for a device. mps->WhisperCppBackend, else->FasterWhisperBackend."""
        if device == "mps":
            from api.backends.whisper_cpp_backend import WhisperCppBackend

            return WhisperCppBackend
        elif device in ("cpu", "cuda", "rocm"):
            from api.backends.faster_whisper_backend import FasterWhisperBackend

            return FasterWhisperBackend
        else:
            raise ValueError(f"Unsupported device: {device}")