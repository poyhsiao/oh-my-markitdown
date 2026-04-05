# Whisper Multi-Device Performance Optimization — Requirements

**Document ID**: 2026-04-05-whisper-performance-requirements  
**Created**: 2026-04-05  
**Author**: Kimhsiao  
**Status**: Approved  
**Priority**: High  
**Related**: 
- Spec: `docs/superpowers/specs/2026-04-05-whisper-multi-device-performance-optimization.md`
- Plan: `docs/plans/2026-04-05-whisper-multi-device-performance-optimization.md`
- Survey: `docs/survey/whisper-performance-optimization.md`

---

## 1. Executive Summary

Comprehensive optimization of the Whisper transcription pipeline implementing all 6 optimization plans from the survey document, with multi-device backend abstraction supporting Apple Silicon (MPS), NVIDIA CUDA, AMD ROCm, and CPU. Developed TDD-style with full unit, integration, and E2E test coverage.

---

## 2. Background

### 2.1 Current State

The project uses `faster-whisper` for local speech-to-text with:
- CPU-only processing (default: 4 threads, int8)
- Sequential chunk processing for long audio files
- Hardcoded beam_size=5, temperature=0.0 in chunking
- No GPU acceleration in default deployment
- Single backend (faster-whisper) with no MPS support

### 2.2 Problem Statement

1. **Performance bottleneck**: 1-hour audio takes 30-50 minutes on CPU with base model
2. **Sequential chunking**: Long audio files processed one chunk at a time
3. **No device optimization**: Same code path for all hardware
4. **Apple Silicon unsupported**: faster-whisper has no MPS backend
5. **No quality/speed tradeoff**: Users cannot choose between speed and accuracy

### 2.3 Survey Findings

The survey document (`docs/survey/whisper-performance-optimization.md`) identified 6 optimization plans with combined potential of 5-10x CPU acceleration and 10-15x GPU acceleration.

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: Parameter Tuning (Plan 1)

**Requirement**: Update default constants for immediate performance gains.

**Acceptance Criteria**:
- [ ] `DEFAULT_CPU_THREADS` changed from 4 to 8
- [ ] `DEFAULT_VAD_MIN_SILENCE_MS` changed from 300 to 500
- [ ] `DEFAULT_VAD_THRESHOLD` changed from 0.6 to 0.5
- [ ] `DEFAULT_VAD_SPEECH_PAD_MS` changed from 200 to 300
- [ ] `DEFAULT_CHUNK_BEAM_SIZE` changed from 5 to 1
- [ ] All new constants defined in `api/constants.py`

#### FR-2: API Parameter Exposure (Plan 2)

**Requirement**: Expose optimization parameters via API endpoints.

**Acceptance Criteria**:
- [ ] All 3 transcription endpoints accept `quality_mode` (speed/balanced/quality)
- [ ] All 3 transcription endpoints accept `beam_size` (overrides quality_mode)
- [ ] All 3 transcription endpoints accept `temperature` (overrides quality_mode)
- [ ] All 3 transcription endpoints accept `use_batched` (auto-detect if None)
- [ ] All 3 transcription endpoints accept `batch_size` (default: 8)
- [ ] All 3 transcription endpoints accept `device` (auto/cpu/cuda/mps/rocm)
- [ ] All 3 transcription endpoints accept `cpu_threads` (auto-detect if None)
- [ ] `model_size` default changed to `"auto"` for automatic model selection
- [ ] All new parameters are optional with backward-compatible defaults
- [ ] Existing API calls without new parameters work identically

#### FR-3: Backend Abstraction Layer (Plan 4)

**Requirement**: Create unified backend interface supporting multiple hardware accelerators.

**Acceptance Criteria**:
- [ ] `TranscriptionBackend` Protocol defined with: name, device, supported_compute_types, supports_batched, load_model(), transcribe(), transcribe_batched(), unload()
- [ ] `FasterWhisperBackend` implements Protocol for CPU, CUDA, ROCm
- [ ] `FasterWhisperBackend` supports `BatchedInferencePipeline` from faster-whisper >= 1.2.0
- [ ] `WhisperCppBackend` implements Protocol for MPS (Apple Silicon)
- [ ] `WhisperCppBackend` uses `whispercpp>=2.0.0` library
- [ ] `DeviceDetector` detects CUDA, ROCm, MPS, CPU in priority order
- [ ] `DeviceDetector.get_backend_class()` routes mps to WhisperCppBackend, others to FasterWhisperBackend
- [ ] `TranscriptionStrategy.auto_configure()` selects optimal configuration based on device, duration, quality_mode

#### FR-4: Parallel Chunking (Plan 3)

**Requirement**: Replace sequential chunk processing with parallel processing.

**Acceptance Criteria**:
- [ ] CPU/MPS chunking uses `ThreadPoolExecutor` with configurable max_workers
- [ ] `max_workers` defaults to 4, capped at 8
- [ ] Results merged and sorted by timestamp regardless of completion order
- [ ] GPU devices use `BatchedInferencePipeline` instead of parallel chunking
- [ ] Temporary chunk files cleaned up after processing

#### FR-5: GPU Deployment (Plan 5)

**Requirement**: Provide Docker images for GPU-accelerated deployment.

**Acceptance Criteria**:
- [ ] `Dockerfile.cuda` based on `nvidia/cuda:12.4.1-runtime-ubuntu22.04`
- [ ] `Dockerfile.rocm` based on `rocm/dev-ubuntu-22.04:6.1`
- [ ] `docker-compose.yml` has `gpu` profile with NVIDIA device reservation
- [ ] `scripts/setup_mac.sh` installs whisper-cpp for Apple Silicon
- [ ] GPU image pre-downloads base model at build time

#### FR-6: Hybrid Strategy (Plan 6)

**Requirement**: Auto-select optimal configuration based on hardware and audio characteristics.

**Acceptance Criteria**:
- [ ] `model_size="auto"` selects model based on audio duration (existing logic, now enabled)
- [ ] `device="auto"` uses DeviceDetector to pick best available hardware
- [ ] `use_batched=None` auto-enables for GPU, disables for CPU
- [ ] Quality presets control beam_size and temperature
- [ ] Explicit parameters override auto-configuration
- [ ] Metadata includes all configuration details for monitoring

### 3.2 Non-Functional Requirements

#### NFR-1: Performance

| Metric | Current | Target (CPU) | Target (GPU) |
|--------|---------|-------------|-------------|
| 1-hour audio, base model | 30-50 min | 5-10 min | 2-4 min |
| Real-time factor | ~0.5-0.8x | < 0.5x | < 0.2x |
| Model load time (cached) | 5-30s | < 1s | < 1s |
| VAD filter rate | 20-60% | 30-70% | 30-70% |

#### NFR-2: Test Coverage

| Test Type | Coverage Target |
|-----------|----------------|
| Unit tests | All new code paths, all backends, all strategies |
| Integration tests | Full pipeline with tiny model |
| E2E tests | All 3 API endpoints, all quality modes |
| Backward compatibility | Existing API calls unchanged |

#### NFR-3: Backward Compatibility

- All existing API endpoints work without modification
- All environment variables continue to work
- Default behavior matches current behavior (with performance improvements)
- No breaking changes to response format

#### NFR-4: Docker

- CPU image size increase < 50MB
- GPU images build successfully
- docker-compose profiles work independently

---

## 4. Technical Design

See spec document: `docs/superpowers/specs/2026-04-05-whisper-multi-device-performance-optimization.md`

### 4.1 Architecture Summary

```
API Endpoints → TranscriptionService → TranscriptionStrategy → ChunkingEngine → TranscriptionBackend
```

### 4.2 Backend Routing

| Detected Device | Backend | Compute Type | Batched | Parallel Workers |
|----------------|---------|-------------|---------|-----------------|
| CUDA | FasterWhisperBackend | float16 | Yes | N/A |
| ROCm | FasterWhisperBackend | float16 | Yes | N/A |
| MPS | WhisperCppBackend | int8/float16 | No | 4 |
| CPU | FasterWhisperBackend | int8 | No | 4 (audio > 90s) |

### 4.3 Quality Presets

| Preset | beam_size | temperature | Use Case |
|--------|-----------|-------------|----------|
| speed | 1 | 0.0 | Fast transcription, acceptable accuracy loss |
| balanced | 3 | 0.0 | Default: good speed/accuracy balance |
| quality | 5 | 0.0 | Maximum accuracy, slower |

---

## 5. Dependencies

### 5.1 Package Updates

| Package | Current | New | Purpose |
|---------|---------|-----|---------|
| `faster-whisper` | `*` | `>=1.2.0` | BatchedInferencePipeline stable |
| `whispercpp` | N/A | `>=2.0.0` | Apple Silicon support |
| `pytest` | N/A | `>=8.0` | Test framework |
| `pytest-asyncio` | N/A | `>=0.23` | Async test support |
| `httpx` | N/A | `>=0.27` | E2E API testing |
| `pytest-mock` | N/A | `>=3.12` | Test mocking |

### 5.2 Optional Dependencies

| Extra | Packages |
|-------|----------|
| `cuda` | `torch>=2.4.0` |
| `rocm` | `torch>=2.4.0` |
| `apple-silicon` | `whispercpp>=2.0.0` |
| `dev` | `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `pytest-mock` |

---

## 6. Implementation Plan

See plan document: `docs/plans/2026-04-05-whisper-multi-device-performance-optimization.md`

### Phase Summary

| Phase | Focus | Tasks | Est. Hours |
|-------|-------|-------|-----------|
| 1 | Foundation (Plans 1+2) | 1-4 | 4-6 |
| 2 | Backend Abstraction (Plan 4) | 5-10 | 6-10 |
| 3 | Parallel Chunking (Plan 3) | 11-12 | 4-6 |
| 4 | Docker + E2E (Plan 5) | 13-18 | 4-6 |
| 5 | Hybrid + Docs (Plan 6) | 19-23 | 4-8 |
| **Total** | | **23 tasks** | **22-36** |

---

## 7. Testing Requirements

### 7.1 Unit Tests (Mock Models)

- [ ] `test_constants.py` — Updated defaults and quality presets
- [ ] `test_api_params.py` — API parameter validation
- [ ] `test_backend_protocol.py` — Protocol definition
- [ ] `test_device_detector.py` — Device detection logic
- [ ] `test_faster_whisper_backend.py` — FasterWhisperBackend methods
- [ ] `test_whisper_cpp_backend.py` — WhisperCppBackend methods
- [ ] `test_transcription_strategy.py` — auto_configure matrix
- [ ] `test_chunking_parallel.py` — Parallel chunking correctness
- [ ] `test_transcription_service.py` — Service orchestration
- [ ] `test_auto_model_selection.py` — Model selection logic

### 7.2 Integration Tests (Real tiny Model)

- [ ] `test_transcribe_pipeline.py` — Full pipeline
- [ ] `test_backend_switching.py` — Backend switching
- [ ] `test_batched_inference.py` — BatchedInferencePipeline
- [ ] `test_chunking.py` — Chunking with real audio

### 7.3 E2E Tests (Full API, CPU Only)

- [ ] `test_audio_transcribe.py` — Audio endpoint
- [ ] `test_video_transcribe.py` — Video endpoint
- [ ] `test_youtube_transcribe.py` — YouTube endpoint
- [ ] `test_quality_modes.py` — All quality modes
- [ ] `test_api_compatibility.py` — Backward compatibility

---

## 8. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| whispercpp compatibility issues | Medium | Medium | Fallback to faster-whisper CPU |
| ROCm CTranslate2 build complexity | Medium | Medium | Pre-built Docker image |
| BatchedInferencePipeline memory | Low | Low | Configurable batch_size, default 8 |
| Parallel chunking memory pressure | Low | Low | max_workers capped at 4 |
| API backward compatibility break | Low | High | All new params optional with defaults |

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CPU speedup (1hr audio) | 5-10x | Benchmark before/after |
| GPU speedup (1hr audio) | 10-15x | Benchmark before/after |
| Test coverage | >80% new code | pytest-cov |
| E2E tests passing | 100% | CI pipeline |
| Backward compatibility | 0 breaking changes | E2E compat tests |
| Docker build success | CPU + GPU images | docker compose build |

---

## 10. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Kimhsiao | 2026-04-05 | - |
| Reviewer | - | - | - |
| Approver | - | - | - |

---

## 11. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-05 | Kimhsiao | Initial draft |
