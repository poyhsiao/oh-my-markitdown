# Video Conversion Performance Improvement Plan

**Document ID:** PERF-001  
**Created:** 2026-03-19  
**Author:** AI Assistant  
**Status:** Approved  
**Target API:** `/api/v1/convert/video`

**Related Documents:**
- [Requirements](./2026-03-19-video-performance-requirements.md)
- [Design](./2026-03-19-video-performance-design.md)
- [Tasks](./2026-03-19-video-performance-tasks.md)

---

## Executive Summary

This document outlines performance optimization strategies for the video-to-text conversion API. The current bottleneck analysis shows that **Whisper transcription accounts for ~80%** of total processing time, making it the primary target for optimization.

---

## Table of Contents

1. [Current Performance Analysis](#1-current-performance-analysis)
2. [Bottleneck Breakdown](#2-bottleneck-breakdown)
3. [Optimization Strategies](#3-optimization-strategies)
4. [Implementation Roadmap](#4-implementation-roadmap)
5. [Risk Assessment](#5-risk-assessment)
6. [Success Metrics](#6-success-metrics)

---

## 1. Current Performance Analysis

### 1.1 Processing Pipeline

```
┌─────────────────┐
│  File Upload    │  ~5% of total time
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audio Extract  │  ~10% of total time
│  (ffmpeg)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Whisper        │  ~80% of total time ← PRIMARY BOTTLENECK
│  Transcription  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Format Output  │  ~3% of total time
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cleanup Files  │  ~2% of total time
└─────────────────┘
```

### 1.2 Current Configuration

| Component | Current Setting | Location |
|-----------|-----------------|----------|
| Device | CPU | `WHISPER_DEVICE=cpu` |
| Compute Type | int8 | `WHISPER_COMPUTE_TYPE=int8` |
| CPU Threads | 4 | `whisper_transcribe.py:139` |
| Audio Format | MP3 (128K) | `whisper_transcribe.py:231` |
| VAD Filter | Enabled (500ms) | `whisper_transcribe.py:167-168` |

### 1.3 Baseline Performance

| Video Duration | Processing Time | Ratio |
|----------------|-----------------|-------|
| 1 minute | ~2-3 minutes | 2-3x |
| 5 minutes | ~8-12 minutes | 1.6-2.4x |
| 30 minutes | ~40-60 minutes | 1.3-2x |
| 1 hour | ~70-120 minutes | 1.2-2x |

---

## 2. Bottleneck Breakdown

### 2.1 Whisper Transcription (80% - Critical)

**Root Causes:**
- CPU-only processing (no GPU acceleration)
- Conservative model size (base)
- Suboptimal VAD parameters
- Audio quality higher than needed for speech recognition

**Affected Code:**
- `api/whisper_transcribe.py:132-188` - `transcribe_audio()`
- `api/whisper_transcribe.py:93-129` - `get_model()`

### 2.2 Audio Extraction (10% - Moderate)

**Root Causes:**
- MP3 encoding overhead (compression)
- Stereo audio (not needed for speech)
- High sample rate (48kHz, but 16kHz sufficient)

**Affected Code:**
- `api/whisper_transcribe.py:513-552` - `extract_audio_from_video()`

### 2.3 File I/O (7% - Low)

**Root Causes:**
- Temporary file writes before processing
- Sequential upload → process workflow

**Affected Code:**
- `api/main.py:724-728` - File save logic

### 2.4 Format Output (3% - Negligible)

Pure text processing, minimal optimization potential.

---

## 3. Optimization Strategies

### 3.1 GPU Acceleration (High Impact)

**Priority:** P0 (Highest)  
**Expected Speedup:** 4-10x  
**Effort:** Medium

| Platform | Implementation | Speedup | Requirements |
|----------|----------------|---------|--------------|
| NVIDIA CUDA | `WHISPER_DEVICE=cuda` | 4-10x | NVIDIA GPU, CUDA toolkit |
| Apple Silicon | `WHISPER_DEVICE=mps` | 2-4x | M1/M2/M3 Mac |
| Multiple GPUs | Distributed processing | Linear scaling | Multiple GPU setup |

**Configuration Changes:**
```bash
# Environment variables
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

# Dockerfile additions (for CUDA)
FROM nvidia/cuda:11.8-runtime
RUN pip install faster-whisper[cuda]
```

**Files to Modify:**
- `Dockerfile` - Add CUDA/cuDNN support
- `docker-compose.yml` - Add GPU resource limits
- `.env.example` - Add GPU configuration options

---

### 3.2 Audio Preprocessing Optimization (Medium Impact)

**Priority:** P1  
**Expected Speedup:** 30-50% (extraction phase)  
**Effort:** Low

**Current:**
```python
# whisper_transcribe.py:535-546
result = subprocess.run([
    "ffmpeg", "-i", video_path,
    "-vn",
    "-acodec", "libmp3lame",  # MP3 encoding
    "-y", output_audio_path
])
```

**Optimized:**
```python
# Recommended parameters
result = subprocess.run([
    "ffmpeg", "-i", video_path,
    "-vn",                    # No video
    "-ac", "1",               # Mono channel
    "-ar", "16000",           # 16kHz sample rate
    "-acodec", "pcm_s16le",   # WAV (no compression)
    "-y", output_audio_path
])
```

**Rationale:**
- **16kHz sample rate:** Sufficient for speech (Whisper trained on 16kHz)
- **Mono channel:** Stereo unnecessary for speech recognition
- **WAV/PCM:** Eliminates MP3 encoding overhead

**Files to Modify:**
- `api/whisper_transcribe.py:513-552`

---

### 3.3 VAD Parameter Tuning (Low Impact, Easy Win)

**Priority:** P1  
**Expected Speedup:** 10-20%  
**Effort:** Very Low

**Current:**
```python
# whisper_transcribe.py:167-168
vad_filter=True,
vad_parameters=dict(min_silence_duration_ms=500)
```

**Optimized:**
```python
vad_filter=True,
vad_parameters=dict(
    min_silence_duration_ms=300,  # More aggressive silence skipping
    speech_pad_ms=200,            # Reduce padding
    threshold=0.6                 # Higher sensitivity
)
```

**Files to Modify:**
- `api/whisper_transcribe.py:163-169`
- `api/constants.py` - Add VAD configuration constants

---

### 3.4 CPU Threading Optimization (Low Impact)

**Priority:** P2  
**Expected Speedup:** ~30%  
**Effort:** Very Low

**Current:**
```python
# whisper_transcribe.py:139
cpu_threads: int = 4
```

**Optimized:**
```python
import os

# Auto-detect optimal thread count
DEFAULT_CPU_THREADS = min(os.cpu_count() or 4, 8)

# Or allow configuration via environment
CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", DEFAULT_CPU_THREADS))
```

**Files to Modify:**
- `api/whisper_transcribe.py:97-98, 139-140`
- `.env.example` - Add `WHISPER_CPU_THREADS`

---

### 3.5 Model Selection Strategy (Medium Impact)

**Priority:** P2  
**Expected Speedup:** Varies  
**Effort:** Low

**Recommended Adaptive Strategy:**

| Video Duration | Recommended Model | Rationale |
|----------------|-------------------|-----------|
| < 2 minutes | `tiny` | Fast, sufficient accuracy for short clips |
| 2-10 minutes | `base` | Balanced speed/accuracy |
| 10-30 minutes | `small` | Better accuracy for longer content |
| > 30 minutes | `small` or `medium` | Prioritize accuracy |

**Implementation:**
```python
def get_recommended_model(duration_seconds: float) -> str:
    if duration_seconds < 120:
        return "tiny"
    elif duration_seconds < 600:
        return "base"
    elif duration_seconds < 1800:
        return "small"
    else:
        return "medium"
```

**Files to Modify:**
- `api/whisper_transcribe.py` - Add model selection function
- `api/main.py:697` - Integrate adaptive selection

---

### 3.6 Streaming Pipeline (High Effort, High Impact)

**Priority:** P3 (Future)  
**Expected Speedup:** Reduced perceived latency  
**Effort:** High

**Current Flow:**
```
Upload Complete → Save File → Extract Audio → Transcribe → Return
```

**Optimized Flow:**
```
Upload Stream → Pipe to ffmpeg → Pipe to Whisper → Stream Output
```

**Benefits:**
- Eliminates temporary file I/O
- Starts processing before upload completes
- Reduces total wall-clock time

**Files to Modify:**
- `api/main.py:693-767` - Complete refactor of endpoint
- `api/whisper_transcribe.py` - Add streaming support

---

### 3.7 Distributed Processing (High Effort)

**Priority:** P3 (Future)  
**Expected Speedup:** Linear with worker count  
**Effort:** Very High

**Architecture:**
```
                    ┌─────────────┐
                    │   API       │
                    │   Gateway   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐┌─────▼─────┐┌─────▼─────┐
        │  Worker 1 ││  Worker 2 ││  Worker 3 │
        │  (GPU)    ││  (GPU)    ││  (GPU)    │
        └───────────┘└───────────┘└───────────┘
```

**Components:**
- Task queue (Celery/RQ)
- Worker pool with GPU instances
- Result aggregation service

---

## 4. Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| VAD parameter tuning | P1 | Very Low | 10-20% |
| CPU threading config | P2 | Very Low | ~30% |
| Audio format optimization | P1 | Low | 30-50% |

**Deliverables:**
- Environment variable for CPU threads
- Optimized ffmpeg parameters
- VAD configuration options

### Phase 2: GPU Support (1-2 weeks)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| CUDA Docker image | P0 | Medium | 4-10x |
| GPU detection logic | P0 | Low | - |
| Fallback to CPU | P0 | Low | - |

**Deliverables:**
- Multi-stage Dockerfile with CUDA support
- Automatic device detection
- Configuration documentation

### Phase 3: Architecture Improvements (2-4 weeks)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Streaming pipeline | P3 | High | Latency reduction |
| Model caching optimization | P2 | Medium | Faster cold start |
| Result caching | P2 | Low | Eliminate re-processing |

**Deliverables:**
- Streaming transcription endpoint
- Warm-up endpoint for model preloading
- Cache layer integration

### Phase 4: Scale-Out (Future)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Distributed workers | P3 | Very High | Linear scaling |
| Auto-scaling | P3 | High | Cost optimization |
| Video segmentation | P3 | High | Parallel processing |

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU memory overflow | Medium | High | Implement chunking, memory monitoring |
| CUDA compatibility issues | Low | Medium | Multiple CUDA version support |
| Audio format incompatibility | Low | Low | Fallback to MP3 encoding |
| Quality degradation | Medium | Medium | A/B testing, quality metrics |

### 5.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Increased infrastructure cost | High | Medium | Auto-scaling, spot instances |
| Docker image size increase | Medium | Low | Multi-stage builds |
| Cold start latency | Medium | Medium | Model preloading, warm pools |

---

## 6. Success Metrics

### 6.1 Performance KPIs

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Processing ratio (1min video) | 2-3x | < 1x | Time comparison |
| Processing ratio (5min video) | 1.6-2.4x | < 0.5x | Time comparison |
| GPU utilization | 0% | > 80% | nvidia-smi |
| Memory usage | ~2GB | < 4GB | Docker stats |
| Queue wait time | N/A | < 30s | Concurrency manager |

### 6.2 Quality KPIs

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Word Error Rate (WER) | Baseline | < 5% degradation | Test dataset |
| Transcription completeness | 100% | 100% | Manual review |
| Timestamp accuracy | ±0.5s | ±0.3s | Spot check |

### 6.3 Testing Requirements

Before deployment, validate:

1. **Performance Tests**
   - Benchmark with 1/5/30/60 minute videos
   - Measure processing time ratio
   - Monitor resource utilization

2. **Quality Tests**
   - WER comparison (current vs. optimized)
   - Edge case handling (silence, music, multiple speakers)
   - Language detection accuracy

3. **Integration Tests**
   - API endpoint functionality
   - Error handling
   - Cleanup verification

---

## Appendix A: Configuration Reference

### Environment Variables

```bash
# GPU Configuration
WHISPER_DEVICE=cpu          # cpu | cuda | mps
WHISPER_COMPUTE_TYPE=int8   # int8 | float16 | float32

# Performance Tuning
WHISPER_CPU_THREADS=4       # CPU thread count
WHISPER_MODEL=base          # Default model size

# Timeouts (seconds)
YOUTUBE_INFO_TIMEOUT=300
YOUTUBE_DOWNLOAD_TIMEOUT=600
AUDIO_EXTRACT_TIMEOUT=300
```

### Docker Compose GPU Configuration

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.gpu
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

---

## Appendix B: Related Files

| File | Purpose |
|------|---------|
| `api/whisper_transcribe.py` | Core transcription logic |
| `api/main.py:693-767` | Video conversion endpoint |
| `api/constants.py` | Configuration constants |
| `api/subtitles.py` | Output formatting |
| `Dockerfile` | Container configuration |
| `docker-compose.yml` | Service orchestration |

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-19 | 1.0.0 | Initial document creation |
| 2026-03-19 | 1.1.0 | Added requirements, design, and tasks documents |

---

**Document Status:** Approved - Ready for Implementation  
**Next Review Date:** TBD  
**Owner:** Development Team