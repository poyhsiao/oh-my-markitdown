# Whisper Multi-Device Performance Optimization — Tasks

**Document ID**: 2026-04-05-whisper-performance-tasks  
**Created**: 2026-04-05  
**Author**: Kimhsiao  
**Status**: Draft  
**Related**: [Requirements](./2026-04-05-whisper-performance-requirements.md) | [Design](../superpowers/specs/2026-04-05-whisper-multi-device-performance-optimization.md) | [Plan](./2026-04-05-whisper-multi-device-performance-optimization.md)

---

## Task Overview

| Phase | Description | Tasks | Effort | Status |
|-------|-------------|-------|--------|--------|
| Phase 1 | Foundation (Plans 1+2) | 1-4 | 4-6h | [ ] Pending |
| Phase 2 | Backend Abstraction (Plan 4) | 5-10 | 6-10h | [ ] Pending |
| Phase 3 | Parallel Chunking (Plan 3) | 11-12 | 4-6h | [ ] Pending |
| Phase 4 | Docker + E2E (Plan 5) | 13-18 | 4-6h | [ ] Pending |
| Phase 5 | Hybrid + Docs (Plan 6) | 19-23 | 4-8h | [ ] Pending |
| **Total** | | **23 tasks** | **22-36h** | |

---

## Phase 1: Foundation — Constants, Presets, API Parameters (4-6h)

### 1.1 Update constants.py defaults and add presets

- [ ] Update `DEFAULT_CPU_THREADS` from 4 to 8
- [ ] Update `DEFAULT_VAD_MIN_SILENCE_MS` from 300 to 500
- [ ] Update `DEFAULT_VAD_THRESHOLD` from 0.6 to 0.5
- [ ] Update `DEFAULT_VAD_SPEECH_PAD_MS` from 200 to 300
- [ ] Add `QUALITY_PRESETS` dict (speed/balanced/quality)
- [ ] Add `DEFAULT_CHUNK_BEAM_SIZE = 1`
- [ ] Add `DEFAULT_CHUNK_TEMPERATURE = 0.0`
- [ ] Add `DEFAULT_BATCH_SIZE = 8`
- [ ] Add `DEFAULT_CHUNK_LENGTH_S = 30`
- [ ] Add `DEFAULT_MAX_WORKERS = 4`, `MIN_MAX_WORKERS = 1`, `MAX_MAX_WORKERS = 8`
- **Files**: `api/constants.py` (lines 80-118)
- **Test**: `tests/unit/test_constants.py` — 12 tests for all new/updated constants
- **Effort**: 30min
- **Acceptance**: `pytest tests/unit/test_constants.py -v` all PASS

### 1.2 Add new API parameters to /convert/audio endpoint

- [ ] Add `quality_mode: str = Query("balanced")`
- [ ] Add `beam_size: int = Query(None)`
- [ ] Add `temperature: float = Query(None)`
- [ ] Add `use_batched: bool = Query(None)`
- [ ] Add `batch_size: int = Query(8)`
- [ ] Add `device: str = Query("auto")`
- [ ] Add `cpu_threads: int = Query(None)`
- [ ] Change `model_size` default from `"base"` to `"auto"`
- **Files**: `api/main.py` — `transcribe_audio_file()` function
- **Test**: `tests/unit/test_api_params.py` — parameter validation tests
- **Effort**: 1h
- **Acceptance**: API starts, Swagger UI shows new params, existing calls work

### 1.3 Add new API parameters to /convert/video endpoint

- [ ] Add same 7 parameters as Task 1.2
- **Files**: `api/main.py` — `transcribe_video_file()` function
- **Effort**: 30min
- **Acceptance**: `python -m py_compile api/main.py` succeeds

### 1.4 Add new API parameters to /convert/youtube endpoint

- [ ] Add same 7 parameters as Task 1.2
- **Files**: `api/main.py` — `transcribe_youtube()` function
- **Effort**: 30min
- **Acceptance**: All unit tests pass, API backward compatible

---

## Phase 2: Backend Abstraction Layer (6-10h)

### 2.1 Create backends package and Protocol

- [ ] Create `api/backends/` directory
- [ ] Create `api/backends/__init__.py`
- [ ] Create `api/backends/protocol.py` with `TranscriptionBackend` Protocol
- [ ] Protocol defines: name, device, supported_compute_types, supports_batched
- [ ] Protocol methods: load_model(), transcribe(), transcribe_batched(), unload()
- **Files**: `api/backends/__init__.py`, `api/backends/protocol.py`
- **Test**: `tests/unit/test_backend_protocol.py`
- **Effort**: 1h
- **Acceptance**: Protocol importable, has all required attributes and methods

### 2.2 Create DeviceDetector

- [ ] Create `api/device_detector.py`
- [ ] `detect()` — priority: CUDA > ROCm > MPS > CPU
- [ ] `get_available_devices()` — list all detected devices
- [ ] `get_backend_class(device)` — route to correct backend
- **Files**: `api/device_detector.py`
- **Test**: `tests/unit/test_device_detector.py` — mock torch, platform, env vars
- **Effort**: 1h
- **Acceptance**: Correct device detection for all 4 device types

### 2.3 Create FasterWhisperBackend

- [ ] Create `api/backends/faster_whisper_backend.py`
- [ ] Support CPU, CUDA, ROCm devices
- [ ] Support standard `WhisperModel` and `BatchedInferencePipeline`
- [ ] Model caching with LRU eviction (reuse existing `_model_cache`)
- [ ] Device-specific compute type validation
- **Files**: `api/backends/faster_whisper_backend.py`
- **Test**: `tests/unit/test_faster_whisper_backend.py` — mock WhisperModel, BatchedInferencePipeline
- **Effort**: 2h
- **Acceptance**: All unit tests pass, supports both standard and batched modes

### 2.4 Create WhisperCppBackend

- [ ] Create `api/backends/whisper_cpp_backend.py`
- [ ] Use `whispercpp` library (whispercpp.py bindings)
- [ ] Support float16, int8 compute types
- [ ] Does NOT support batched inference (raise NotImplementedError)
- [ ] Model caching with LRU eviction
- [ ] Normalize output to faster-whisper format (segments_iter, info_dict)
- **Files**: `api/backends/whisper_cpp_backend.py`
- **Test**: `tests/unit/test_whisper_cpp_backend.py` — mock Whisper
- **Effort**: 2h
- **Acceptance**: All unit tests pass, transcribe_batched raises NotImplementedError

### 2.5 Create TranscriptionStrategy

- [ ] Create `api/transcription_strategy.py`
- [ ] `@dataclass TranscriptionStrategy` with all configuration fields
- [ ] `auto_configure()` classmethod with full configuration matrix
- [ ] CUDA/ROCm: faster-whisper + float16 + batched
- [ ] MPS: whisper-cpp + int8/float16 + parallel chunking (4 workers)
- [ ] CPU: faster-whisper + int8 + parallel chunking for audio > 90s
- [ ] Quality presets override beam_size and temperature
- [ ] Explicit parameters override presets
- **Files**: `api/transcription_strategy.py`
- **Test**: `tests/unit/test_transcription_strategy.py` — 10+ tests covering full matrix
- **Effort**: 2h
- **Acceptance**: All auto_configure combinations produce correct strategies

### 2.6 Enable DeviceDetector backend class tests

- [ ] Re-run previously skipped backend class tests in `test_device_detector.py`
- [ ] Now that both backends exist, all tests should pass
- **Files**: `tests/unit/test_device_detector.py`
- **Effort**: 15min
- **Acceptance**: `pytest tests/unit/test_device_detector.py -v` all PASS

---

## Phase 3: Parallel Chunking + BatchedInferencePipeline Integration (4-6h)

### 3.1 Add parallel chunk processing to chunking.py

- [ ] Add `transcribe_audio_parallel()` function
- [ ] Use `ThreadPoolExecutor` with configurable `max_workers`
- [ ] Split audio into chunks, process in parallel
- [ ] Merge results sorted by timestamp
- [ ] Clean up temporary chunk files
- [ ] Fallback to whole-file transcription if no chunks
- **Files**: `api/chunking.py`
- **Test**: `tests/unit/test_chunking_parallel.py` — mock split, transcribe_chunk, merge
- **Effort**: 2h
- **Acceptance**: Parallel processing calls transcribe for each chunk, results ordered by timestamp

### 3.2 Create TranscriptionService orchestration layer

- [ ] Create `api/transcription_service.py`
- [ ] `TranscriptionService` class coordinates DeviceDetector, Strategy, backends, chunking
- [ ] Start with skeleton (init + basic structure)
- [ ] Full pipeline integration in Phase 5
- **Files**: `api/transcription_service.py`
- **Test**: `tests/unit/test_transcription_service.py` — initialization test
- **Effort**: 1h
- **Acceptance**: Service initializes, imports all dependencies

---

## Phase 4: Docker Deployment + E2E Tests (4-6h)

### 4.1 Create CUDA Dockerfile

- [ ] Create `Dockerfile.cuda` based on `nvidia/cuda:12.4.1-runtime-ubuntu22.04`
- [ ] Install system deps (ffmpeg, tesseract, poppler, etc.)
- [ ] Install uv, create venv
- [ ] Install faster-whisper + PyTorch CUDA
- [ ] Pre-download base model
- **Files**: `Dockerfile.cuda`
- **Effort**: 1h
- **Acceptance**: Dockerfile syntax valid, build starts successfully

### 4.2 Create ROCm Dockerfile

- [ ] Create `Dockerfile.rocm` based on `rocm/dev-ubuntu-22.04:6.1`
- [ ] Match CUDA image structure with ROCm-specific packages
- [ ] Install PyTorch ROCm
- **Files**: `Dockerfile.rocm`
- **Effort**: 30min
- **Acceptance**: Dockerfile syntax valid

### 4.3 Update docker-compose.yml with GPU profiles

- [ ] Add `api-gpu` service with `profiles: ["gpu"]`
- [ ] Add NVIDIA device reservation
- [ ] Set `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`
- **Files**: `docker-compose.yml`
- **Effort**: 30min
- **Acceptance**: `docker compose --profile gpu config` succeeds

### 4.4 Create Mac setup script

- [ ] Create `scripts/setup_mac.sh`
- [ ] Validate Apple Silicon architecture
- [ ] Install whisper-cpp via Homebrew
- [ ] Install whispercpp Python bindings
- **Files**: `scripts/setup_mac.sh`
- **Effort**: 30min
- **Acceptance**: Script runs on Apple Silicon, installs dependencies

### 4.5 Create test fixtures

- [ ] Create `tests/fixtures/` directory
- [ ] Create `tests/fixtures/generate_fixtures.py`
- [ ] Generate: 5s_silence.wav, 5s_speech.wav, 120s_speech.wav
- **Files**: `tests/fixtures/generate_fixtures.py`
- **Effort**: 30min
- **Acceptance**: `python tests/fixtures/generate_fixtures.py` creates all fixtures

### 4.6 Create E2E test for audio transcription

- [ ] Create `tests/e2e/test_audio_transcribe.py`
- [ ] Test short audio transcription returns markdown
- [ ] Test quality_mode parameter
- [ ] Test JSON return format
- [ ] Add `api_client` fixture to `tests/conftest.py`
- **Files**: `tests/e2e/test_audio_transcribe.py`, `tests/conftest.py`
- **Effort**: 1h
- **Acceptance**: E2E tests pass with running API

---

## Phase 5: Hybrid Strategy + Full E2E + Documentation (4-8h)

### 5.1 Add auto model selection to API endpoints

- [ ] When `model_size == "auto"`, call `get_audio_duration()` + `get_recommended_model()`
- [ ] Apply to all 3 transcription endpoints
- **Files**: `api/main.py`
- **Test**: `tests/unit/test_auto_model_selection.py`
- **Effort**: 1h
- **Acceptance**: Auto model selection works for all duration ranges

### 5.2 Add performance monitoring metadata

- [ ] Extend metadata dict in `transcribe_audio()` and `transcribe_audio_chunked()`
- [ ] Add: backend, device, compute_type, use_batched, quality_mode, beam_size, batch_size, cpu_threads, max_workers
- [ ] Add timing: model_load_time_ms, transcription_time_ms, chunking_time_ms, merging_time_ms
- [ ] Add: vad_filtered_duration_ms, realtime_factor, audio_duration_seconds
- **Files**: `api/whisper_transcribe.py`, `api/main.py`
- **Effort**: 1h
- **Acceptance**: Response metadata includes all new fields

### 5.3 Create remaining E2E tests

- [ ] `tests/e2e/test_video_transcribe.py` — video endpoint
- [ ] `tests/e2e/test_youtube_transcribe.py` — youtube endpoint
- [ ] `tests/e2e/test_quality_modes.py` — all 3 quality modes
- [ ] `tests/e2e/test_api_compatibility.py` — backward compatibility
- **Files**: 4 new E2E test files
- **Effort**: 2h
- **Acceptance**: All E2E tests pass

### 5.4 Update pyproject.toml dependencies

- [ ] Update `faster-whisper` to `>=1.2.0`
- [ ] Add `whispercpp>=2.0.0`
- [ ] Add optional deps: cuda, rocm, apple-silicon, dev
- [ ] Configure pytest markers
- **Files**: `pyproject.toml`
- **Effort**: 30min
- **Acceptance**: `uv sync` succeeds with all deps

### 5.5 Update documentation

- [ ] Update `README.md` — add GPU deployment section
- [ ] Update `docs/API_REFERENCE.md` — document new API parameters
- [ ] Update `CONFIG_GUIDE.md` — add new environment variables
- **Files**: `README.md`, `docs/API_REFERENCE.md`, `CONFIG_GUIDE.md`
- **Effort**: 1h
- **Acceptance**: Documentation reflects all changes

---

## Acceptance Checklist

### Functional
- [ ] All 6 optimization plans implemented
- [ ] Multi-device support: CPU, CUDA, ROCm, MPS
- [ ] Backend abstraction layer with Protocol
- [ ] Parallel chunking for CPU/MPS
- [ ] BatchedInferencePipeline for GPU
- [ ] Auto model selection
- [ ] Quality mode presets (speed/balanced/quality)
- [ ] All 3 API endpoints updated with new parameters
- [ ] Backward compatible — existing API calls work

### Performance
- [ ] CPU threads: 4 → 8
- [ ] VAD params: more aggressive filtering
- [ ] Chunk beam_size: 5 → 1 (default)
- [ ] Parallel chunking: up to 4 workers
- [ ] BatchedInferencePipeline: batch_size=8 (GPU)

### Testing
- [ ] 10+ unit test files
- [ ] 4+ integration test files
- [ ] 5+ E2E test files
- [ ] Test fixtures generated
- [ ] >80% coverage on new code

### Docker
- [ ] CPU image builds
- [ ] CUDA Dockerfile created
- [ ] ROCm Dockerfile created
- [ ] docker-compose GPU profile works
- [ ] Mac setup script works

---

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/whisper-performance-optimization

# Phase 1 commits
git add api/constants.py tests/unit/test_constants.py
git commit -m "feat(whisper): update constants for performance optimization"

git add api/main.py tests/unit/test_api_params.py
git commit -m "feat(whisper): add optimization parameters to API endpoints"

# Phase 2 commits
git add api/backends/ tests/unit/test_backend_protocol.py
git commit -m "feat(whisper): add TranscriptionBackend Protocol"

git add api/device_detector.py tests/unit/test_device_detector.py
git commit -m "feat(whisper): add DeviceDetector for hardware auto-detection"

git add api/backends/faster_whisper_backend.py tests/unit/test_faster_whisper_backend.py
git commit -m "feat(whisper): add FasterWhisperBackend for CPU/CUDA/ROCm"

git add api/backends/whisper_cpp_backend.py tests/unit/test_whisper_cpp_backend.py
git commit -m "feat(whisper): add WhisperCppBackend for Apple Silicon"

git add api/transcription_strategy.py tests/unit/test_transcription_strategy.py
git commit -m "feat(whisper): add TranscriptionStrategy auto-configuration"

# Phase 3 commits
git add api/chunking.py tests/unit/test_chunking_parallel.py
git commit -m "feat(whisper): add parallel chunk processing"

git add api/transcription_service.py tests/unit/test_transcription_service.py
git commit -m "feat(whisper): add TranscriptionService skeleton"

# Phase 4 commits
git add Dockerfile.cuda Dockerfile.rocm docker-compose.yml
git commit -m "feat(whisper): add GPU Dockerfiles and docker-compose profiles"

git add scripts/setup_mac.sh
git commit -m "feat(whisper): add Apple Silicon setup script"

git add tests/fixtures/ tests/e2e/test_audio_transcribe.py tests/conftest.py
git commit -m "test(whisper): add test fixtures and E2E audio test"

# Phase 5 commits
git add api/main.py tests/unit/test_auto_model_selection.py
git commit -m "feat(whisper): enable auto model selection"

git add api/whisper_transcribe.py api/main.py
git commit -m "feat(whisper): add performance monitoring metadata"

git add tests/e2e/
git commit -m "test(whisper): add remaining E2E tests"

git add pyproject.toml
git commit -m "deps(whisper): update dependencies for multi-device support"

git add README.md docs/
git commit -m "docs(whisper): update documentation for multi-device support"

# Final merge
git checkout main
git merge feature/whisper-performance-optimization
git tag v0.6.0
```

---

## Rollback Plan

If optimization causes issues:

```bash
# Option 1: Git revert
git revert <commit-hash>

# Option 2: Use backup Docker image
docker tag oh-my-markitdown:latest oh-my-markitdown:backup
docker compose down
# Rebuild with old Dockerfile
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-05 | Kimhsiao | Initial task document |
