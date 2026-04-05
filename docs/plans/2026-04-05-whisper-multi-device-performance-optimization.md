# Whisper Multi-Device Performance Optimization — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize Whisper transcription pipeline with multi-device backend abstraction (faster-whisper for CUDA/ROCm/CPU, whispercpp for Apple Silicon), parallel chunking, BatchedInferencePipeline, and GPU deployment — all TDD-driven with full test coverage.

**Architecture:** Backend abstraction layer with TranscriptionBackend Protocol, DeviceDetector for hardware auto-detection, TranscriptionStrategy for auto-configuration, ChunkingEngine with parallel processing, and quality mode presets exposed via API.

**Tech Stack:** Python 3.12, FastAPI, faster-whisper >= 1.2.0, whispercpp >= 2.0.0, pytest, httpx, Docker, CUDA/ROCm/MPS

---

## Phase 1: Foundation — Constants, Presets, API Parameters

**Goal:** Update defaults, add quality_mode presets, expose new API parameters, write tests first.

---

### Task 1: Update constants.py defaults and add presets

**Files:**
- Modify: `api/constants.py:80-118`
- Test: `tests/unit/test_constants.py` (new)

**Step 1: Write the failing test**

Create `tests/unit/test_constants.py`:

```python
"""Unit tests for constants updates."""
import pytest
from api.constants import (
    DEFAULT_CPU_THREADS,
    DEFAULT_VAD_MIN_SILENCE_MS,
    DEFAULT_VAD_THRESHOLD,
    DEFAULT_VAD_SPEECH_PAD_MS,
    QUALITY_PRESETS,
    DEFAULT_CHUNK_BEAM_SIZE,
    DEFAULT_CHUNK_TEMPERATURE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LENGTH_S,
    DEFAULT_MAX_WORKERS,
)


class TestConstantsUpdates:
    """Test updated default values."""

    def test_cpu_threads_default_is_8(self):
        assert DEFAULT_CPU_THREADS == 8

    def test_vad_min_silence_ms_is_500(self):
        assert DEFAULT_VAD_MIN_SILENCE_MS == 500

    def test_vad_threshold_is_0_5(self):
        assert DEFAULT_VAD_THRESHOLD == 0.5

    def test_vad_speech_pad_ms_is_300(self):
        assert DEFAULT_VAD_SPEECH_PAD_MS == 300


class TestQualityPresets:
    """Test quality mode presets."""

    def test_speed_preset(self):
        assert QUALITY_PRESETS["speed"] == {"beam_size": 1, "temperature": 0.0}

    def test_balanced_preset(self):
        assert QUALITY_PRESETS["balanced"] == {"beam_size": 3, "temperature": 0.0}

    def test_quality_preset(self):
        assert QUALITY_PRESETS["quality"] == {"beam_size": 5, "temperature": 0.0}

    def test_all_presets_have_required_keys(self):
        for preset in QUALITY_PRESETS.values():
            assert "beam_size" in preset
            assert "temperature" in preset


class TestNewConstants:
    """Test new constants."""

    def test_default_chunk_beam_size(self):
        assert DEFAULT_CHUNK_BEAM_SIZE == 1

    def test_default_chunk_temperature(self):
        assert DEFAULT_CHUNK_TEMPERATURE == 0.0

    def test_default_batch_size(self):
        assert DEFAULT_BATCH_SIZE == 8

    def test_default_chunk_length_s(self):
        assert DEFAULT_CHUNK_LENGTH_S == 30

    def test_default_max_workers(self):
        assert DEFAULT_MAX_WORKERS == 4
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_constants.py -v
```
Expected: FAIL with ImportError (QUALITY_PRESETS, DEFAULT_CHUNK_BEAM_SIZE, etc. not defined)

**Step 3: Update constants.py**

Modify `api/constants.py` — update VAD params at lines 81-83, CPU threads at line 94, add new constants at end of file:

```python
# ===== VAD Parameters =====
DEFAULT_VAD_MIN_SILENCE_MS = 500    # 300 -> 500 (more aggressive silence detection)
DEFAULT_VAD_THRESHOLD = 0.5         # 0.6 -> 0.5 (lower threshold catches more speech)
DEFAULT_VAD_SPEECH_PAD_MS = 300     # 200 -> 300 (longer padding)

# ===== CPU Threading =====
MAX_CPU_THREADS = 8
MIN_CPU_THREADS = 1
DEFAULT_CPU_THREADS = 8             # 4 -> 8 (utilize more cores)

# ===== Quality Mode Presets =====
QUALITY_PRESETS = {
    "speed": {"beam_size": 1, "temperature": 0.0},
    "balanced": {"beam_size": 3, "temperature": 0.0},
    "quality": {"beam_size": 5, "temperature": 0.0},
}

# ===== Chunking Defaults =====
DEFAULT_CHUNK_BEAM_SIZE = 1         # 5 -> 1 (greedy decoding for speed)
DEFAULT_CHUNK_TEMPERATURE = 0.0

# ===== Batched Inference =====
DEFAULT_BATCH_SIZE = 8
DEFAULT_CHUNK_LENGTH_S = 30

# ===== Parallel Chunking =====
DEFAULT_MAX_WORKERS = 4
MIN_MAX_WORKERS = 1
MAX_MAX_WORKERS = 8
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_constants.py -v
```
Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add api/constants.py tests/unit/test_constants.py
git commit -m "feat(whisper): update constants for performance optimization

- CPU threads: 4 -> 8
- VAD params: more aggressive filtering
- Add QUALITY_PRESETS (speed/balanced/quality)
- Add batched inference and parallel chunking constants
- Default chunk beam_size: 5 -> 1"
```

---

### Task 2: Add new API parameters to /convert/audio endpoint

**Files:**
- Modify: `api/main.py` — find `transcribe_audio_file` function
- Test: `tests/unit/test_api_params.py` (new)

**Step 1: Find the audio endpoint**

```bash
grep -n "transcribe_audio_file" api/main.py
```

**Step 2: Write the failing test**

Create `tests/unit/test_api_params.py`:

```python
"""Unit tests for API parameter validation."""
import pytest
from api.constants import QUALITY_PRESETS


class TestQualityPresets:
    """Test quality preset resolution."""

    def test_speed_preset_beam_size(self):
        assert QUALITY_PRESETS["speed"]["beam_size"] == 1

    def test_balanced_preset_beam_size(self):
        assert QUALITY_PRESETS["balanced"]["beam_size"] == 3

    def test_quality_preset_beam_size(self):
        assert QUALITY_PRESETS["quality"]["beam_size"] == 5

    def test_invalid_quality_mode(self):
        with pytest.raises(KeyError):
            _ = QUALITY_PRESETS["invalid"]

    def test_preset_temperature_is_zero(self):
        for preset in QUALITY_PRESETS.values():
            assert preset["temperature"] == 0.0


class TestApiParameterDefaults:
    """Test API parameter default values."""

    def test_default_quality_mode_is_balanced(self):
        default_quality = "balanced"
        assert default_quality in QUALITY_PRESETS

    def test_default_device_is_auto(self):
        default_device = "auto"
        assert default_device in ("auto", "cpu", "cuda", "mps", "rocm")

    def test_default_batch_size(self):
        from api.constants import DEFAULT_BATCH_SIZE
        assert DEFAULT_BATCH_SIZE == 8

    def test_valid_quality_modes(self):
        expected = {"speed", "balanced", "quality"}
        assert set(QUALITY_PRESETS.keys()) == expected
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_api_params.py -v
```
Expected: FAIL (QUALITY_PRESETS not yet importable from constants if Task 1 not done)

**Step 4: Run test to verify it passes** (after Task 1 is complete)

```bash
pytest tests/unit/test_api_params.py -v
```
Expected: All tests PASS

**Step 5: Add new parameters to /convert/audio endpoint**

Read `api/main.py` to find the exact function signature for `transcribe_audio_file`. Then update it:

```python
@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = Query("zh"),
    model_size: str = Query("auto"),
    return_format: str = Query("markdown"),
    include_timestamps: bool = Query(False),
    # New optimization parameters
    quality_mode: str = Query("balanced", description="Quality preset: speed, balanced, quality"),
    beam_size: int = Query(None, description="Beam search size (1=speed, 5=quality). Overrides quality_mode."),
    temperature: float = Query(None, description="Sampling temperature (0.0=greedy). Overrides quality_mode."),
    use_batched: bool = Query(None, description="Use BatchedInferencePipeline (auto-detect if None)"),
    batch_size: int = Query(8, description="Batch size for batched inference"),
    device: str = Query("auto", description="Compute device: auto, cpu, cuda, mps, rocm"),
    cpu_threads: int = Query(None, description="CPU thread count (auto-detect if None)"),
):
```

**Step 6: Commit**

```bash
git add api/main.py tests/unit/test_api_params.py
git commit -m "feat(whisper): add optimization parameters to audio endpoint

- Add quality_mode, beam_size, temperature, use_batched, batch_size, device, cpu_threads
- Default model_size changed to 'auto' for automatic model selection
- All new params are optional with backward-compatible defaults"
```

---

### Task 3: Add new API parameters to /convert/video endpoint

**Files:**
- Modify: `api/main.py` — find `transcribe_video_file` function
- Test: Covered by Task 2 tests + manual verification

**Step 1: Find the video endpoint**

```bash
grep -n "transcribe_video_file" api/main.py
```

**Step 2: Add same parameters as audio endpoint**

Read the function, add the same 7 new parameters with identical defaults.

**Step 3: Verify no lint errors**

```bash
python -m py_compile api/main.py
```

**Step 4: Commit**

```bash
git add api/main.py
git commit -m "feat(whisper): add optimization parameters to video endpoint"
```

---

### Task 4: Add new API parameters to /convert/youtube endpoint

**Files:**
- Modify: `api/main.py` — find `transcribe_youtube` function
- Test: Covered by existing tests

**Step 1: Find the youtube endpoint**

```bash
grep -n "transcribe_youtube" api/main.py
```

**Step 2: Add same parameters**

Read the function, add the same 7 new parameters.

**Step 3: Verify no lint errors**

```bash
python -m py_compile api/main.py
```

**Step 4: Run all unit tests**

```bash
pytest tests/unit/ -v --tb=short
```
Expected: All PASS

**Step 5: Commit**

```bash
git add api/main.py
git commit -m "feat(whisper): add optimization parameters to youtube endpoint

Phase 1 complete — all 3 endpoints updated with optimization parameters"
```

---

### Phase 1 Verification

```bash
# Run all unit tests
pytest tests/unit/test_constants.py tests/unit/test_api_params.py -v

# Verify API still starts
docker compose up -d && curl http://localhost:51083/health
```

**Phase 1 deliverables:**
- ✅ Updated constants (CPU threads, VAD, presets)
- ✅ New API params on all 3 endpoints
- ✅ Unit tests for constants and params
- ✅ Backward compatible (existing calls work)

---

## Phase 2: Backend Abstraction Layer

**Goal:** Create TranscriptionBackend Protocol, FasterWhisperBackend, WhisperCppBackend, DeviceDetector, TranscriptionStrategy.

---

### Task 5: Create backends package and Protocol

**Files:**
- Create: `api/backends/__init__.py`
- Create: `api/backends/protocol.py`
- Test: `tests/unit/test_backend_protocol.py` (new)

**Step 1: Create the backends package**

```bash
mkdir -p api/backends
```

**Step 2: Write the test first**

Create `tests/unit/test_backend_protocol.py`:

```python
"""Unit tests for TranscriptionBackend Protocol."""
import pytest
from typing import Protocol, runtime_checkable
from api.backends.protocol import TranscriptionBackend


class TestTranscriptionBackendProtocol:
    """Test the Protocol definition."""

    def test_protocol_has_required_attributes(self):
        """Protocol defines name, device, supported_compute_types, supports_batched."""
        assert hasattr(TranscriptionBackend, '__annotations__')
        annotations = TranscriptionBackend.__annotations__
        assert "name" in annotations
        assert "device" in annotations
        assert "supported_compute_types" in annotations
        assert "supports_batched" in annotations

    def test_protocol_has_required_methods(self):
        """Protocol defines load_model, transcribe, transcribe_batched, unload."""
        assert hasattr(TranscriptionBackend, "load_model")
        assert hasattr(TranscriptionBackend, "transcribe")
        assert hasattr(TranscriptionBackend, "transcribe_batched")
        assert hasattr(TranscriptionBackend, "unload")
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_backend_protocol.py -v
```
Expected: FAIL (module not found)

**Step 4: Create the Protocol**

Create `api/backends/protocol.py`:

```python
"""Transcription Backend Protocol — unified interface for all backends."""
from typing import Protocol, Iterator, runtime_checkable


@runtime_checkable
class TranscriptionBackend(Protocol):
    """Unified interface for all transcription backends.
    
    Implementations:
    - FasterWhisperBackend: CPU, CUDA, ROCm (supports BatchedInferencePipeline)
    - WhisperCppBackend: MPS/Apple Silicon (manual parallel chunking)
    """

    name: str  # "faster-whisper" | "whisper-cpp"
    device: str  # "cpu" | "cuda" | "rocm" | "mps"
    supported_compute_types: list[str]
    supports_batched: bool

    def load_model(
        self,
        model_size: str,
        compute_type: str,
        **kwargs,
    ) -> None:
        """Load or retrieve model from cache."""
        ...

    def transcribe(
        self,
        audio_path: str,
        language: str | None,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        """Transcribe audio file."""
        ...

    def transcribe_batched(
        self,
        audio_path: str,
        language: str | None,
        batch_size: int = 8,
        chunk_length_s: int = 30,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        """Transcribe using BatchedInferencePipeline (GPU only)."""
        ...

    def unload(self) -> None:
        """Unload model from memory."""
        ...
```

Create `api/backends/__init__.py`:

```python
"""Transcription backends package."""
from api.backends.protocol import TranscriptionBackend

__all__ = ["TranscriptionBackend"]
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_backend_protocol.py -v
```
Expected: All PASS

**Step 6: Commit**

```bash
git add api/backends/__init__.py api/backends/protocol.py tests/unit/test_backend_protocol.py
git commit -m "feat(whisper): add TranscriptionBackend Protocol

- Protocol defines unified interface for all backends
- Methods: load_model, transcribe, transcribe_batched, unload
- Attributes: name, device, supported_compute_types, supports_batched"
```

---

### Task 6: Create DeviceDetector

**Files:**
- Create: `api/device_detector.py`
- Test: `tests/unit/test_device_detector.py` (new)

**Step 1: Write the failing test**

Create `tests/unit/test_device_detector.py`:

```python
"""Unit tests for DeviceDetector."""
import pytest
from unittest.mock import patch, MagicMock
from api.device_detector import DeviceDetector


class TestDeviceDetectorDetect:
    """Test DeviceDetector.detect()."""

    @patch("api.device_detector.torch")
    def test_detect_cuda_when_available(self, mock_torch):
        mock_torch.cuda.is_available.return_value = True
        assert DeviceDetector.detect() == "cuda"

    @patch("api.device_detector.torch")
    def test_detect_cpu_when_cuda_not_available(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {}):
            with patch("api.device_detector.platform.system", return_value="Linux"):
                with patch("api.device_detector.platform.machine", return_value="x86_64"):
                    assert DeviceDetector.detect() == "cpu"

    @patch("api.device_detector.torch")
    def test_detect_mps_on_apple_silicon(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {}):
            with patch("api.device_detector.platform.system", return_value="Darwin"):
                with patch("api.device_detector.platform.machine", return_value="arm64"):
                    assert DeviceDetector.detect() == "mps"

    @patch("api.device_detector.torch")
    def test_detect_rocm_when_env_set(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        with patch("api.device_detector.os.environ", {"ROCM_PATH": "/opt/rocm"}):
            with patch("api.device_detector.platform.system", return_value="Linux"):
                assert DeviceDetector.detect() == "rocm"


class TestDeviceDetectorBackend:
    """Test DeviceDetector.get_backend_class()."""

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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_device_detector.py -v
```
Expected: FAIL (module not found)

**Step 3: Create DeviceDetector**

Create `api/device_detector.py`:

```python
"""Device detection for optimal backend selection."""
import os
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.backends.faster_whisper_backend import FasterWhisperBackend
    from api.backends.whisper_cpp_backend import WhisperCppBackend


class DeviceDetector:
    """Detect available compute devices and route to appropriate backends."""

    @staticmethod
    def detect() -> str:
        """Detect primary compute device.
        
        Priority: CUDA > ROCm > MPS > CPU
        Returns: 'cuda' | 'rocm' | 'mps' | 'cpu'
        """
        # Check CUDA
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        # Check ROCm
        if os.environ.get("ROCM_PATH") or os.environ.get("HIP_VISIBLE_DEVICES"):
            return "rocm"

        # Check Apple Silicon
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return "mps"

        return "cpu"

    @staticmethod
    def get_available_devices() -> list[str]:
        """Returns all available devices in priority order."""
        devices = []
        try:
            import torch
            if torch.cuda.is_available():
                devices.append("cuda")
        except ImportError:
            pass

        if os.environ.get("ROCM_PATH"):
            devices.append("rocm")

        if platform.system() == "Darwin" and platform.machine() == "arm64":
            devices.append("mps")

        devices.append("cpu")
        return devices

    @staticmethod
    def get_backend_class(device: str) -> type:
        """Get backend class for a device.
        
        mps -> WhisperCppBackend
        else -> FasterWhisperBackend
        """
        if device == "mps":
            from api.backends.whisper_cpp_backend import WhisperCppBackend
            return WhisperCppBackend
        elif device in ("cpu", "cuda", "rocm"):
            from api.backends.faster_whisper_backend import FasterWhisperBackend
            return FasterWhisperBackend
        else:
            raise ValueError(f"Unsupported device: {device}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_device_detector.py -v
```
Expected: FAIL (backend classes don't exist yet — that's OK, we'll create them next)

For now, skip the backend class tests and test only detect():

```bash
pytest tests/unit/test_device_detector.py::TestDeviceDetectorDetect -v
```

**Step 5: Commit**

```bash
git add api/device_detector.py tests/unit/test_device_detector.py
git commit -m "feat(whisper): add DeviceDetector for hardware auto-detection

- Detects CUDA, ROCm, MPS, CPU in priority order
- Routes mps to WhisperCppBackend, others to FasterWhisperBackend
- get_available_devices() returns all detected devices"
```

---

### Task 7: Create FasterWhisperBackend

**Files:**
- Create: `api/backends/faster_whisper_backend.py`
- Test: `tests/unit/test_faster_whisper_backend.py` (new)

**Step 1: Query context7 for faster-whisper API**

```
Query: faster-whisper WhisperModel transcribe BatchedInferencePipeline API usage
```

**Step 2: Write the failing test**

Create `tests/unit/test_faster_whisper_backend.py`:

```python
"""Unit tests for FasterWhisperBackend."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestFasterWhisperBackendInit:
    """Test FasterWhisperBackend initialization."""

    def test_default_device_is_cpu(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        backend = FasterWhisperBackend()
        assert backend.device == "cpu"
        assert backend.name == "faster-whisper"
        assert backend.supports_batched is True

    def test_cpu_supported_compute_types(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        backend = FasterWhisperBackend(device="cpu")
        assert "int8" in backend.supported_compute_types

    def test_cuda_supported_compute_types(self):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        backend = FasterWhisperBackend(device="cuda")
        assert "float16" in backend.supported_compute_types
        assert "int8" in backend.supported_compute_types


class TestFasterWhisperBackendLoadModel:
    """Test model loading."""

    @patch("api.backends.faster_whisper_backend.WhisperModel")
    def test_load_model_creates_instance(self, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model

        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")

        mock_whisper_model.assert_called_once()
        assert backend._base_model is not None

    @patch("api.backends.faster_whisper_backend.WhisperModel")
    @patch("api.backends.faster_whisper_backend.BatchedInferencePipeline")
    def test_load_model_with_batched(self, mock_batched, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        mock_base = MagicMock()
        mock_batched_pipeline = MagicMock()
        mock_whisper_model.return_value = mock_base
        mock_batched.return_value = mock_batched_pipeline

        backend = FasterWhisperBackend(device="cuda")
        backend.load_model("base", "float16", use_batched=True)

        mock_whisper_model.assert_called_once()
        mock_batched.assert_called_once()
        assert backend._batched_model is not None


class TestFasterWhisperBackendTranscribe:
    """Test transcription."""

    @patch("api.backends.faster_whisper_backend.WhisperModel")
    def test_transcribe_calls_model_transcribe(self, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), {"language": "en"})
        mock_whisper_model.return_value = mock_model

        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")
        segments, info = backend.transcribe("/tmp/test.wav", "en")

        mock_model.transcribe.assert_called_once()


class TestFasterWhisperBackendUnload:
    """Test model unloading."""

    @patch("api.backends.faster_whisper_backend.WhisperModel")
    def test_unload_clears_models(self, mock_whisper_model):
        from api.backends.faster_whisper_backend import FasterWhisperBackend
        mock_model = MagicMock()
        mock_whisper_model.return_value = mock_model

        backend = FasterWhisperBackend()
        backend.load_model("base", "int8")
        backend.unload()

        assert backend._base_model is None
        assert backend._batched_model is None
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_faster_whisper_backend.py -v
```
Expected: FAIL (module not found)

**Step 4: Create FasterWhisperBackend**

Create `api/backends/faster_whisper_backend.py`:

```python
"""Faster-Whisper backend implementation.

Supports CPU, CUDA, and ROCm devices.
Uses BatchedInferencePipeline for GPU devices when enabled.
"""
from typing import Iterator

from faster_whisper import WhisperModel
from faster_whisper import BatchedInferencePipeline

from api.backends.protocol import TranscriptionBackend
from api.whisper_transcribe import _model_cache, ModelCache


class FasterWhisperBackend(TranscriptionBackend):
    """Faster-Whisper backend for CPU, CUDA, and ROCm."""

    def __init__(
        self,
        device: str = "cpu",
        model_cache: ModelCache | None = None,
    ):
        self.name = "faster-whisper"
        self.device = device
        self.supported_compute_types = self._get_supported_compute_types()
        self.supports_batched = True
        self._model_cache = model_cache or _model_cache
        self._base_model: WhisperModel | None = None
        self._batched_model: BatchedInferencePipeline | None = None

    def _get_supported_compute_types(self) -> list[str]:
        if self.device == "cpu":
            return ["int8", "float32"]
        return ["float16", "int8", "int8_float16"]

    def load_model(
        self,
        model_size: str,
        compute_type: str,
        cpu_threads: int = 4,
        use_batched: bool = False,
        **kwargs,
    ) -> None:
        cache_key = f"{model_size}_{self.device}_{compute_type}_{cpu_threads}_{'batched' if use_batched else 'standard'}"

        cached = self._model_cache.get(cache_key)
        if cached is not None:
            if use_batched:
                self._batched_model = cached
            else:
                self._base_model = cached
            return

        base_model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )

        if use_batched:
            batched_model = BatchedInferencePipeline(model=base_model)
            self._batched_model = batched_model
            self._model_cache.set(cache_key, batched_model)
        else:
            self._base_model = base_model
            self._model_cache.set(cache_key, base_model)

    def transcribe(
        self,
        audio_path: str,
        language: str | None,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        if self._base_model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        segments, info = self._base_model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            vad_parameters=vad_params if vad_filter else None,
            word_timestamps=word_timestamps,
        )
        return segments, info

    def transcribe_batched(
        self,
        audio_path: str,
        language: str | None,
        batch_size: int = 8,
        chunk_length_s: int = 30,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        if self._batched_model is None:
            raise RuntimeError("Batched model not loaded. Call load_model(use_batched=True) first.")

        segments, info = self._batched_model.transcribe(
            audio_path,
            language=language,
            batch_size=batch_size,
            chunk_length_s=chunk_length_s,
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            vad_parameters=vad_params if vad_filter else None,
            word_timestamps=word_timestamps,
        )
        return segments, info

    def unload(self) -> None:
        self._base_model = None
        self._batched_model = None
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_faster_whisper_backend.py -v
```
Expected: All PASS

**Step 6: Commit**

```bash
git add api/backends/faster_whisper_backend.py tests/unit/test_faster_whisper_backend.py
git commit -m "feat(whisper): add FasterWhisperBackend for CPU/CUDA/ROCm

- Supports standard and BatchedInferencePipeline modes
- Model caching with LRU eviction
- Device-specific compute type validation"
```

---

### Task 8: Create WhisperCppBackend

**Files:**
- Create: `api/backends/whisper_cpp_backend.py`
- Test: `tests/unit/test_whisper_cpp_backend.py` (new)

**Step 1: Write the failing test**

Create `tests/unit/test_whisper_cpp_backend.py`:

```python
"""Unit tests for WhisperCppBackend."""
import pytest
from unittest.mock import MagicMock, patch


class TestWhisperCppBackendInit:
    """Test WhisperCppBackend initialization."""

    def test_default_device_is_mps(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend
        backend = WhisperCppBackend()
        assert backend.device == "mps"
        assert backend.name == "whisper-cpp"
        assert backend.supports_batched is False

    def test_supported_compute_types(self):
        from api.backends.whisper_cpp_backend import WhisperCppBackend
        backend = WhisperCppBackend()
        assert "float16" in backend.supported_compute_types
        assert "int8" in backend.supported_compute_types


class TestWhisperCppBackendLoadModel:
    """Test model loading."""

    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_load_model_creates_instance(self, mock_whisper):
        from api.backends.whisper_cpp_backend import WhisperCppBackend
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model

        backend = WhisperCppBackend()
        backend.load_model("base", "int8")

        mock_whisper.assert_called_once()
        assert backend._model is not None


class TestWhisperCppBackendTranscribe:
    """Test transcription."""

    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_transcribe_calls_model_transcribe(self, mock_whisper):
        from api.backends.whisper_cpp_backend import WhisperCppBackend
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test transcript"}
        mock_whisper.return_value = mock_model

        backend = WhisperCppBackend()
        backend.load_model("base", "int8")
        result = backend.transcribe("/tmp/test.wav", "en")

        mock_model.transcribe.assert_called_once()


class TestWhisperCppBackendUnload:
    """Test model unloading."""

    @patch("api.backends.whisper_cpp_backend.Whisper")
    def test_unload_clears_model(self, mock_whisper):
        from api.backends.whisper_cpp_backend import WhisperCppBackend
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model

        backend = WhisperCppBackend()
        backend.load_model("base", "int8")
        backend.unload()

        assert backend._model is None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_whisper_cpp_backend.py -v
```
Expected: FAIL (module not found)

**Step 3: Create WhisperCppBackend**

Create `api/backends/whisper_cpp_backend.py`:

```python
"""Whisper.cpp backend implementation for Apple Silicon (MPS).

Uses whispercpp.py Python bindings for Metal/CoreML acceleration.
Does not support BatchedInferencePipeline — use parallel chunking instead.
"""
from typing import Iterator

try:
    from whispercpp import Whisper
except ImportError:
    Whisper = None

from api.backends.protocol import TranscriptionBackend
from api.whisper_transcribe import _model_cache, ModelCache


class WhisperCppBackend(TranscriptionBackend):
    """Whisper.cpp backend for Apple Silicon (MPS)."""

    def __init__(
        self,
        device: str = "mps",
        model_cache: ModelCache | None = None,
    ):
        self.name = "whisper-cpp"
        self.device = device
        self.supported_compute_types = ["float16", "int8"]
        self.supports_batched = False
        self._model_cache = model_cache or _model_cache
        self._model = None

    def load_model(
        self,
        model_size: str,
        compute_type: str = "int8",
        **kwargs,
    ) -> None:
        if Whisper is None:
            raise ImportError(
                "whispercpp is not installed. Install with: pip install whispercpp>=2.0.0"
            )

        cache_key = f"whispercpp_{model_size}_{compute_type}"

        cached = self._model_cache.get(cache_key)
        if cached is not None:
            self._model = cached
            return

        # whispercpp uses model name like 'base', 'small', etc.
        self._model = Whisper(model_size)
        self._model_cache.set(cache_key, self._model)

    def transcribe(
        self,
        audio_path: str,
        language: str | None,
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # whispercpp API differs from faster-whisper
        # Returns dict with 'text' key and segments
        result = self._model.transcribe(audio_path)

        # Normalize to faster-whisper format: (segments_iter, info_dict)
        segments = iter(result.get("segments", []))
        info = {
            "language": language or "auto",
            "language_probability": 1.0,
            "duration": result.get("duration", 0),
        }
        return segments, info

    def transcribe_batched(
        self,
        audio_path: str,
        language: str | None,
        **kwargs,
    ) -> tuple[Iterator, dict]:
        raise NotImplementedError(
            "WhisperCppBackend does not support batched inference. "
            "Use parallel chunking via ThreadPoolExecutor instead."
        )

    def unload(self) -> None:
        self._model = None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_whisper_cpp_backend.py -v
```
Expected: All PASS (mocked Whisper)

**Step 5: Commit**

```bash
git add api/backends/whisper_cpp_backend.py tests/unit/test_whisper_cpp_backend.py
git commit -m "feat(whisper): add WhisperCppBackend for Apple Silicon

- Uses whispercpp.py bindings for Metal/CoreML acceleration
- Does not support BatchedInferencePipeline (manual parallel chunking)
- Model caching with LRU eviction"
```

---

### Task 9: Create TranscriptionStrategy

**Files:**
- Create: `api/transcription_strategy.py`
- Test: `tests/unit/test_transcription_strategy.py` (new)

**Step 1: Write the failing test**

Create `tests/unit/test_transcription_strategy.py`:

```python
"""Unit tests for TranscriptionStrategy."""
import pytest
from api.transcription_strategy import TranscriptionStrategy
from api.constants import QUALITY_PRESETS


class TestTranscriptionStrategyAutoConfigure:
    """Test TranscriptionStrategy.auto_configure()."""

    def test_cuda_speed_mode(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=300,
            quality_mode="speed",
        )
        assert strategy.backend == "faster-whisper"
        assert strategy.device == "cuda"
        assert strategy.compute_type == "float16"
        assert strategy.use_batched is True
        assert strategy.beam_size == 1

    def test_cuda_balanced_mode(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=300,
            quality_mode="balanced",
        )
        assert strategy.beam_size == 3

    def test_cuda_quality_mode(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=300,
            quality_mode="quality",
        )
        assert strategy.beam_size == 5

    def test_mps_uses_whisper_cpp(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="mps",
            audio_duration=300,
            quality_mode="balanced",
        )
        assert strategy.backend == "whisper-cpp"
        assert strategy.use_batched is False
        assert strategy.max_workers == 4

    def test_cpu_long_audio_uses_parallel(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=600,  # 10 minutes
            quality_mode="balanced",
        )
        assert strategy.use_batched is False
        assert strategy.max_workers == 4

    def test_cpu_short_audio_no_parallel(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=30,  # 30 seconds
            quality_mode="balanced",
        )
        # Short audio doesn't need parallel chunking
        assert strategy.max_workers >= 1

    def test_rocm_uses_faster_whisper(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="rocm",
            audio_duration=300,
            quality_mode="balanced",
        )
        assert strategy.backend == "faster-whisper"
        assert strategy.use_batched is True

    def test_explicit_beam_size_overrides_preset(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=300,
            quality_mode="speed",  # beam_size=1
            beam_size=5,  # explicit override
        )
        assert strategy.beam_size == 5

    def test_explicit_temperature_overrides_preset(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cuda",
            audio_duration=300,
            quality_mode="speed",
            temperature=0.7,
        )
        assert strategy.temperature == 0.7

    def test_default_quality_is_balanced(self):
        strategy = TranscriptionStrategy.auto_configure(
            device="cpu",
            audio_duration=300,
        )
        assert strategy.beam_size == QUALITY_PRESETS["balanced"]["beam_size"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_transcription_strategy.py -v
```
Expected: FAIL (module not found)

**Step 3: Create TranscriptionStrategy**

Create `api/transcription_strategy.py`:

```python
"""TranscriptionStrategy — auto-configuration for optimal transcription."""
from dataclasses import dataclass

from api.constants import QUALITY_PRESETS, DEFAULT_CPU_THREADS, DEFAULT_MAX_WORKERS


@dataclass
class TranscriptionStrategy:
    """Configuration for a transcription session."""
    backend: str  # "faster-whisper" | "whisper-cpp"
    device: str
    compute_type: str
    use_batched: bool
    batch_size: int
    beam_size: int
    temperature: float
    cpu_threads: int
    max_workers: int

    @classmethod
    def auto_configure(
        cls,
        device: str,
        audio_duration: float,
        quality_mode: str = "balanced",
        beam_size: int | None = None,
        temperature: float | None = None,
        use_batched: bool | None = None,
        batch_size: int = 8,
        cpu_threads: int | None = None,
    ) -> "TranscriptionStrategy":
        """Auto-configure optimal strategy based on device and audio."""
        # Resolve quality preset
        preset = QUALITY_PRESETS.get(quality_mode, QUALITY_PRESETS["balanced"])

        # Determine backend and compute type
        if device == "mps":
            backend = "whisper-cpp"
            compute_type = "int8" if quality_mode == "speed" else "float16"
            resolved_use_batched = False
            max_workers = DEFAULT_MAX_WORKERS
        elif device in ("cuda", "rocm"):
            backend = "faster-whisper"
            compute_type = "float16"
            resolved_use_batched = True if use_batched is None else use_batched
            max_workers = 1  # GPU uses BatchedInferencePipeline, not parallel
        else:  # cpu
            backend = "faster-whisper"
            compute_type = "int8"
            resolved_use_batched = False
            # CPU: use parallel chunking for audio > 90 seconds
            if audio_duration > 90:
                max_workers = DEFAULT_MAX_WORKERS
            else:
                max_workers = 1

        return cls(
            backend=backend,
            device=device,
            compute_type=compute_type,
            use_batched=resolved_use_batched,
            batch_size=batch_size,
            beam_size=beam_size if beam_size is not None else preset["beam_size"],
            temperature=temperature if temperature is not None else preset["temperature"],
            cpu_threads=cpu_threads or DEFAULT_CPU_THREADS,
            max_workers=max_workers,
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_transcription_strategy.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add api/transcription_strategy.py tests/unit/test_transcription_strategy.py
git commit -m "feat(whisper): add TranscriptionStrategy auto-configuration

- Auto-selects backend, compute_type, batched mode based on device
- CUDA/ROCm: faster-whisper + BatchedInferencePipeline
- MPS: whisper-cpp + parallel chunking
- CPU: faster-whisper + parallel chunking for audio > 90s
- Quality presets (speed/balanced/quality) control beam_size
- Explicit params override presets"
```

---

### Task 10: Update DeviceDetector tests for backend class resolution

**Files:**
- Modify: `tests/unit/test_device_detector.py` — enable backend class tests

**Step 1: Run the previously skipped backend class tests**

```bash
pytest tests/unit/test_device_detector.py::TestDeviceDetectorBackend -v
```

Now that FasterWhisperBackend and WhisperCppBackend exist, these should PASS.

**Step 2: Commit**

```bash
git add tests/unit/test_device_detector.py
git commit -m "test(whisper): enable DeviceDetector backend class tests"
```

---

### Phase 2 Verification

```bash
# Run all Phase 2 unit tests
pytest tests/unit/test_backend_protocol.py \
         tests/unit/test_device_detector.py \
         tests/unit/test_faster_whisper_backend.py \
         tests/unit/test_whisper_cpp_backend.py \
         tests/unit/test_transcription_strategy.py \
         -v --tb=short

# Expected: All tests PASS
```

**Phase 2 deliverables:**
- ✅ TranscriptionBackend Protocol
- ✅ FasterWhisperBackend (CPU/CUDA/ROCm)
- ✅ WhisperCppBackend (MPS)
- ✅ DeviceDetector
- ✅ TranscriptionStrategy auto_configure
- ✅ Full unit test coverage

---

## Phase 3: Parallel Chunking + BatchedInferencePipeline Integration

**Goal:** Refactor ChunkingEngine for parallel processing, integrate with backends.

---

### Task 11: Write parallel chunking tests

**Files:**
- Create: `tests/unit/test_chunking_parallel.py`

**Step 1: Write the failing test**

```python
"""Unit tests for parallel chunking."""
import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor


class TestParallelChunking:
    """Test parallel chunk transcription."""

    @patch("api.chunking.split_audio_into_chunks")
    @patch("api.chunking.transcribe_chunk")
    @patch("api.chunking.merge_transcription_results")
    def test_parallel_processing_calls_transcribe_for_each_chunk(
        self, mock_merge, mock_transcribe_chunk, mock_split
    ):
        from api.chunking import transcribe_audio_parallel

        mock_split.return_value = [
            MagicMock(chunk_id=0, start_time=0, end_time=60),
            MagicMock(chunk_id=1, start_time=58, end_time=120),
        ]
        mock_transcribe_chunk.return_value = {"text": "test", "segments": []}
        mock_merge.return_value = {"text": "merged", "segments": []}

        result = transcribe_audio_parallel(
            audio_path="/tmp/test.wav",
            language="en",
            model=MagicMock(),
            beam_size=1,
            vad_filter=True,
            temperature=0.0,
            max_workers=2,
        )

        assert mock_transcribe_chunk.call_count == 2
        mock_merge.assert_called_once()

    def test_result_ordering_by_timestamp(self):
        """Results should be ordered by timestamp regardless of completion order."""
        from api.chunking import merge_transcription_results

        # Simulate out-of-order results
        results = [
            {"text": "chunk 2", "offset": 60.0, "segments": [{"start": 60, "end": 65}]},
            {"text": "chunk 1", "offset": 0.0, "segments": [{"start": 0, "end": 5}]},
        ]

        merged = merge_transcription_results(results, overlap_duration=2)

        # Segments should be sorted by start time
        assert merged["segments"][0]["start"] <= merged["segments"][1]["start"]


class TestParallelChunkingConstraints:
    """Test parallel chunking worker limits."""

    def test_max_workers_capped_at_4(self):
        from api.constants import MAX_MAX_WORKERS
        assert MAX_MAX_WORKERS >= 4

    def test_min_workers_at_least_1(self):
        from api.constants import MIN_MAX_WORKERS
        assert MIN_MAX_WORKERS >= 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_chunking_parallel.py -v
```
Expected: FAIL (transcribe_audio_parallel doesn't exist)

**Step 3: Add parallel transcribe function to chunking.py**

Read `api/chunking.py` to understand the existing structure, then add:

```python
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed


def transcribe_audio_parallel(
    audio_path: str,
    language: str,
    model,
    beam_size: int = 1,
    vad_filter: bool = True,
    temperature: float = 0.0,
    max_workers: int = 4,
    chunk_config: ChunkConfig | None = None,
) -> dict:
    """Transcribe audio with parallel chunk processing.
    
    Splits audio into chunks, processes each chunk in parallel,
    and merges results ordered by timestamp.
    """
    if chunk_config is None:
        chunk_config = ChunkConfig()

    # Split audio into chunks
    chunks = split_audio_into_chunks(audio_path, chunk_config)

    if not chunks:
        # Fallback: transcribe whole file
        result = transcribe_chunk(
            chunk=AudioChunk(
                chunk_id=0,
                start_time=0,
                end_time=get_audio_duration(audio_path),
                file_path=audio_path,
                duration=get_audio_duration(audio_path),
                overlap_with_previous=0,
            ),
            model=model,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            temperature=temperature,
        )
        return result

    # Process chunks in parallel
    max_w = min(max_workers, len(chunks))
    chunk_results = []

    with ThreadPoolExecutor(max_workers=max_w) as executor:
        futures = {
            executor.submit(
                transcribe_chunk,
                chunk=chunk,
                model=model,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                temperature=temperature,
            ): chunk
            for chunk in chunks
        }

        for future in as_completed(futures):
            chunk_results.append(future.result())

    # Merge results (already sorted by timestamp)
    merged = merge_transcription_results(chunk_results, overlap_duration=chunk_config.overlap_duration)

    # Cleanup temp chunk files
    cleanup_chunks(chunks)

    return merged
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_chunking_parallel.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add api/chunking.py tests/unit/test_chunking_parallel.py
git commit -m "feat(whisper): add parallel chunk processing

- transcribe_audio_parallel() uses ThreadPoolExecutor
- Results merged and sorted by timestamp
- max_workers configurable, capped at 4
- Temp chunk files cleaned up after processing"
```

---

### Task 12: Create TranscriptionService orchestration layer

**Files:**
- Create: `api/transcription_service.py`
- Test: `tests/unit/test_transcription_service.py` (new)

**Step 1: Write the failing test**

```python
"""Unit tests for TranscriptionService."""
import pytest
from unittest.mock import MagicMock, patch


class TestTranscriptionService:
    """Test TranscriptionService orchestration."""

    @patch("api.transcription_service.DeviceDetector")
    @patch("api.transcription_service.TranscriptionStrategy")
    def test_transcribe_audio_selects_correct_backend(
        self, mock_strategy, mock_detector
    ):
        from api.transcription_service import TranscriptionService

        mock_detector.detect.return_value = "cpu"
        mock_strategy.auto_configure.return_value = MagicMock(
            backend="faster-whisper",
            device="cpu",
            compute_type="int8",
            use_batched=False,
            beam_size=3,
            temperature=0.0,
            batch_size=8,
            cpu_threads=8,
            max_workers=4,
        )

        service = TranscriptionService()
        # Would call service.transcribe_audio(...)
        # For now, just test initialization
        assert service is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_transcription_service.py -v
```
Expected: FAIL (module not found)

**Step 3: Create TranscriptionService**

Create `api/transcription_service.py` — this is the orchestration layer that ties together DeviceDetector, TranscriptionStrategy, backends, and chunking. It will be built incrementally in later phases. For now, create the skeleton:

```python
"""TranscriptionService — orchestration layer for multi-device transcription.

This service coordinates:
1. Device detection (DeviceDetector)
2. Strategy auto-configuration (TranscriptionStrategy)
3. Backend selection and model loading
4. Chunking engine dispatch (batched vs parallel)
5. Result formatting
"""
from api.device_detector import DeviceDetector
from api.transcription_strategy import TranscriptionStrategy


class TranscriptionService:
    """Orchestrates transcription across all devices and backends."""

    def __init__(self):
        self._detector = DeviceDetector()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_transcription_service.py -v
```

**Step 5: Commit**

```bash
git add api/transcription_service.py tests/unit/test_transcription_service.py
git commit -m "feat(whisper): add TranscriptionService skeleton

- Orchestration layer for multi-device transcription
- Will be expanded in Phase 5 with full pipeline integration"
```

---

### Phase 3 Verification

```bash
pytest tests/unit/test_chunking_parallel.py tests/unit/test_transcription_service.py -v
```

**Phase 3 deliverables:**
- ✅ Parallel chunking in chunking.py
- ✅ TranscriptionService skeleton
- ✅ Unit tests

---

## Phase 4: Docker Deployment + E2E Tests

**Goal:** CUDA/ROCm Dockerfiles, docker-compose profiles, Mac setup script, E2E tests.

---

### Task 13: Create CUDA Dockerfile

**Files:**
- Create: `Dockerfile.cuda`

**Step 1: Create the CUDA Dockerfile**

```dockerfile
# NVIDIA CUDA Dockerfile for GPU-accelerated Whisper transcription
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3-pip python3.12-dev \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-chi-tra tesseract-ocr-chi-sim \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-tha tesseract-ocr-vie \
    poppler-utils \
    libexif12 exiftool \
    fonts-noto-cjk \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with CUDA support
RUN uv pip install "faster-whisper>=1.2.0"
RUN uv pip install torch --index-url https://download.pytorch.org/whl/cu124

# Install project
COPY . .
RUN uv pip install -e ".[cuda]"

# Pre-download Whisper base model
RUN uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cuda', compute_type='float16')"

# Environment variables
ENV WHISPER_DEVICE=cuda
ENV WHISPER_COMPUTE_TYPE=float16
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Verify Dockerfile syntax**

```bash
docker build -f Dockerfile.cuda --no-cache --target=0 . 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add Dockerfile.cuda
git commit -m "feat(whisper): add CUDA Dockerfile for GPU deployment

- Based on nvidia/cuda:12.4.1-runtime-ubuntu22.04
- Installs faster-whisper + PyTorch CUDA
- Pre-downloads base model
- All system deps (ffmpeg, tesseract, poppler)"
```

---

### Task 14: Create ROCm Dockerfile

**Files:**
- Create: `Dockerfile.rocm`

**Step 1: Create the ROCm Dockerfile**

```dockerfile
# AMD ROCm Dockerfile for GPU-accelerated Whisper transcription
FROM rocm/dev-ubuntu-22.04:6.1

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3-pip python3.12-dev \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-chi-tra tesseract-ocr-chi-sim \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-tha tesseract-ocr-vie \
    poppler-utils \
    libexif12 exiftool \
    fonts-noto-cjk \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with ROCm support
RUN uv pip install "faster-whisper>=1.2.0"
RUN uv pip install torch --index-url https://download.pytorch.org/whl/rocm6.1

# Install project
COPY . .
RUN uv pip install -e ".[rocm]"

# Environment variables
ENV WHISPER_DEVICE=rocm
ENV WHISPER_COMPUTE_TYPE=float16
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Commit**

```bash
git add Dockerfile.rocm
git commit -m "feat(whisper): add ROCm Dockerfile for AMD GPU deployment

- Based on rocm/dev-ubuntu-22.04:6.1
- Installs faster-whisper + PyTorch ROCm
- All system deps matching CUDA image"
```

---

### Task 15: Update docker-compose.yml with GPU profiles

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Read current docker-compose.yml**

```bash
cat docker-compose.yml
```

**Step 2: Add GPU service and profiles**

Append to docker-compose.yml:

```yaml
  # GPU-accelerated service (NVIDIA CUDA)
  api-gpu:
    profiles: ["gpu"]
    build:
      context: .
      dockerfile: Dockerfile.cuda
    ports:
      - "${API_PORT:-51083}:8000"
    volumes:
      - ./data:/app/data
      - ./input:/app/input
      - ./output:/app/output
    environment:
      - WHISPER_MODEL=${WHISPER_MODEL:-base}
      - WHISPER_DEVICE=cuda
      - WHISPER_COMPUTE_TYPE=float16
      - WHISPER_CPU_THREADS=${WHISPER_CPU_THREADS:-0}
      - API_PORT=8000
      - API_HOST=0.0.0.0
      - API_DEBUG=${API_DEBUG:-false}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 3: Verify docker-compose syntax**

```bash
docker compose config --profiles
```

**Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(whisper): add GPU profile to docker-compose

- api-gpu service with NVIDIA GPU reservation
- Uses Dockerfile.cuda
- Activate with: docker compose --profile gpu up -d"
```

---

### Task 16: Create Mac setup script

**Files:**
- Create: `scripts/setup_mac.sh`

**Step 1: Create the setup script**

```bash
#!/bin/bash
# setup_mac.sh — Apple Silicon setup for whisper-cpp support
# Usage: bash scripts/setup_mac.sh

set -e

echo "=== Oh-My-MarkItDown: Apple Silicon Setup ==="

# Check if running on Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "ERROR: This script is for Apple Silicon (M1/M2/M3/M4) only."
    echo "Your machine: $(uname -m)"
    exit 1
fi

echo "Detected Apple Silicon ($(uname -m))"

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install whisper-cpp
echo "Installing whisper-cpp..."
brew install whisper-cpp

# Install Python dependencies
echo "Installing Python dependencies..."
pip install whispercpp>=2.0.0

echo ""
echo "=== Setup Complete ==="
echo "Whisper.cpp is now installed with Metal acceleration."
echo "Start the API with: docker compose --profile cpu up -d"
echo "Note: The API will use whisper-cpp for transcription on Apple Silicon."
```

**Step 2: Make executable**

```bash
chmod +x scripts/setup_mac.sh
```

**Step 3: Commit**

```bash
git add scripts/setup_mac.sh
git commit -m "feat(whisper): add Apple Silicon setup script

- Installs whisper-cpp via Homebrew
- Installs whispercpp Python bindings
- Validates Apple Silicon architecture"
```

---

### Task 17: Create test fixtures (audio assets)

**Files:**
- Create: `tests/fixtures/` directory
- Create: `tests/fixtures/generate_fixtures.py`

**Step 1: Create fixture generation script**

```bash
mkdir -p tests/fixtures
```

Create `tests/fixtures/generate_fixtures.py`:

```python
"""Generate test audio fixtures using ffmpeg."""
import subprocess
import os

FIXTURES_DIR = os.path.dirname(__file__)


def generate_silence(output_path: str, duration: float):
    """Generate silence audio file."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"anullsrc=r=16000:cl=mono",
        "-t", str(duration),
        "-c:a", "pcm_s16le",
        output_path,
    ], check=True, capture_output=True)


def generate_speech(output_path: str, duration: float):
    """Generate speech-like audio (sine wave tone)."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"sine=frequency=440:duration={duration}:sample_rate=16000",
        "-c:a", "pcm_s16le",
        output_path,
    ], check=True, capture_output=True)


if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    print("Generating 5s silence...")
    generate_silence(os.path.join(FIXTURES_DIR, "5s_silence.wav"), 5)

    print("Generating 5s speech-like audio...")
    generate_speech(os.path.join(FIXTURES_DIR, "5s_speech.wav"), 5)

    print("Generating 120s speech-like audio...")
    generate_speech(os.path.join(FIXTURES_DIR, "120s_speech.wav"), 120)

    print("Done!")
```

**Step 2: Generate fixtures**

```bash
python tests/fixtures/generate_fixtures.py
```

**Step 3: Commit**

```bash
git add tests/fixtures/
git commit -m "test(whisper): add test fixture generation script

- Generates silence and speech-like audio with ffmpeg
- 5s silence, 5s speech, 120s speech fixtures"
```

---

### Task 18: Create E2E test for audio transcription

**Files:**
- Create: `tests/e2e/test_audio_transcribe.py`

**Step 1: Write the E2E test**

```python
"""E2E tests for audio transcription API."""
import pytest
import asyncio
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestAudioTranscribeE2E:
    """E2E tests for POST /api/v1/convert/audio."""

    @pytest.mark.asyncio
    async def test_transcribe_short_audio_returns_markdown(self, api_client):
        """Transcribe 5s audio, expect markdown response."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny"},
            )

        assert response.status_code == 200
        content = response.text
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_transcribe_with_quality_mode_speed(self, api_client):
        """Transcribe with speed quality mode."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "quality_mode": "speed"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_transcribe_with_json_format(self, api_client):
        """Transcribe with JSON return format."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "return_format": "json"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data or "markdown" in data
```

**Step 2: Add api_client fixture to conftest.py**

Read `tests/conftest.py` and add:

```python
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def api_client():
    """HTTPX AsyncClient for E2E API testing."""
    from api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

**Step 3: Commit**

```bash
git add tests/e2e/test_audio_transcribe.py tests/conftest.py
git commit -m "test(whisper): add E2E test for audio transcription

- Tests POST /api/v1/convert/audio with short audio
- Tests quality_mode parameter
- Tests JSON return format
- Uses httpx ASGITransport for in-process testing"
```

---

### Phase 4 Verification

```bash
# Run E2E tests (requires API running or uses ASGITransport)
pytest tests/e2e/test_audio_transcribe.py -v -m e2e

# Verify docker-compose profiles
docker compose --profile cpu config
docker compose --profile gpu config
```

**Phase 4 deliverables:**
- ✅ CUDA Dockerfile
- ✅ ROCm Dockerfile
- ✅ docker-compose GPU profiles
- ✅ Mac setup script
- ✅ Test fixtures
- ✅ E2E audio test

---

## Phase 5: Hybrid Strategy + Full E2E + Documentation

**Goal:** Auto model selection, performance monitoring, full E2E suite, docs.

---

### Task 19: Add auto model selection to API endpoints

**Files:**
- Modify: `api/main.py` — all 3 transcription endpoints
- Test: `tests/unit/test_auto_model_selection.py` (new)

**Step 1: Write the failing test**

```python
"""Unit tests for auto model selection."""
import pytest
from api.whisper_transcribe import get_recommended_model


class TestAutoModelSelection:
    """Test get_recommended_model()."""

    def test_short_audio_recommends_tiny(self):
        assert get_recommended_model(30) == "tiny"

    def test_medium_audio_recommends_base(self):
        assert get_recommended_model(300) == "base"

    def test_long_audio_recommends_small(self):
        assert get_recommended_model(900) == "small"

    def test_very_long_audio_recommends_medium(self):
        assert get_recommended_model(3600) == "medium"
```

**Step 2: Run test, verify, commit**

```bash
pytest tests/unit/test_auto_model_selection.py -v
git add tests/unit/test_auto_model_selection.py
git commit -m "test(whisper): add auto model selection tests"
```

**Step 3: Update API endpoints to use auto model selection**

In each endpoint, when `model_size == "auto"`:
```python
if model_size == "auto":
    duration = get_audio_duration(tmp_path)
    model_size = get_recommended_model(duration)
```

**Step 4: Commit**

```bash
git add api/main.py
git commit -m "feat(whisper): enable auto model selection in API endpoints

- model_size='auto' selects model based on audio duration
- Short audio -> tiny, medium -> base, long -> small, very long -> medium"
```

---

### Task 20: Add performance monitoring metadata

**Files:**
- Modify: `api/whisper_transcribe.py` — metadata output
- Modify: `api/main.py` — response metadata

**Step 1: Extend metadata dict in transcription functions**

Update the metadata dict returned by `transcribe_audio()` and `transcribe_audio_chunked()` to include:

```python
metadata = {
    # Existing
    "processing_time_ms": total_time,
    "model_size": model_size,
    "language": detected_language,

    # New
    "backend": "faster-whisper",
    "device": device,
    "compute_type": compute_type,
    "use_batched": use_batched,
    "quality_mode": quality_mode,
    "beam_size": beam_size,
    "batch_size": batch_size,
    "cpu_threads": cpu_threads,
    "max_workers": max_workers,
    "model_load_time_ms": model_load_time,
    "transcription_time_ms": transcribe_time,
    "chunking_time_ms": chunking_time,
    "merging_time_ms": merging_time,
    "vad_filtered_duration_ms": vad_filtered,
    "realtime_factor": realtime_factor,
    "audio_duration_seconds": duration,
}
```

**Step 2: Commit**

```bash
git add api/whisper_transcribe.py api/main.py
git commit -m "feat(whisper): add performance monitoring metadata

- New metadata fields: backend, device, compute_type, quality_mode, etc.
- Timing breakdown: model_load, transcription, chunking, merging
- Realtime factor calculation"
```

---

### Task 21: Create remaining E2E tests

**Files:**
- Create: `tests/e2e/test_video_transcribe.py`
- Create: `tests/e2e/test_youtube_transcribe.py`
- Create: `tests/e2e/test_quality_modes.py`
- Create: `tests/e2e/test_api_compatibility.py`

**Step 1: Create video E2E test**

```python
"""E2E tests for video transcription API."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestVideoTranscribeE2E:
    """E2E tests for POST /api/v1/convert/video."""

    @pytest.mark.asyncio
    async def test_transcribe_short_video(self, api_client):
        """Transcribe short video, expect markdown."""
        # Skip if no video fixture
        video_path = FIXTURES_DIR / "sample_video.mp4"
        if not video_path.exists():
            pytest.skip("Video fixture not found")

        with open(video_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/video",
                files={"file": ("sample_video.mp4", f, "video/mp4")},
                params={"language": "en", "model_size": "tiny"},
            )

        assert response.status_code == 200
```

**Step 2: Create quality modes E2E test**

```python
"""E2E tests for quality mode presets."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestQualityModesE2E:
    """E2E tests for quality_mode parameter."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["speed", "balanced", "quality"])
    async def test_all_quality_modes_work(self, api_client, mode):
        """All quality modes should produce valid output."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "quality_mode": mode},
            )

        assert response.status_code == 200
        assert len(response.text) > 0
```

**Step 3: Create API compatibility test**

```python
"""E2E tests for backward compatibility."""
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestApiCompatibilityE2E:
    """Ensure existing API calls still work."""

    @pytest.mark.asyncio
    async def test_audio_without_new_params_still_works(self, api_client):
        """Old API calls (without new params) should still work."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "zh", "model_size": "base"},
            )

        assert response.status_code == 200
```

**Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "test(whisper): add remaining E2E tests

- Video transcription E2E
- Quality modes E2E (speed/balanced/quality)
- API backward compatibility E2E
- YouTube transcription E2E"
```

---

### Task 22: Update pyproject.toml dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update dependencies**

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing ...
    "faster-whisper>=1.2.0",
    "whispercpp>=2.0.0",
]

[project.optional-dependencies]
cuda = ["torch>=2.4.0"]
rocm = ["torch>=2.4.0"]
apple-silicon = ["whispercpp>=2.0.0"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
    "httpx>=0.27",
    "pytest-mock>=3.12",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests (mock models)",
    "integration: Integration tests (real tiny model)",
    "e2e: End-to-end tests (full API calls)",
    "slow: Long-running tests",
    "gpu: Tests requiring GPU",
]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "deps(whisper): update dependencies for multi-device support

- faster-whisper>=1.2.0 (BatchedInferencePipeline)
- whispercpp>=2.0.0 (Apple Silicon)
- Add optional deps: cuda, rocm, apple-silicon, dev
- Configure pytest markers"
```

---

### Task 23: Update documentation

**Files:**
- Modify: `README.md` — add GPU section
- Modify: `docs/API_REFERENCE.md` — add new params
- Modify: `CONFIG_GUIDE.md` — add new env vars

**Step 1: Update README.md**

Add GPU deployment section after Quick Start:

```markdown
## GPU Deployment

### NVIDIA CUDA

```bash
docker compose --profile gpu up -d
```

### AMD ROCm

```bash
docker compose -f docker-compose.yml -f docker-compose.rocm.yml up -d
```

### Apple Silicon

```bash
bash scripts/setup_mac.sh
```
```

**Step 2: Commit**

```bash
git add README.md docs/API_REFERENCE.md CONFIG_GUIDE.md
git commit -m "docs(whisper): update documentation for multi-device support

- Add GPU deployment section to README
- Document new API parameters
- Add new environment variables to CONFIG_GUIDE"
```

---

### Phase 5 Verification

```bash
# Run full test suite
pytest tests/ -v --tb=short -m "not slow and not gpu"

# Verify all E2E tests
pytest tests/e2e/ -v -m e2e

# Verify OpenAPI docs
curl http://localhost:51083/openapi.json | python -m json.tool | head -50
```

**Phase 5 deliverables:**
- ✅ Auto model selection
- ✅ Performance monitoring metadata
- ✅ Full E2E test suite
- ✅ Documentation updates

---

## Final Verification

```bash
# Full test suite
pytest tests/ -v --tb=short

# Lint check
python -m py_compile api/*.py api/backends/*.py

# Docker build (CPU)
docker compose --profile cpu build

# Health check
curl http://localhost:51083/health
```

## Summary of All Phases

| Phase | Tasks | Files Changed | Tests | Estimated |
|-------|-------|--------------|-------|-----------|
| 1: Foundation | 1-4 | constants.py, main.py | 2 test files | 4-6h |
| 2: Backend Abstraction | 5-10 | 4 new files, 1 modified | 5 test files | 6-10h |
| 3: Parallel Chunking | 11-12 | chunking.py, new service | 2 test files | 4-6h |
| 4: Docker + E2E | 13-18 | 2 Dockerfiles, compose, fixtures | 1 E2E test | 4-6h |
| 5: Hybrid + Docs | 19-23 | main.py, whisper_transcribe.py, docs | 4 E2E tests | 4-8h |
| **Total** | **23 tasks** | **31 files** | **14 test files** | **22-36h** |
