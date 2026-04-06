"""
Device detection and GPU configuration utilities.

Multi-layer detection: env override > nvidia-smi > torch > fallback CPU.
"""

import os
import shutil
import subprocess
import logging
from typing import Literal, Dict, Any, Optional

# Type definitions
DeviceType = Literal["cpu", "cuda", "mps", "auto"]

logger = logging.getLogger(__name__)

# Constants
MAX_CPU_THREADS = 8
MIN_CPU_THREADS = 1
DEFAULT_CPU_THREADS = 4


def _has_nvidia_gpu() -> bool:
    """Check for NVIDIA GPU via nvidia-smi (works in Docker with NVIDIA runtime)."""
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, Exception):
        return False


def _has_torch_cuda() -> bool:
    """Check for CUDA via PyTorch."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
    except Exception:
        return False


def _has_torch_mps() -> bool:
    """Check for Apple Silicon MPS via PyTorch."""
    try:
        import torch
        if hasattr(torch.backends, 'mps'):
            return torch.backends.mps.is_available() and torch.backends.mps.is_built()
        return False
    except ImportError:
        return False
    except Exception:
        return False


def detect_device() -> DeviceType:
    """
    Auto-detect optimal compute device.
    
    Detection order:
    1. WHISPER_DEVICE env var (explicit override)
    2. nvidia-smi (Docker NVIDIA runtime)
    3. torch.cuda (PyTorch CUDA)
    4. torch.mps (Apple Silicon)
    5. CPU fallback
    
    Returns:
        DeviceType: The detected device ("cuda", "mps", or "cpu")
    """
    # 1. Explicit env override
    env_device = os.getenv("WHISPER_DEVICE", "").lower()
    if env_device in ("cuda", "mps", "cpu"):
        logger.info("Device overridden by WHISPER_DEVICE env: %s", env_device)
        return env_device  # type: ignore[return-value]
    if env_device == "auto":
        pass  # Continue with auto-detection
    
    # 2. nvidia-smi (fastest, no torch dependency)
    if _has_nvidia_gpu():
        logger.info("NVIDIA GPU detected via nvidia-smi")
        return "cuda"
    
    # 3. torch.cuda
    if _has_torch_cuda():
        logger.info("CUDA device detected via PyTorch")
        return "cuda"
    
    # 4. torch.mps
    if _has_torch_mps():
        logger.info("MPS (Apple Silicon) device detected")
        return "mps"
    
    # 5. Fallback
    logger.info("No GPU detected, using CPU")
    return "cpu"


def get_compute_type_for_device(device: str) -> str:
    """
    Get recommended compute type for a device.
    
    Args:
        device: Device type (cpu, cuda, mps)
        
    Returns:
        str: Recommended compute type (int8, float16, or float32)
    """
    compute_type_map = {
        "cpu": "int8",       # CPU uses int8 quantization for efficiency
        "cuda": "float16",   # NVIDIA GPU uses float16 for speed
        "mps": "float16",    # Apple Silicon uses float16
    }
    return compute_type_map.get(device, "int8")


def _is_running_in_docker() -> bool:
    """Detect if running inside a Docker container."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def get_device_info() -> Dict[str, Any]:
    """
    Get detailed information about available compute devices.
    """
    in_docker = _is_running_in_docker()
    info: Dict[str, Any] = {
        "device": "cpu",
        "cuda_available": False,
        "mps_available": False,
        "cpu_count": os.cpu_count() or 4,
        "recommended_compute_type": "int8",
        "in_docker": in_docker,
    }
    
    # Check CUDA via nvidia-smi (no torch needed)
    if shutil.which("nvidia-smi") is not None:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                gpus = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                info["cuda_available"] = True
                info["cuda_device_count"] = len(gpus)
                # Parse first GPU name and memory
                parts = gpus[0].split(',')
                info["cuda_device_name"] = parts[0].strip()
                if len(parts) > 1:
                    info["cuda_memory_gb"] = round(float(parts[1].strip().replace(' MiB', '')) / 1024, 2)
        except (subprocess.TimeoutExpired, ValueError, IndexError, Exception) as e:
            logger.debug("nvidia-smi info retrieval failed: %s", e)
    
    # Check CUDA via torch (if available)
    if not info["cuda_available"]:
        try:
            import torch
            if torch.cuda.is_available():
                info["cuda_available"] = True
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
                info["cuda_device_count"] = torch.cuda.device_count()
                info["cuda_memory_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
                )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("CUDA info retrieval failed: %s", e)
    
    # Check MPS
    try:
        import torch
        if hasattr(torch.backends, 'mps'):
            if torch.backends.mps.is_available():
                info["mps_available"] = True
                info["mps_built"] = torch.backends.mps.is_built()
    except ImportError:
        pass
    except Exception as e:
        logger.debug("MPS info retrieval failed: %s", e)
    
    # Set detected device
    info["device"] = detect_device()
    info["recommended_compute_type"] = get_compute_type_for_device(info["device"])
    
    # Docker limitation warnings
    if in_docker:
        info["docker_mps_available"] = False
        info["docker_mps_note"] = "MPS is not available in Docker containers. Use native execution on macOS for Apple Silicon GPU acceleration."
    
    return info


def validate_device(device: str) -> str:
    """
    Validate and return effective device.
    
    Args:
        device: Requested device ("cpu", "cuda", "mps", or "auto")
        
    Returns:
        str: Validated device
        
    Raises:
        ValueError: If requested device is not available
    """
    if device == "auto":
        return detect_device()
    
    if device == "cpu":
        return "cpu"
    
    if device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                raise ValueError(
                    "CUDA requested but not available. "
                    "Please ensure NVIDIA GPU and CUDA toolkit are installed."
                )
        except ImportError:
            raise ValueError(
                "CUDA requested but PyTorch not installed. "
                "Please install PyTorch with CUDA support."
            )
        return "cuda"
    
    if device == "mps":
        try:
            import torch
            if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
                raise ValueError(
                    "MPS requested but not available. "
                    "MPS is only available on Apple Silicon Macs (M1/M2/M3)."
                )
        except ImportError:
            raise ValueError(
                "MPS requested but PyTorch not installed. "
                "Please install PyTorch for macOS."
            )
        return "mps"
    
    raise ValueError(
        f"Invalid device '{device}'. Must be 'cpu', 'cuda', 'mps', or 'auto'."
    )


def get_recommended_threads(cpu_threads: int = 0) -> int:
    """
    Get recommended CPU thread count.
    
    Args:
        cpu_threads: Requested thread count (0 = auto detect)
        
    Returns:
        int: Effective thread count (1-8)
    """
    if cpu_threads > 0:
        return min(cpu_threads, MAX_CPU_THREADS)
    
    # Auto-detect
    cpu_count = os.cpu_count() or DEFAULT_CPU_THREADS
    return min(cpu_count, MAX_CPU_THREADS)


def get_recommended_batch_size(device: str, model_size: str) -> int:
    """
    Get recommended batch size for a device and model.
    
    Args:
        device: Device type (cpu, cuda, mps)
        model_size: Whisper model size (tiny, base, small, medium, large)
        
    Returns:
        int: Recommended batch size
    """
    batch_size_map = {
        "cuda": {
            "tiny": 32,
            "base": 16,
            "small": 8,
            "medium": 4,
            "large": 2
        },
        "mps": {
            "tiny": 16,
            "base": 8,
            "small": 4,
            "medium": 2,
            "large": 1
        },
        "cpu": {
            "tiny": 8,
            "base": 4,
            "small": 2,
            "medium": 1,
            "large": 1
        }
    }
    
    return batch_size_map.get(device, {}).get(model_size, 1)


def configure_mps_memory_limit(limit_gb: int = 8) -> None:
    """
    Configure MPS memory limit for Apple Silicon.
    
    MPS uses unified memory, so we need to be conservative.
    
    Args:
        limit_gb: Memory limit in GB (default 8GB)
    """
    if limit_gb <= 0:
        return
    
    # PyTorch MPS doesn't have direct memory limit API,
    # but we can set environment variable
    os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
    logger.info(f"MPS memory limit set to {limit_gb}GB")


def is_gpu_available() -> bool:
    """
    Check if any GPU is available.
    
    Returns:
        bool: True if CUDA or MPS is available
    """
    device = detect_device()
    return device in ("cuda", "mps")


def get_device_memory_info(device: str) -> Optional[Dict[str, Any]]:
    """
    Get memory information for a device.
    
    Args:
        device: Device type (cuda or mps)
        
    Returns:
        dict: Memory info or None if not available
    """
    if device == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                total = props.total_memory
                allocated = torch.cuda.memory_allocated(0)
                reserved = torch.cuda.memory_reserved(0)
                
                return {
                    "total_gb": round(total / (1024**3), 2),
                    "allocated_gb": round(allocated / (1024**3), 2),
                    "reserved_gb": round(reserved / (1024**3), 2),
                    "free_gb": round((total - reserved) / (1024**3), 2)
                }
        except Exception as e:
            logger.debug(f"CUDA memory info retrieval failed: {e}")
    
    elif device == "mps":
        # MPS uses unified memory, no direct query available
        return {
            "type": "unified",
            "note": "MPS uses unified memory shared with system"
        }
    
    return None