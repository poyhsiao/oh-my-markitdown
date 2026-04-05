# Whisper Multi-Device Performance Optimization — Design Spec

> **Date:** 2026-04-05
> **Author:** Kimhsiao (via AI)
> **Status:** Draft — Pending Review
> **Related:** `docs/survey/whisper-performance-optimization.md`

---

## 1. Overview

Comprehensive optimization of the Whisper transcription pipeline across all 6 optimization plans from the survey document, with multi-device backend abstraction supporting Apple Silicon (MPS), NVIDIA CUDA, AMD ROCm, and CPU.

### Goals

1. **5-10x CPU acceleration** and **10-15x GPU acceleration** for 1-hour audio
2. **Multi-device support**: auto-detect and use optimal backend per hardware
3. **TDD development**: full unit tests, integration tests, and E2E tests
4. **Backward compatible**: existing API calls work unchanged; new params are optional

### Non-Goals

- Model training or fine-tuning
- Real-time streaming transcription
- Speaker diarization
- Multi-GPU model parallelism (data parallelism only)

---

## 2. Architecture

### 2.1 Backend Abstraction Layer

```
┌─────────────────────────────────────────────────────┐
│                  API Endpoints                       │
│  /convert/audio  /convert/video  /convert/youtube    │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              TranscriptionService                    │
│  - Receives API params                               │
│  - Creates TranscriptionStrategy                     │
│  - Delegates to ChunkingEngine                       │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              TranscriptionStrategy                   │
│  - auto_configure(device, duration, quality_mode)   │
│  - Returns: backend, device, compute_type, etc.     │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              ChunkingEngine                          │
│  - GPU: BatchedInferencePipeline (built-in)          │
│  - CPU/MPS: Parallel ThreadPoolExecutor              │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│           TranscriptionBackend (Protocol)            │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │ FasterWhisperBackend │  │  WhisperCppBackend   │ │
│  │ CPU / CUDA / ROCm    │  │  MPS (Apple Silicon) │ │
│  │ BatchedInferencePipe │  │  Parallel chunking   │ │
│  └──────────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.2 TranscriptionBackend Protocol

```python
class TranscriptionBackend(Protocol):
    """Unified interface for all transcription backends."""

    name: str  # "faster-whisper" | "whisper-cpp"
    device: str  # "cpu" | "cuda" | "rocm" | "mps"
    supported_compute_types: list[str]
    supports_batched: bool

    def load_model(self, model_size: str, compute_type: str, **kwargs) -> None: ...
    def transcribe(
        self,
        audio_path: str,
        language: str | None,
        beam_size: int,
        temperature: float,
        vad_filter: bool,
        vad_params: dict | None,
        word_timestamps: bool,
        **kwargs,
    ) -> tuple[Iterator, dict]: ...
    def transcribe_batched(
        self,
        audio_path: str,
        language: str | None,
        batch_size: int,
        chunk_length_s: int,
        beam_size: int,
        temperature: float,
        vad_filter: bool,
        vad_params: dict | None,
        word_timestamps: bool,
        **kwargs,
    ) -> tuple[Iterator, dict]: ...
    def unload(self) -> None: ...
```

### 2.3 FasterWhisperBackend

**File:** `api/backends/faster_whisper_backend.py`

- **Devices:** CPU, CUDA, ROCm
- **Compute types:** int8 (CPU), float16 (GPU), int8_float16 (GPU)
- **Batched:** ✅ `BatchedInferencePipeline` from `faster-whisper >= 1.2.0`
- **Model caching:** Reuses existing `ModelCache` with cache key including `batched` flag

```python
class FasterWhisperBackend:
    def __init__(self, device: str = "cpu", model_cache: ModelCache | None = None):
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
```

### 2.4 WhisperCppBackend

**File:** `api/backends/whisper_cpp_backend.py`

- **Devices:** MPS (Apple Silicon)
- **Compute types:** float16, int8
- **Batched:** ❌ (manual parallel chunking via ThreadPoolExecutor)
- **Library:** `whisper-cpp` via `whisper-cpp-python` (https://github.com/stlukey/whispercpp.py) or `faster-whisper` CPU fallback if unavailable.
  - Primary: `whispercpp.py` — Python bindings for whisper.cpp with Metal/CoreML support on Apple Silicon
  - Fallback: `faster-whisper` with `device="cpu"` if whisper-cpp installation fails
  - pip package: `whispercpp` (not `whisper-cpp-py`)

```python
class WhisperCppBackend:
    def __init__(self, device: str = "mps", model_cache: ModelCache | None = None):
        self.name = "whisper-cpp"
        self.device = device
        self.supported_compute_types = ["float16", "int8"]
        self.supports_batched = False
        self._model_cache = model_cache or _model_cache
        self._model: Any | None = None
```

### 2.5 DeviceDetector

**File:** `api/device_detector.py`

```python
class DeviceDetector:
    @staticmethod
    def detect() -> str:
        """Detect primary compute device.
        
        Priority: CUDA > ROCm > MPS > CPU
        Returns: 'cuda' | 'rocm' | 'mps' | 'cpu'
        """

    @staticmethod
    def get_available_devices() -> list[str]:
        """Returns all available devices in priority order."""

    @staticmethod
    def get_backend_class(device: str) -> type:
        """mps -> WhisperCppBackend, else -> FasterWhisperBackend"""
```

**Detection logic:**
1. Try `torch.cuda.is_available()` → "cuda"
2. Check `ROCM_PATH` env var or `hipInfo` → "rocm"
3. Check `platform.system() == "Darwin"` and `platform.machine() == "arm64"` → "mps"
4. Fallback → "cpu"

### 2.6 TranscriptionStrategy

**File:** `api/transcription_strategy.py`

```python
@dataclass
class TranscriptionStrategy:
    backend: str  # "faster-whisper" | "whisper-cpp"
    device: str
    compute_type: str
    use_batched: bool
    batch_size: int
    beam_size: int
    temperature: float
    cpu_threads: int
    max_workers: int  # parallel chunking workers

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
```

**Auto-configuration matrix:**

| Device | Duration | quality_mode | backend | compute_type | batched | beam | workers |
|--------|----------|-------------|---------|-------------|---------|------|---------|
| CUDA | any | speed | faster-whisper | float16 | ✅ | 1 | N/A |
| CUDA | any | balanced | faster-whisper | float16 | ✅ | 3 | N/A |
| CUDA | any | quality | faster-whisper | float16 | ✅ | 5 | N/A |
| ROCm | any | speed | faster-whisper | float16 | ✅ | 1 | N/A |
| ROCm | any | balanced | faster-whisper | float16 | ✅ | 3 | N/A |
| ROCm | any | quality | faster-whisper | float16 | ✅ | 5 | N/A |
| MPS | any | speed | whisper-cpp | int8 | ❌ | 1 | 4 |
| MPS | any | balanced | whisper-cpp | int8 | ❌ | 3 | 4 |
| MPS | any | quality | whisper-cpp | float16 | ❌ | 5 | 4 |
| CPU | <90s | any | faster-whisper | int8 | ❌ | per-mode | N/A |
| CPU | >90s | speed | faster-whisper | int8 | ❌ | 1 | 4 |
| CPU | >90s | balanced | faster-whisper | int8 | ❌ | 3 | 4 |
| CPU | >90s | quality | faster-whisper | int8 | ❌ | 5 | 4 |

### 2.7 Quality Mode Presets

**File:** `api/constants.py`

```python
QUALITY_PRESETS = {
    "speed": {"beam_size": 1, "temperature": 0.0},
    "balanced": {"beam_size": 3, "temperature": 0.0},
    "quality": {"beam_size": 5, "temperature": 0.0},
}
```

---

## 3. API Endpoint Updates

### 3.1 New Parameters (all 3 transcription endpoints)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `beam_size` | int | None (auto from quality_mode) | Beam search size (1=speed, 5=quality) |
| `temperature` | float | None (auto from quality_mode) | Sampling temperature (0.0=greedy) |
| `quality_mode` | str | "balanced" | Preset: speed, balanced, quality |
| `use_batched` | bool | None (auto) | Use BatchedInferencePipeline |
| `batch_size` | int | 8 | Batch size for batched inference |
| `device` | str | "auto" | Device: auto, cpu, cuda, mps, rocm |
| `cpu_threads` | int | None (auto) | CPU thread count |

### 3.2 Endpoints Updated

- `POST /api/v1/convert/audio` — Audio file transcription
- `POST /api/v1/convert/video` — Video file transcription (extract audio → transcribe)
- `POST /api/v1/convert/youtube` — YouTube video transcription

### 3.3 Backward Compatibility

All new parameters have defaults matching current behavior:
- `quality_mode="balanced"` → beam_size=3 (close to current beam_size=5, slight speedup)
- `device="auto"` → DeviceDetector picks best available
- `use_batched=None` → auto (GPU=true, CPU=false)

Existing API calls without these parameters work identically.

---

## 4. Chunking Engine Refactor

### 4.1 Current Issues

1. **Sequential processing** — chunks processed one at a time
2. **Hardcoded params** — beam_size=5, temperature=0.0
3. **No batched support** — doesn't use BatchedInferencePipeline

### 4.2 Refactored Design

**File:** `api/chunking.py` (refactored)

```python
class ChunkingEngine:
    def transcribe(
        self,
        audio_path: str,
        backend: TranscriptionBackend,
        strategy: TranscriptionStrategy,
        language: str | None = None,
        vad_enabled: bool = True,
        vad_params: dict | None = None,
        word_timestamps: bool = False,
    ) -> tuple[str, dict]:
        if strategy.use_batched and backend.supports_batched:
            return self._transcribe_batched(audio_path, backend, strategy, ...)
        else:
            return self._transcribe_parallel(audio_path, backend, strategy, ...)

    def _transcribe_batched(self, ...):
        """Use BatchedInferencePipeline for GPU devices."""
        segments, info = backend.transcribe_batched(
            audio_path, language, strategy.batch_size, ...
        )
        return format_transcription(segments, info)

    def _transcribe_parallel(self, ...):
        """Split audio into chunks, process in parallel ThreadPoolExecutor."""
        chunks = split_audio_into_chunks(audio_path, chunk_config)
        max_workers = min(strategy.max_workers, len(chunks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(transcribe_chunk, chunk, ...): chunk for chunk in chunks}
            results = [f.result() for f in as_completed(futures)]
        return merge_transcription_results(results)
```

### 4.3 Parallel Chunking Constraints

| Device | max_workers | Rationale |
|--------|------------|-----------|
| CPU (8+ cores) | min(4, num_chunks) | Balance throughput vs memory |
| CPU (<8 cores) | min(2, num_chunks) | Prevent resource exhaustion |
| MPS | min(4, num_chunks) | Apple Silicon unified memory |
| GPU | N/A | Use BatchedInferencePipeline instead |

---

## 5. Docker Deployment

### 5.1 CPU Image (existing, optimized)

```dockerfile
FROM python:3.12-slim
# Existing dependencies + updated constants
```

### 5.2 NVIDIA CUDA Image (new)

```dockerfile
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    ffmpeg tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-chi-sim \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-tha tesseract-ocr-vie \
    poppler-utils exiftool \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv && uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN uv pip install "faster-whisper>=1.2.0" torch --extra-index-url https://download.pytorch.org/whl/cu124
RUN uv pip install -e ".[cuda]"

# Pre-download base model
RUN uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cuda', compute_type='float16')"
```

### 5.3 AMD ROCm Image (new)

```dockerfile
FROM rocm/dev-ubuntu-22.04:6.1

# Similar to CUDA image but with ROCm-specific packages
RUN uv pip install -e ".[rocm]"
```

### 5.4 docker-compose Updates

```yaml
services:
  api-cpu:
    profiles: ["cpu"]
    build:
      context: .
      dockerfile: Dockerfile
    # existing config

  api-gpu:
    profiles: ["gpu"]
    build:
      context: .
      dockerfile: Dockerfile.cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - WHISPER_DEVICE=cuda
      - WHISPER_COMPUTE_TYPE=float16
```

### 5.5 Apple Silicon Setup

Not Docker-based. Provide `scripts/setup_mac.sh`:

```bash
#!/bin/bash
# Install whisper-cpp with Metal support
brew install whisper-cpp
pip install whisper-cpp-py
```

---

## 6. Constants Updates

### 6.1 Updated Defaults

```python
# api/constants.py

# CPU threads: 4 -> 8
DEFAULT_CPU_THREADS = 8

# VAD parameters: more aggressive filtering
DEFAULT_VAD_MIN_SILENCE_MS = 500    # 300 -> 500
DEFAULT_VAD_THRESHOLD = 0.5         # 0.6 -> 0.5
DEFAULT_VAD_SPEECH_PAD_MS = 300     # 200 -> 300

# Chunking: beam_size 5 -> 1 (default for speed)
DEFAULT_CHUNK_BEAM_SIZE = 1
DEFAULT_CHUNK_TEMPERATURE = 0.0
```

### 6.2 New Constants

```python
# Quality presets
QUALITY_PRESETS = {
    "speed": {"beam_size": 1, "temperature": 0.0},
    "balanced": {"beam_size": 3, "temperature": 0.0},
    "quality": {"beam_size": 5, "temperature": 0.0},
}

# Batched inference defaults
DEFAULT_BATCH_SIZE = 8
DEFAULT_CHUNK_LENGTH_S = 30

# Parallel chunking
DEFAULT_MAX_WORKERS = 4
MIN_MAX_WORKERS = 1
MAX_MAX_WORKERS = 8

# Device detection
DEVICE_DETECTION_TIMEOUT = 5  # seconds
```

---

## 7. Dependency Updates

### 7.1 pyproject.toml Changes

```toml
[project]
dependencies = [
    # Existing
    "faster-whisper>=1.2.0",  # BatchedInferencePipeline stable
    "yt-dlp",
    "markitdown[all]",
    "fastapi",
    "uvicorn[standard]",
    "python-multipart",
    "aiofiles",
    "psutil",
    "pytesseract>=0.3.10",
    "ffmpeg-python>=0.2.0",
    "pymupdf>=1.23.0",
    "openai",
    "readability-lxml>=0.8.4.1",

    # New
    "whispercpp>=2.0.0",  # whisper.cpp Python bindings (Apple Silicon)
]

[project.optional-dependencies]
cuda = [
    "torch>=2.4.0",
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12",
]
rocm = [
    "torch>=2.4.0",
    # CTranslate2 ROCm: use official ROCm wheel or build from source
    # pip install ctranslate2 --extra-index-url https://rocm-pytorch.github.io/whl/
]
apple-silicon = [
    "whispercpp>=2.0.0",  # whisper.cpp Python bindings (whispercpp.py)
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
    "httpx>=0.27",  # E2E API testing
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

---

## 8. Testing Strategy (TDD)

### 8.1 Unit Tests (Mock Models)

| File | Tests | Mark |
|------|-------|------|
| `tests/unit/test_device_detector.py` | Device detection logic (mock torch, platform, env vars) | `@pytest.mark.unit` |
| `tests/unit/test_transcription_strategy.py` | auto_configure matrix, quality presets, edge cases | `@pytest.mark.unit` |
| `tests/unit/test_faster_whisper_backend.py` | Model loading, transcribe, transcribe_batched, unload (mock WhisperModel, BatchedInferencePipeline) | `@pytest.mark.unit` |
| `tests/unit/test_whisper_cpp_backend.py` | Model loading, transcribe, unload (mock whisper-cpp) | `@pytest.mark.unit` |
| `tests/unit/test_chunking_parallel.py` | Parallel chunking correctness, result ordering, error handling | `@pytest.mark.unit` |
| `tests/unit/test_api_params.py` | API parameter validation, quality_mode presets, default values | `@pytest.mark.unit` |
| `tests/unit/test_transcription_service.py` | Service orchestration, backend selection, strategy creation | `@pytest.mark.unit` |

### 8.2 Integration Tests (Real tiny Model)

| File | Tests | Mark |
|------|-------|------|
| `tests/integration/test_transcribe_pipeline.py` | Full transcription pipeline with tiny model on CPU | `@pytest.mark.integration` |
| `tests/integration/test_backend_switching.py` | Backend switching correctness | `@pytest.mark.integration` |
| `tests/integration/test_batched_inference.py` | BatchedInferencePipeline result quality vs standard | `@pytest.mark.integration` |
| `tests/integration/test_chunking.py` | Chunking with real audio files | `@pytest.mark.integration` |

### 8.3 E2E Tests (Full API, CPU Only)

| File | Tests | Mark |
|------|-------|------|
| `tests/e2e/test_audio_transcribe.py` | POST /api/v1/convert/audio — various formats, languages, params | `@pytest.mark.e2e` |
| `tests/e2e/test_video_transcribe.py` | POST /api/v1/convert/video — audio extraction + transcription | `@pytest.mark.e2e` |
| `tests/e2e/test_youtube_transcribe.py` | POST /api/v1/convert/youtube — subtitle fallback, whisper | `@pytest.mark.e2e` |
| `tests/e2e/test_quality_modes.py` | All three quality modes produce valid output | `@pytest.mark.e2e` |
| `tests/e2e/test_api_compatibility.py` | Existing API calls still work (backward compat) | `@pytest.mark.e2e` |

### 8.4 Test Fixtures

```python
# tests/conftest.py

@pytest.fixture
def mock_faster_whisper_model():
    """Mock WhisperModel for unit tests."""

@pytest.fixture
def mock_whisper_cpp_model():
    """Mock whisper-cpp model for unit tests."""

@pytest.fixture
def sample_audio_path():
    """Path to a short test audio file (5 seconds)."""

@pytest.fixture
def sample_video_path():
    """Path to a short test video file (5 seconds)."""

@pytest.fixture
def api_client():
    """HTTPX AsyncClient for E2E API testing."""

@pytest.fixture
def tiny_model():
    """Real tiny model for integration tests."""
```

### 8.5 Test Audio Assets

Create `tests/fixtures/` with:
- `5s_silence.wav` — 5 seconds silence (VAD test)
- `5s_speech.wav` — 5 seconds speech (basic transcription)
- `120s_speech.wav` — 2 minutes speech (chunking threshold test)
- `sample_video.mp4` — Short video with audio
- `test_srt.srt`, `test_vtt.vtt` — Subtitle format tests

---

## 9. Performance Monitoring

### 9.1 Metadata Extensions

```python
metadata = {
    # Existing
    "processing_time_ms": total_time,
    "model_size": model_size,
    "language": detected_language,

    # New
    "backend": "faster-whisper" | "whisper-cpp",
    "device": "cpu" | "cuda" | "rocm" | "mps",
    "compute_type": "int8" | "float16",
    "use_batched": True | False,
    "quality_mode": "speed" | "balanced" | "quality",
    "beam_size": 1 | 3 | 5,
    "batch_size": 8,
    "cpu_threads": 8,
    "max_workers": 4,
    "model_load_time_ms": model_load_time,
    "transcription_time_ms": transcribe_time,
    "chunking_time_ms": chunking_time,
    "merging_time_ms": merging_time,
    "vad_filtered_duration_ms": vad_filtered,
    "realtime_factor": processing_time / audio_duration,
    "audio_duration_seconds": duration,
}
```

### 9.2 Monitoring Thresholds

| Metric | CPU Target | GPU Target |
|--------|-----------|-----------|
| Real-time Factor | < 0.5x | < 0.2x |
| Model Load Time | < 30s | < 15s |
| Cache Hit Rate | > 80% | > 80% |
| VAD Filter Rate | 20-60% | 20-60% |
| Error Rate | < 1% | < 1% |

---

## 10. Implementation Phases

### Phase 1: Foundation (Plans 1+2) — 4-6 hours
- Update constants.py (CPU threads, VAD params)
- Add quality_mode presets
- Add new API parameters to all 3 endpoints
- Unit tests: parameter validation

### Phase 2: Backend Abstraction (Plan 4 core) — 6-10 hours
- TranscriptionBackend Protocol
- FasterWhisperBackend + BatchedInferencePipeline
- WhisperCppBackend (Apple Silicon)
- DeviceDetector
- TranscriptionStrategy auto_configure
- Unit tests: all backends and strategies

### Phase 3: Parallel Chunking (Plan 3) — 4-6 hours
- Refactor ChunkingEngine for parallel processing
- Integrate BatchedInferencePipeline
- Unit tests: parallel correctness
- Integration tests

### Phase 4: Docker Deployment (Plan 5) — 4-6 hours
- CUDA Dockerfile
- ROCm Dockerfile
- docker-compose profiles
- Mac setup script
- E2E tests

### Phase 5: Hybrid Strategy (Plan 6) — 4-8 hours
- Auto model selection (model_size="auto")
- Performance monitoring metadata
- Full E2E test suite
- Documentation updates (OpenAPI, README)

**Total estimated: 22-36 hours**

---

## 11. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| whisper-cpp-py compatibility | Medium | Fallback to faster-whisper CPU if unavailable |
| ROCm CTranslate2 build complexity | Medium | Provide pre-built wheels or Docker image |
| BatchedInferencePipeline memory usage | Low | Configurable batch_size, default 8 |
| Parallel chunking memory pressure | Low | max_workers capped at 4 |
| API backward compatibility | Low | All new params have defaults |
| Test asset licensing | Low | Generate synthetic audio with ffmpeg |

---

## 12. File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `api/constants.py` | Modify | Update defaults, add presets |
| `api/whisper_transcribe.py` | Modify | Refactor to use new architecture |
| `api/main.py` | Modify | Add new API parameters |
| `api/chunking.py` | Modify | Add parallel processing |
| `api/device_detector.py` | **New** | Hardware detection |
| `api/transcription_strategy.py` | **New** | Strategy auto-configuration |
| `api/backends/__init__.py` | **New** | Backend package |
| `api/backends/faster_whisper_backend.py` | **New** | Faster-whisper backend |
| `api/backends/whisper_cpp_backend.py` | **New** | Whisper-cpp backend |
| `api/transcription_service.py` | **New** | Service orchestration layer |
| `Dockerfile.cuda` | **New** | NVIDIA CUDA image |
| `Dockerfile.rocm` | **New** | AMD ROCm image |
| `scripts/setup_mac.sh` | **New** | Apple Silicon setup |
| `tests/unit/test_device_detector.py` | **New** | Device detection tests |
| `tests/unit/test_transcription_strategy.py` | **New** | Strategy tests |
| `tests/unit/test_faster_whisper_backend.py` | **New** | Backend unit tests |
| `tests/unit/test_whisper_cpp_backend.py` | **New** | Backend unit tests |
| `tests/unit/test_chunking_parallel.py` | **New** | Parallel chunking tests |
| `tests/unit/test_api_params.py` | **New** | API parameter tests |
| `tests/unit/test_transcription_service.py` | **New** | Service tests |
| `tests/integration/test_transcribe_pipeline.py` | **New** | Integration tests |
| `tests/integration/test_backend_switching.py` | **New** | Backend switching tests |
| `tests/integration/test_batched_inference.py` | **New** | Batched inference tests |
| `tests/integration/test_chunking.py` | **New** | Chunking integration tests |
| `tests/e2e/test_audio_transcribe.py` | **New** | Audio E2E tests |
| `tests/e2e/test_video_transcribe.py` | **New** | Video E2E tests |
| `tests/e2e/test_youtube_transcribe.py` | **New** | YouTube E2E tests |
| `tests/e2e/test_quality_modes.py` | **New** | Quality mode E2E tests |
| `tests/e2e/test_api_compatibility.py` | **New** | Backward compat tests |
| `tests/fixtures/` | **New** | Test audio assets |
| `tests/conftest.py` | Modify | Add new fixtures |
| `pyproject.toml` | Modify | Update dependencies |
| `docker-compose.yml` | Modify | Add GPU profiles |
