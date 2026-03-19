# Video Conversion Performance Requirements

**Document ID:** PERF-REQ-001  
**Created:** 2026-03-19  
**Author:** AI Assistant  
**Status:** Approved  
**Related Design:** video-performance-design.md

---

## 1. Overview

### 1.1 Purpose

Optimize the performance of all Whisper-based transcription APIs to achieve significant speedup (4-10x on GPU, 50-80% on CPU) while maintaining transcription quality.

### 1.2 Scope

This optimization applies to all Whisper transcription endpoints:

- `/api/v1/convert/video` - Video file conversion
- `/api/v1/convert/audio` - Audio file conversion
- `/api/v1/convert/youtube` - YouTube URL conversion

### 1.3 Current Baseline

| Video Duration | Processing Time (CPU) | Ratio |
|----------------|----------------------|-------|
| 1 minute | 2-3 minutes | 2-3x |
| 5 minutes | 8-12 minutes | 1.6-2.4x |
| 30 minutes | 40-60 minutes | 1.3-2x |
| 1 hour | 70-120 minutes | 1.2-2x |

---

## 2. Functional Requirements

### 2.1 GPU Support

**REQ-001: Multi-Platform GPU Support**

The system shall support GPU acceleration for:

| Platform | Device Type | Expected Speedup |
|----------|-------------|------------------|
| NVIDIA | CUDA | 4-10x |
| Apple Silicon | MPS | 2-4x |

**Acceptance Criteria:**
- Auto-detect available GPU (CUDA > MPS > CPU priority)
- Fall back to CPU if GPU unavailable
- Validate GPU availability before use

### 2.2 CPU Optimization

**REQ-002: Automatic Thread Detection**

The system shall automatically detect and configure optimal CPU thread count.

**Acceptance Criteria:**
- Detect CPU core count via `os.cpu_count()`
- Limit maximum threads to 8
- Allow manual override via environment variable

**REQ-003: VAD Parameter Tuning**

The system shall use optimized VAD (Voice Activity Detection) parameters.

| Parameter | Current | Optimized |
|-----------|---------|-----------|
| `min_silence_duration_ms` | 500 | 300 |
| `threshold` | - | 0.6 |
| `speech_pad_ms` | - | 200 |

**Acceptance Criteria:**
- Reduce processing time by 10-20%
- Maintain transcription quality

### 2.3 Audio Extraction

**REQ-004: Optimized Audio Format**

The system shall extract audio in WAV/PCM format instead of MP3.

**Audio Parameters:**
- Sample rate: 16kHz (Whisper native)
- Channels: 1 (mono)
- Codec: `pcm_s16le` (no compression)

**Acceptance Criteria:**
- Reduce audio extraction time by 30-50%
- No quality degradation for transcription

**REQ-005: FFmpeg Multi-threading**

The system shall use multi-threaded FFmpeg for audio extraction.

**Acceptance Criteria:**
- Use 4 threads by default
- Reduce extraction time by 20-30%

### 2.4 Model Selection

**REQ-006: Adaptive Model Selection**

The system shall automatically select optimal model size based on media duration.

| Duration | Recommended Model |
|----------|-------------------|
| < 2 minutes | tiny |
| 2-10 minutes | base |
| 10-30 minutes | small |
| > 30 minutes | medium |

**Acceptance Criteria:**
- Auto-select when `model_size=auto`
- Allow manual override via API parameter
- Provide model selection function for API layer

### 2.5 Configuration Management

**REQ-007: Hybrid Configuration**

The system shall support configuration via:

1. **Environment variables** - Default values for deployment
2. **API parameters** - Per-request override

**Priority:** API Parameter > Environment Variable > Default

**Acceptance Criteria:**
- All new parameters have sensible defaults
- Backward compatible with existing API calls
- Document all configuration options

---

## 3. Non-Functional Requirements

### 3.1 Performance

**NFR-001: Processing Time Targets**

| Device | Target Ratio |
|--------|-------------|
| CPU | < 1.5x media duration |
| CUDA | < 0.5x media duration |
| MPS | < 1x media duration |

**NFR-002: Quality Preservation**

- Word Error Rate (WER) degradation: < 5%
- Transcription completeness: 100%
- Timestamp accuracy: ±0.3s

### 3.2 Compatibility

**NFR-003: Backward Compatibility**

- Existing API calls without new parameters shall work unchanged
- Default behavior matches current implementation
- No breaking changes to response format

**NFR-004: Platform Support**

| Platform | Support Level |
|----------|---------------|
| Linux (Docker) | Full |
| macOS (local) | Full (including MPS) |
| Windows | Not tested |

### 3.3 Reliability

**NFR-005: Graceful Degradation**

- GPU unavailability shall not cause errors
- Automatic fallback to CPU
- Clear error messages for configuration issues

---

## 4. API Requirements

### 4.1 New Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device` | string | auto | cpu / cuda / mps / auto |
| `model_size` | string | auto | tiny / base / small / medium / large / auto |
| `cpu_threads` | int | auto | CPU thread count (0 = auto) |
| `vad_enabled` | bool | true | Enable VAD filtering |

### 4.2 New Endpoints

**REQ-008: Device Info Endpoint**

```
GET /api/v1/device-info
```

**Response:**
```json
{
  "device": "cuda",
  "cuda_available": true,
  "cuda_device_name": "NVIDIA GeForce RTX 3080",
  "cuda_device_count": 1,
  "cuda_memory_gb": 10.0,
  "mps_available": false,
  "cpu_count": 8,
  "recommended_compute_type": "float16"
}
```

---

## 5. Environment Variables

### 5.1 New Variables

```bash
# GPU Configuration
WHISPER_DEVICE=auto              # cpu | cuda | mps | auto
WHISPER_COMPUTE_TYPE=auto        # int8 | float16 | float32 | auto

# CPU Performance
WHISPER_CPU_THREADS=0            # 0 = auto detect

# VAD Configuration
WHISPER_VAD_ENABLED=true
WHISPER_VAD_MIN_SILENCE_MS=300
WHISPER_VAD_THRESHOLD=0.6

# Model Selection
WHISPER_MODEL_AUTO_SELECTION=true
```

### 5.2 Existing Variables (Modified)

```bash
# Existing - behavior updated
WHISPER_MODEL=auto               # Now supports "auto"
WHISPER_DEVICE=auto              # Now supports "auto" and "mps"
```

---

## 6. Testing Requirements

### 6.1 Performance Testing

**TEST-001: Benchmark Tests**

- Measure processing time for 1/5/30 minute videos
- Compare CPU, CUDA, MPS performance
- Verify performance targets

### 6.2 Quality Testing

**TEST-002: Transcription Quality**

- WER comparison between CPU and GPU
- Quality comparison between model sizes
- Edge case handling (silence, music, multiple speakers)

### 6.3 Integration Testing

**TEST-003: API Functionality**

- All endpoints with new parameters
- Backward compatibility verification
- Error handling scenarios

---

## 7. Constraints

### 7.1 Technical Constraints

- C1: Must not require code changes from existing users
- C2: Must support both Docker and local deployment
- C3: GPU support is optional, not mandatory
- C4: No additional paid dependencies

### 7.2 Resource Constraints

- C5: CPU memory limit: < 4GB
- C6: GPU memory: depends on model size (1-10GB)
- C7: Docker image size: minimal increase

---

## 8. Acceptance Criteria

### 8.1 Must Have

- [ ] GPU acceleration (CUDA + MPS) with auto-detection
- [ ] CPU thread auto-detection
- [ ] VAD parameter optimization
- [ ] Audio format optimization (WAV/PCM)
- [ ] Adaptive model selection
- [ ] Hybrid configuration (env + API params)
- [ ] Backward compatibility
- [ ] Benchmark tests

### 8.2 Should Have

- [ ] `/device-info` endpoint
- [ ] Performance documentation
- [ ] Migration guide

### 8.3 Nice to Have

- [ ] Streaming pipeline (Phase 3)
- [ ] Distributed processing (Phase 4)

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU memory overflow | Medium | High | Memory monitoring, chunking |
| Quality degradation | Medium | Medium | Quality tests, A/B comparison |
| CUDA compatibility | Low | Medium | Multi-version support |
| Docker image bloat | Medium | Low | Multi-stage builds |

---

## 10. Glossary

| Term | Definition |
|------|------------|
| VAD | Voice Activity Detection - filters non-speech segments |
| CUDA | NVIDIA's GPU computing platform |
| MPS | Metal Performance Shaders - Apple Silicon GPU |
| WER | Word Error Rate - transcription quality metric |
| WAV/PCM | Uncompressed audio format |

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-19 | 1.0.0 | Initial requirements document |

---

**Document Status:** Approved  
**Next Review Date:** After implementation  
**Owner:** Development Team