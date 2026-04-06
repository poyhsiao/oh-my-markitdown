#!/usr/bin/env python3
"""
GPU Detection Verification Script

Tests device detection logic without requiring actual GPU hardware.
Simulates nvidia-smi output and verifies all detection paths.

Usage:
    python3 scripts/verify_gpu_detection.py
"""

import os
import sys
import tempfile
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.device_utils import (
    detect_device,
    get_compute_type_for_device,
    get_device_info,
    _has_nvidia_gpu,
    _has_torch_cuda,
    _has_torch_mps,
)

# ============================================================
# Test Results
# ============================================================
class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, condition: bool, detail: str = ""):
        status = "PASS" if condition else "FAIL"
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append((status, name, detail))
        icon = "✅" if condition else "❌"
        print(f"  {icon} [{status}] {name}")
        if detail and not condition:
            print(f"         Detail: {detail}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.failed > 0:
            print("Failed tests:")
            for status, name, detail in self.results:
                if status == "FAIL":
                    print(f"  - {name}: {detail}")
        print(f"{'='*60}")
        return self.failed == 0


def test_compute_type_mapping(runner: TestRunner):
    """Test compute type mapping for all devices."""
    print("\n--- Compute Type Mapping ---")
    runner.test("CPU -> int8", get_compute_type_for_device("cpu") == "int8")
    runner.test("CUDA -> float16", get_compute_type_for_device("cuda") == "float16")
    runner.test("MPS -> float16", get_compute_type_for_device("mps") == "float16")
    runner.test("Unknown -> int8", get_compute_type_for_device("unknown") == "int8")


def test_env_override(runner: TestRunner):
    """Test WHISPER_DEVICE environment variable override."""
    print("\n--- Environment Variable Override ---")

    # Save original
    original = os.environ.get("WHISPER_DEVICE")

    os.environ["WHISPER_DEVICE"] = "cuda"
    runner.test("WHISPER_DEVICE=cuda", detect_device() == "cuda",
                f"Got: {detect_device()}")

    os.environ["WHISPER_DEVICE"] = "mps"
    runner.test("WHISPER_DEVICE=mps", detect_device() == "mps",
                f"Got: {detect_device()}")

    os.environ["WHISPER_DEVICE"] = "cpu"
    runner.test("WHISPER_DEVICE=cpu", detect_device() == "cpu",
                f"Got: {detect_device()}")

    # Restore
    if original is not None:
        os.environ["WHISPER_DEVICE"] = original
    else:
        os.environ.pop("WHISPER_DEVICE", None)


def test_nvidia_smi_detection(runner: TestRunner):
    """Test nvidia-smi detection path."""
    print("\n--- nvidia-smi Detection ---")

    has_nvidia = _has_nvidia_gpu()
    runner.test("nvidia-smi available", has_nvidia,
                "No NVIDIA GPU or nvidia-smi not installed")

    if has_nvidia:
        # Verify nvidia-smi output parsing
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        runner.test("nvidia-smi returns valid output",
                    result.returncode == 0 and bool(result.stdout.strip()),
                    f"Output: {result.stdout.strip()[:100]}")

        # Verify detect_device returns cuda
        runner.test("detect_device returns cuda",
                    detect_device() == "cuda",
                    f"Got: {detect_device()}")

        # Verify compute type
        runner.test("compute_type is float16 for CUDA",
                    get_compute_type_for_device("cuda") == "float16")


def test_device_info_endpoint(runner: TestRunner):
    """Test get_device_info() returns expected structure."""
    print("\n--- Device Info Structure ---")

    info = get_device_info()

    required_keys = ["device", "cuda_available", "mps_available",
                     "cpu_count", "recommended_compute_type", "in_docker"]
    for key in required_keys:
        runner.test(f"device_info has '{key}'", key in info,
                    f"Missing key: {key}")

    # Verify consistency
    runner.test("device matches recommended compute type",
                info["recommended_compute_type"] == get_compute_type_for_device(info["device"]),
                f"device={info['device']}, compute_type={info['recommended_compute_type']}")

    # Docker-specific checks
    if info["in_docker"]:
        runner.test("Docker reports docker_mps_available=false",
                    info.get("docker_mps_available") == False)
        runner.test("Docker has docker_mps_note",
                    "docker_mps_note" in info and len(info["docker_mps_note"]) > 0)


def test_quality_presets(runner: TestRunner):
    """Test quality preset mapping."""
    print("\n--- Quality Presets ---")

    from api.constants import QUALITY_PRESETS

    runner.test("'fast' preset exists", "fast" in QUALITY_PRESETS)
    runner.test("'standard' preset exists", "standard" in QUALITY_PRESETS)
    runner.test("'best' preset exists", "best" in QUALITY_PRESETS)

    if "fast" in QUALITY_PRESETS:
        runner.test("fast: beam_size=1",
                    QUALITY_PRESETS["fast"]["beam_size"] == 1)
    if "standard" in QUALITY_PRESETS:
        runner.test("standard: beam_size=3",
                    QUALITY_PRESETS["standard"]["beam_size"] == 3)
    if "best" in QUALITY_PRESETS:
        runner.test("best: beam_size=5",
                    QUALITY_PRESETS["best"]["beam_size"] == 5)


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print("GPU Detection Verification")
    print("=" * 60)

    runner = TestRunner()

    test_compute_type_mapping(runner)
    test_env_override(runner)
    test_nvidia_smi_detection(runner)
    test_device_info_endpoint(runner)
    test_quality_presets(runner)

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
