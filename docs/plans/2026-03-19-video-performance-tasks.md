# Video Conversion Performance Tasks

**Document ID:** PERF-TASKS-001  
**Created:** 2026-03-19  
**Author:** AI Assistant  
**Status:** Ready for Implementation  
**Related Documents:** video-performance-requirements.md, video-performance-design.md

---

## Task Overview

| Phase | Tasks | Estimated Effort |
|-------|-------|------------------|
| Phase 1: Foundation | 3 | 1-2 hours |
| Phase 2: Core Optimization | 5 | 3-4 hours |
| Phase 3: API Updates | 3 | 2-3 hours |
| Phase 4: Docker Support | 3 | 1-2 hours |
| Phase 5: Documentation | 3 | 1 hour |
| **Total** | **17** | **8-12 hours** |

---

## Phase 1: Foundation (Testing & Infrastructure)

### Task 1.1: Create Test Framework and Benchmarks

**Priority:** P0 (Highest)  
**Status:** [ ] Pending  
**Estimated Time:** 45 minutes

**Description:**
Set up performance testing infrastructure and baseline benchmarks.

**Files to Create:**
```
tests/
├── performance/
│   ├── __init__.py
│   ├── benchmark_transcribe.py
│   └── benchmark_audio_extract.py
├── unit/
│   ├── test_device_utils.py
│   └── test_performance_config.py
└── fixtures/
    └── .gitkeep
```

**Acceptance Criteria:**
- [ ] Benchmark test structure created
- [ ] Baseline CPU benchmark test implemented
- [ ] Baseline CUDA benchmark test implemented (skip if unavailable)
- [ ] Baseline MPS benchmark test implemented (skip if unavailable)
- [ ] Test fixtures directory created

**Implementation Notes:**
```python
# tests/performance/benchmark_transcribe.py
class TestTranscribeBenchmark:
    def test_benchmark_cpu_1min(self, sample_1min_audio):
        """1 minute audio - CPU baseline"""
        # Measure processing time
        # Assert < 3x duration
```

---

### Task 1.2: Create Device Detection Module

**Priority:** P0  
**Status:** [ ] Pending  
**Estimated Time:** 30 minutes

**Description:**
Create `api/device_utils.py` with GPU detection and device information functions.

**Files to Create:**
- `api/device_utils.py`

**Acceptance Criteria:**
- [ ] `detect_device()` function returns correct device
- [ ] `get_compute_type_for_device()` returns appropriate compute type
- [ ] `get_device_info()` returns complete device information
- [ ] `validate_device()` validates requested device availability
- [ ] Unit tests pass

**Implementation Notes:**
```python
# api/device_utils.py
def detect_device() -> DeviceType:
    """Auto-detect: CUDA > MPS > CPU"""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
```

---

### Task 1.3: Update Configuration Module

**Priority:** P0  
**Status:** [ ] Pending  
**Estimated Time:** 30 minutes

**Description:**
Add `PerformanceConfig` dataclass to `api/config.py`.

**Files to Modify:**
- `api/config.py`

**Acceptance Criteria:**
- [ ] `PerformanceConfig` dataclass created
- [ ] `get_effective_device()` resolves "auto"
- [ ] `get_effective_compute_type()` resolves "auto"
- [ ] `get_effective_threads()` auto-detects CPU cores
- [ ] Configuration validates correctly
- [ ] Unit tests pass

**Implementation Notes:**
```python
@dataclass
class PerformanceConfig:
    device: str = "auto"
    compute_type: str = "auto"
    cpu_threads: int = 0  # 0 = auto
    vad_enabled: bool = True
    vad_min_silence_ms: int = 300
    ...
```

---

## Phase 2: Core Optimization

### Task 2.1: Update Constants Module

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Add VAD, audio, and model selection constants to `api/constants.py`.

**Files to Modify:**
- `api/constants.py`

**Acceptance Criteria:**
- [ ] VAD constants added
- [ ] Audio extraction constants added
- [ ] Model selection thresholds added
- [ ] CPU threading constants added

**Implementation Notes:**
```python
# VAD Parameters
DEFAULT_VAD_MIN_SILENCE_MS = 300
DEFAULT_VAD_THRESHOLD = 0.6

# Audio Extraction
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CODEC = "pcm_s16le"

# Model Selection
MODEL_SELECTION_THRESHOLDS = {
    "tiny": 120, "base": 600, ...
}
```

---

### Task 2.2: Implement Model Selection Function

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Add `get_recommended_model()` function to `api/whisper_transcribe.py`.

**Files to Modify:**
- `api/whisper_transcribe.py`

**Acceptance Criteria:**
- [ ] Function returns correct model based on duration
- [ ] Unit tests pass
- [ ] Edge cases handled (0 duration, very long)

**Implementation Notes:**
```python
def get_recommended_model(duration_seconds: float) -> str:
    if duration_seconds < 120: return "tiny"
    elif duration_seconds < 600: return "base"
    ...
```

---

### Task 2.3: Optimize Audio Extraction

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 45 minutes

**Description:**
Modify `extract_audio_from_video()` to use WAV/PCM format and multi-threading.

**Files to Modify:**
- `api/whisper_transcribe.py`

**Acceptance Criteria:**
- [ ] Audio extracted as WAV/PCM (16kHz mono)
- [ ] FFmpeg uses multi-threading (4 threads)
- [ ] Performance benchmark shows improvement
- [ ] Existing tests still pass

**Implementation Notes:**
```python
cmd = [
    "ffmpeg", "-threads", "4",
    "-i", video_path,
    "-vn", "-ac", "1", "-ar", "16000",
    "-acodec", "pcm_s16le",
    "-y", output_audio_path
]
```

---

### Task 2.4: Optimize VAD Parameters

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 30 minutes

**Description:**
Update VAD parameters in `transcribe_audio()` function.

**Files to Modify:**
- `api/whisper_transcribe.py`

**Acceptance Criteria:**
- [ ] VAD parameters configurable
- [ ] Default uses optimized values (300ms, 0.6 threshold)
- [ ] Quality tests pass (no significant WER degradation)
- [ ] Performance improved

**Implementation Notes:**
```python
vad_parameters = {
    "min_silence_duration_ms": 300,
    "threshold": 0.6,
    "speech_pad_ms": 200
}
```

---

### Task 2.5: Update Transcribe Function Signatures

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 45 minutes

**Description:**
Update `transcribe_audio()`, `transcribe_youtube_video()`, and related functions with new parameters.

**Files to Modify:**
- `api/whisper_transcribe.py`

**Acceptance Criteria:**
- [ ] New parameters added (device, model_size, cpu_threads, vad_enabled, vad_params)
- [ ] Parameters use config defaults when not specified
- [ ] All existing callers updated
- [ ] Tests pass

**Implementation Notes:**
```python
def transcribe_audio(
    audio_path: str,
    language: str = "auto",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    ...
):
```

---

## Phase 3: API Updates

### Task 3.1: Add New API Parameters

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 45 minutes

**Description:**
Add new parameters to all Whisper transcription endpoints.

**Files to Modify:**
- `api/main.py`

**Endpoints to Update:**
- `/api/v1/convert/video`
- `/api/v1/convert/audio`
- `/api/v1/convert/youtube`

**Acceptance Criteria:**
- [ ] All endpoints accept new parameters
- [ ] Parameters optional with defaults
- [ ] Backward compatible
- [ ] Integration tests pass

**Implementation Notes:**
```python
@router.post("/convert/video")
async def convert_video(
    file: UploadFile = File(...),
    # Existing params...
    device: Optional[str] = Form(None),
    model_size: Optional[str] = Form(None),
    cpu_threads: Optional[int] = Form(None),
    vad_enabled: Optional[bool] = Form(None),
):
```

---

### Task 3.2: Add Device Info Endpoint

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Create new `/api/v1/device-info` endpoint.

**Files to Modify:**
- `api/main.py`

**Acceptance Criteria:**
- [ ] Endpoint returns device information
- [ ] CUDA info included when available
- [ ] MPS info included when available
- [ ] Response format documented

**Implementation Notes:**
```python
@router.get("/device-info")
async def get_device_info_endpoint():
    return get_device_info()
```

---

### Task 3.3: Update OpenAPI Documentation

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 30 minutes

**Description:**
Update API documentation with new parameters and endpoint.

**Files to Modify:**
- `api/main.py` (docstrings)
- `docs/api/` (if exists)

**Acceptance Criteria:**
- [ ] All new parameters documented
- [ ] New endpoint documented
- [ ] Examples provided
- [ ] ReDoc/Docs render correctly

---

## Phase 4: Docker Support

### Task 4.1: Update Dockerfile with Multi-Stage Build

**Priority:** P1  
**Status:** [ ] Pending  
**Estimated Time:** 30 minutes

**Description:**
Create multi-stage Dockerfile supporting both CPU and GPU images.

**Files to Modify:**
- `Dockerfile`

**Acceptance Criteria:**
- [ ] CPU base stage created
- [ ] CUDA stage created
- [ ] Default stage is CPU
- [ ] Both stages build successfully
- [ ] Image size optimized

**Implementation Notes:**
```dockerfile
FROM python:3.12-slim AS cpu-base
# ... CPU setup

FROM nvidia/cuda:11.8-runtime-ubuntu22.04 AS cuda-base
# ... CUDA setup

FROM cpu-base AS default
# ... final image
```

---

### Task 4.2: Update docker-compose.yml

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Add GPU service configuration to docker-compose.yml.

**Files to Modify:**
- `docker-compose.yml`

**Acceptance Criteria:**
- [ ] GPU service defined with profile
- [ ] GPU resource limits configured
- [ ] Environment variables set correctly
- [ ] Both services can start

**Implementation Notes:**
```yaml
services:
  markitdown-api-gpu:
    profiles: [gpu]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

### Task 4.3: Update Environment Variables

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 15 minutes

**Description:**
Add new environment variables to `.env.example`.

**Files to Modify:**
- `.env.example`

**Acceptance Criteria:**
- [ ] All new variables documented
- [ ] Default values provided
- [ ] Comments explain usage
- [ ] Categorized logically

**Implementation Notes:**
```bash
# GPU Configuration
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto

# CPU Performance
WHISPER_CPU_THREADS=0  # 0 = auto

# VAD Configuration
WHISPER_VAD_ENABLED=true
WHISPER_VAD_MIN_SILENCE_MS=300
...
```

---

## Phase 5: Documentation

### Task 5.1: Update README

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Update README with GPU support and performance optimization information.

**Files to Modify:**
- `README.md`
- `README_ZH_TW.md`

**Acceptance Criteria:**
- [ ] GPU support documented
- [ ] Performance improvements documented
- [ ] Configuration examples provided
- [ ] Docker GPU instructions included

---

### Task 5.2: Update API Documentation

**Priority:** P2  
**Status:** [ ] Pending  
**Estimated Time:** 20 minutes

**Description:**
Update API documentation with new endpoints and parameters.

**Files to Modify:**
- `docs/api/` (if exists)
- Inline documentation

**Acceptance Criteria:**
- [ ] New parameters documented
- [ ] Device info endpoint documented
- [ ] Examples provided

---

### Task 5.3: Update Performance Plan Document

**Priority:** P3  
**Status:** [ ] Pending  
**Estimated Time:** 10 minutes

**Description:**
Update the original performance plan document status.

**Files to Modify:**
- `docs/plans/video-conversion-performance-improvement.md`

**Acceptance Criteria:**
- [ ] Status changed to "Approved"
- [ ] Links to requirements/design/tasks added
- [ ] Change log updated

---

## Testing Checklist

### Unit Tests
- [ ] `test_device_utils.py` - All device detection tests pass
- [ ] `test_config.py` - Configuration resolution tests pass
- [ ] `test_whisper_transcribe.py` - Model selection tests pass

### Performance Tests
- [ ] CPU benchmark - Processing time < 1.5x duration
- [ ] CUDA benchmark - Processing time < 0.5x duration (if available)
- [ ] MPS benchmark - Processing time < 1x duration (if available)
- [ ] Audio extraction - 30-50% improvement verified

### Quality Tests
- [ ] WER comparison - < 5% degradation
- [ ] Transcription completeness - 100%

### Integration Tests
- [ ] Video API with new parameters
- [ ] Audio API with new parameters
- [ ] YouTube API with new parameters
- [ ] Device info endpoint

---

## Verification Commands

```bash
# Run all tests
pytest tests/ -v

# Run performance benchmarks
pytest tests/performance/ -v --benchmark-only

# Run specific test file
pytest tests/unit/test_device_utils.py -v

# Check GPU detection
curl http://localhost:51083/api/v1/device-info

# Test video conversion with GPU
curl -X POST "http://localhost:51083/api/v1/convert/video" \
  -F "file=@test.mp4" \
  -F "device=cuda" \
  -F "model_size=auto"

# Build Docker CPU image
docker compose build

# Build Docker GPU image
docker compose --profile gpu build
```

---

## Rollback Plan

If issues arise during implementation:

1. **Phase 1 issues** - Can rollback individual modules, no API changes yet
2. **Phase 2 issues** - Revert file changes, tests should catch regressions
3. **Phase 3 issues** - New parameters are optional, existing calls unaffected
4. **Phase 4 issues** - Docker images are separate, can use previous version
5. **Phase 5 issues** - Documentation only, no code impact

---

## Dependencies

### Internal Dependencies
```
Task 1.1 (Tests) → Task 1.2 (Device Utils) → Task 1.3 (Config)
                                          ↓
Task 2.1 (Constants) → Task 2.2 (Model Selection)
                     → Task 2.3 (Audio Extract)
                     → Task 2.4 (VAD)
                     → Task 2.5 (Transcribe) → Task 3.1 (API)
                                               → Task 3.2 (Device Info)
Task 4.1 (Dockerfile) → Task 4.2 (Compose) → Task 4.3 (Env)
Task 5.1 (README) → Task 5.2 (API Docs) → Task 5.3 (Plan Update)
```

### External Dependencies
- PyTorch with CUDA support (for GPU)
- NVIDIA Docker runtime (for GPU containers)
- FFmpeg (existing)

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-19 | 1.0.0 | Initial task breakdown |

---

**Document Status:** Ready for Implementation  
**Next Step:** Begin with Task 1.1  
**Owner:** Development Team