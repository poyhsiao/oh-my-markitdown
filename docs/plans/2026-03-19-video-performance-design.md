# Video Conversion Performance Design

**Document ID:** PERF-DESIGN-001  
**Created:** 2026-03-19  
**Author:** AI Assistant  
**Status:** Approved  
**Related Requirements:** video-performance-requirements.md

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Web UI    │  │   CLI       │  │  API Client │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          └────────────────┴────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/v1/convert/video                                │   │
│  │  /api/v1/convert/audio                                │   │
│  │  /api/v1/convert/youtube                              │   │
│  │  /api/v1/device-info (NEW)                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Transcription Layer                       │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │ Device Utils  │  │    Config     │  │   Constants   │   │
│  │   (NEW)       │  │  (Modified)   │  │  (Modified)   │   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘   │
│          │                  │                  │            │
│          └──────────────────┴──────────────────┘            │
│                             │                                │
│                             ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Whisper Transcribe Core                  │   │
│  │  • transcribe_audio() (MODIFIED)                      │   │
│  │  • extract_audio_from_video() (MODIFIED)              │   │
│  │  • get_model() (MODIFIED)                             │   │
│  │  • get_recommended_model() (NEW)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │   FFmpeg      │  │  Faster-      │  │  Docker       │   │
│  │  (Modified)   │  │  Whisper      │  │  (Modified)   │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Backward Compatibility** - Existing API behavior unchanged, new parameters have defaults
2. **Progressive Enhancement** - CPU works by default, GPU accelerates automatically
3. **Configuration Layers** - Environment variables as defaults, API parameters can override
4. **Fail-Safe** - GPU unavailability falls back to CPU gracefully

---

## 2. Component Design

### 2.1 Device Detection Module (NEW)

**File:** `api/device_utils.py`

**Purpose:** Auto-detect optimal compute device and provide GPU information.

```python
from typing import Literal
import os
import torch

DeviceType = Literal["cpu", "cuda", "mps", "auto"]

def detect_device() -> DeviceType:
    """
    Auto-detect optimal compute device.
    Priority: CUDA > MPS > CPU
    """
    try:
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    
    try:
        if (hasattr(torch.backends, 'mps') and 
            torch.backends.mps.is_available() and
            torch.backends.mps.is_built()):
            return "mps"
    except Exception:
        pass
    
    return "cpu"

def get_compute_type_for_device(device: str) -> str:
    """Get recommended compute type for device."""
    mapping = {
        "cuda": "float16",
        "mps": "float16", 
        "cpu": "int8"
    }
    return mapping.get(device, "int8")

def get_device_info() -> dict:
    """Get detailed device information."""
    info = {
        "device": detect_device(),
        "cuda_available": False,
        "mps_available": False,
        "cpu_count": os.cpu_count() or 4,
        "recommended_compute_type": "int8"
    }
    
    # CUDA details
    try:
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
            info["cuda_device_count"] = torch.cuda.device_count()
            info["cuda_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
            )
    except Exception:
        pass
    
    # MPS details
    try:
        if (hasattr(torch.backends, 'mps') and 
            torch.backends.mps.is_available()):
            info["mps_available"] = True
            info["mps_built"] = torch.backends.mps.is_built()
    except Exception:
        pass
    
    info["recommended_compute_type"] = get_compute_type_for_device(info["device"])
    return info

def validate_device(device: str) -> str:
    """Validate and return effective device."""
    if device == "auto":
        return detect_device()
    
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but not available")
    
    if device == "mps":
        if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
            raise ValueError("MPS requested but not available")
    
    return device
```

### 2.2 Configuration Module (MODIFIED)

**File:** `api/config.py`

**Changes:** Add `PerformanceConfig` dataclass.

```python
from dataclasses import dataclass
from typing import Optional
from api.device_utils import detect_device, validate_device, get_compute_type_for_device

@dataclass
class PerformanceConfig:
    """Performance-related configuration."""
    
    # GPU Configuration
    device: str = "auto"              # cpu | cuda | mps | auto
    compute_type: str = "auto"        # int8 | float16 | float32 | auto
    
    # CPU Performance
    cpu_threads: int = 0              # 0 = auto detect
    
    # VAD Configuration
    vad_enabled: bool = True
    vad_min_silence_ms: int = 300
    vad_threshold: float = 0.6
    vad_speech_pad_ms: int = 200
    
    # Model Selection
    auto_model_selection: bool = True
    
    def get_effective_device(self) -> str:
        """Get effective device (resolve 'auto')."""
        return validate_device(self.device)
    
    def get_effective_compute_type(self) -> str:
        """Get effective compute type."""
        if self.compute_type == "auto":
            return get_compute_type_for_device(self.get_effective_device())
        return self.compute_type
    
    def get_effective_threads(self) -> int:
        """Get effective CPU thread count."""
        if self.cpu_threads <= 0:
            return min(os.cpu_count() or 4, 8)
        return min(self.cpu_threads, 8)

@dataclass
class WhisperConfig:
    """Whisper configuration (existing, modified)."""
    model: str = "base"
    device: str = "auto"
    compute_type: str = "auto"
    default_language: str = "auto"
    performance: PerformanceConfig = None
    
    def __post_init__(self):
        if self.performance is None:
            self.performance = PerformanceConfig()
```

### 2.3 Constants Module (MODIFIED)

**File:** `api/constants.py`

**Changes:** Add VAD, audio, and model selection constants.

```python
# ===== VAD Parameters =====
DEFAULT_VAD_MIN_SILENCE_MS = 300
DEFAULT_VAD_THRESHOLD = 0.6
DEFAULT_VAD_SPEECH_PAD_MS = 200

# ===== Audio Extraction Parameters =====
AUDIO_SAMPLE_RATE = 16000           # 16kHz (Whisper native)
AUDIO_CHANNELS = 1                  # Mono
AUDIO_CODEC = "pcm_s16le"           # WAV/PCM
AUDIO_FFMPEG_THREADS = 4            # FFmpeg thread count

# ===== CPU Threading =====
MAX_CPU_THREADS = 8
MIN_CPU_THREADS = 1
DEFAULT_CPU_THREADS = 4

# ===== Model Selection Thresholds (seconds) =====
MODEL_SELECTION_THRESHOLDS = {
    "tiny": 120,         # < 2 minutes
    "base": 600,         # 2-10 minutes
    "small": 1800,       # 10-30 minutes
    "medium": float("inf")  # > 30 minutes
}

# ===== Compute Type by Device =====
COMPUTE_TYPE_BY_DEVICE = {
    "cpu": "int8",
    "cuda": "float16",
    "mps": "float16"
}
```

### 2.4 Whisper Transcribe Module (MODIFIED)

**File:** `api/whisper_transcribe.py`

#### 2.4.1 Model Selection Function (NEW)

```python
def get_recommended_model(duration_seconds: float) -> str:
    """
    Get recommended model size based on media duration.
    
    Args:
        duration_seconds: Media duration in seconds
        
    Returns:
        Recommended model size (tiny/base/small/medium)
    """
    if duration_seconds < MODEL_SELECTION_THRESHOLDS["tiny"]:
        return "tiny"
    elif duration_seconds < MODEL_SELECTION_THRESHOLDS["base"]:
        return "base"
    elif duration_seconds < MODEL_SELECTION_THRESHOLDS["small"]:
        return "small"
    return "medium"
```

#### 2.4.2 Audio Extraction (MODIFIED)

```python
def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None,
    threads: int = AUDIO_FFMPEG_THREADS
) -> str:
    """
    Extract audio from video file.
    
    Optimizations:
    - WAV/PCM format (no compression overhead)
    - 16kHz sample rate (Whisper native)
    - Mono channel
    - Multi-threaded decoding
    
    Args:
        video_path: Path to video file
        output_audio_path: Output path (optional, temp file if None)
        threads: FFmpeg thread count
        
    Returns:
        Path to extracted audio file
    """
    if not output_audio_path:
        output_audio_path = tempfile.mktemp(suffix=".wav")
    
    cmd = [
        "ffmpeg",
        "-threads", str(threads),     # Multi-threaded decoding
        "-i", video_path,
        "-vn",                        # No video
        "-ac", str(AUDIO_CHANNELS),   # Mono
        "-ar", str(AUDIO_SAMPLE_RATE),# 16kHz
        "-acodec", AUDIO_CODEC,       # WAV/PCM
        "-y", output_audio_path
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=AUDIO_EXTRACT_TIMEOUT
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")
    
    return output_audio_path
```

#### 2.4.3 Transcribe Function (MODIFIED)

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
    word_timestamps: bool = False
) -> Tuple[str, List[dict]]:
    """
    Transcribe audio file with Whisper.
    
    Args:
        audio_path: Path to audio file
        language: Language code or "auto" for detection
        model_size: Model size (None = use config default)
        device: Compute device (None = use config default)
        compute_type: Compute type (None = use config default)
        cpu_threads: CPU threads (None = auto detect)
        vad_enabled: Enable VAD filtering
        vad_params: Custom VAD parameters
        word_timestamps: Enable word-level timestamps
        
    Returns:
        Tuple of (transcription_text, segments_list)
    """
    config = get_config().whisper
    
    # Resolve effective values
    effective_device = device or config.performance.get_effective_device()
    effective_compute_type = compute_type or config.performance.get_effective_compute_type()
    effective_threads = cpu_threads or config.performance.get_effective_threads()
    effective_model = model_size or config.model
    
    # VAD parameters
    if vad_enabled and vad_params is None:
        vad_params = {
            "min_silence_duration_ms": config.performance.vad_min_silence_ms,
            "threshold": config.performance.vad_threshold,
            "speech_pad_ms": config.performance.vad_speech_pad_ms
        }
    
    # Get or load model
    model = get_model(
        model_size=effective_model,
        device=effective_device,
        compute_type=effective_compute_type,
        cpu_threads=effective_threads
    )
    
    # Transcribe
    segments, info = model.transcribe(
        audio_path,
        language=None if language == "auto" else language,
        vad_filter=vad_enabled,
        vad_parameters=vad_params if vad_enabled else None,
        word_timestamps=word_timestamps
    )
    
    # Format output
    transcription = " ".join([seg.text for seg in segments])
    segment_list = [
        {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text
        }
        for seg in segments
    ]
    
    return transcription, segment_list
```

---

## 3. API Design

### 3.1 New Endpoint: Device Info

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

### 3.2 Modified Endpoints

All transcription endpoints accept new parameters:

```
POST /api/v1/convert/video
POST /api/v1/convert/audio
POST /api/v1/convert/youtube
```

**New Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device` | string | auto | cpu / cuda / mps / auto |
| `model_size` | string | auto | tiny / base / small / medium / large / auto |
| `cpu_threads` | int | 0 | 0 = auto detect |
| `vad_enabled` | bool | true | Enable VAD filtering |

### 3.3 Parameter Resolution

```
API Parameter > Environment Variable > Default Value
```

**Resolution Logic:**

```python
def resolve_transcribe_config(
    device: Optional[str] = None,
    model_size: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: Optional[bool] = None,
    duration_seconds: Optional[float] = None
) -> dict:
    """Resolve transcription configuration with priority."""
    config = get_config().whisper
    
    effective_device = device or config.performance.get_effective_device()
    effective_threads = cpu_threads or config.performance.get_effective_threads()
    
    # Model selection
    if model_size and model_size != "auto":
        effective_model = model_size
    elif config.performance.auto_model_selection and duration_seconds:
        effective_model = get_recommended_model(duration_seconds)
    else:
        effective_model = config.model
    
    return {
        "device": effective_device,
        "model_size": effective_model,
        "cpu_threads": effective_threads,
        "vad_enabled": vad_enabled if vad_enabled is not None else config.performance.vad_enabled,
        "compute_type": config.performance.get_effective_compute_type(),
        "vad_params": {
            "min_silence_duration_ms": config.performance.vad_min_silence_ms,
            "threshold": config.performance.vad_threshold,
            "speech_pad_ms": config.performance.vad_speech_pad_ms
        }
    }
```

---

## 4. Docker Design

### 4.1 Multi-Stage Dockerfile

```dockerfile
# ===== CPU Base Image =====
FROM python:3.12-slim AS cpu-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    exiftool \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-eng \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    tesseract-ocr-tha \
    tesseract-ocr-vie \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== CUDA Image =====
FROM nvidia/cuda:11.8-runtime-ubuntu22.04 AS cuda-base

RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    poppler-utils \
    exiftool \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-eng \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    tesseract-ocr-tha \
    tesseract-ocr-vie \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install faster-whisper[cuda]

# ===== Default Image (CPU) =====
FROM cpu-base AS default

COPY . /app
WORKDIR /app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 Docker Compose Configuration

```yaml
services:
  # CPU Version (Default)
  markitdown-api:
    build:
      context: .
      dockerfile: Dockerfile
      target: default
    environment:
      - WHISPER_DEVICE=auto
      - WHISPER_COMPUTE_TYPE=auto

  # GPU Version (Optional)
  markitdown-api-gpu:
    profiles:
      - gpu
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

## 5. Data Flow

### 5.1 Video Transcription Flow

```
┌─────────────┐
│   Upload    │
│   Video     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Resolve Configuration        │
│  API Params > Env Vars > Defaults    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Detect Device                │
│  CUDA > MPS > CPU                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Extract Audio (FFmpeg)            │
│  • WAV/PCM 16kHz mono                │
│  • Multi-threaded                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Select Model (if auto)            │
│  Based on video duration             │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Transcribe with Whisper           │
│  • VAD filtering                     │
│  • Optimized parameters              │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Format & Return Response          │
└─────────────────────────────────────┘
```

---

## 6. Error Handling

### 6.1 Device Unavailable

```python
try:
    device = validate_device(requested_device)
except ValueError as e:
    # Log warning and fall back to CPU
    logger.warning(f"Device validation failed: {e}, falling back to CPU")
    device = "cpu"
```

### 6.2 GPU Memory Issues

```python
try:
    result = model.transcribe(audio_path, ...)
except torch.cuda.OutOfMemoryError:
    # Fall back to CPU
    logger.warning("GPU OOM, falling back to CPU")
    model = get_model(model_size, device="cpu", ...)
    result = model.transcribe(audio_path, ...)
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Test | File | Purpose |
|------|------|---------|
| Device detection | `test_device_utils.py` | Verify CUDA/MPS/CPU detection |
| Config resolution | `test_config.py` | Verify parameter priority |
| Model selection | `test_whisper_transcribe.py` | Verify adaptive selection |

### 7.2 Performance Tests

| Test | Purpose | Target |
|------|---------|--------|
| CPU benchmark | Measure processing time | < 1.5x duration |
| CUDA benchmark | Measure GPU speedup | < 0.5x duration |
| MPS benchmark | Measure Apple Silicon speedup | < 1x duration |
| Audio extraction | Measure format optimization | > 30% improvement |

### 7.3 Quality Tests

| Test | Purpose | Target |
|------|---------|--------|
| WER comparison | CPU vs GPU quality | < 5% degradation |
| Model comparison | Accuracy across models | Varies by use case |

---

## 8. Migration Guide

### 8.1 For Existing Users

**No changes required.** All new parameters have defaults that maintain current behavior.

### 8.2 For New Users

**Enable GPU acceleration:**

```bash
# Environment variable
export WHISPER_DEVICE=cuda

# Or in .env file
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

**API parameter override:**

```bash
curl -X POST "http://localhost:51083/api/v1/convert/video" \
  -F "file=@video.mp4" \
  -F "device=cuda" \
  -F "model_size=auto"
```

---

## 9. Performance Projections

### 9.1 Expected Improvements

| Component | CPU Improvement | CUDA Speedup | MPS Speedup |
|-----------|-----------------|--------------|-------------|
| VAD tuning | 10-20% | 10-20% | 10-20% |
| Thread optimization | ~30% | - | - |
| Audio format | 30-50% | 30-50% | 30-50% |
| GPU acceleration | - | 4-10x | 2-4x |
| **Combined** | **50-80%** | **4-10x** | **2-4x** |

### 9.2 Target Performance

| Video Duration | CPU (Current) | CPU (Optimized) | CUDA | MPS |
|----------------|---------------|-----------------|------|-----|
| 1 min | 2-3 min | 1-1.5 min | < 30s | < 1 min |
| 5 min | 8-12 min | 4-6 min | < 2.5 min | < 5 min |
| 30 min | 40-60 min | 20-30 min | < 15 min | < 30 min |

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-19 | 1.0.0 | Initial design document |

---

**Document Status:** Approved  
**Next Review Date:** After implementation  
**Owner:** Development Team