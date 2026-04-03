# API Reference

Complete reference for MarkItDown API endpoints.

## Table of Contents

- [Endpoints Overview](#endpoints-overview)
- [File Conversion](#file-conversion)
- [YouTube Transcription](#youtube-transcription)
- [Audio Transcription](#audio-transcription)
- [Language Support](#language-support)
- [Configuration](#configuration)
- [System Management](#system-management)

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API Homepage (version info) |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/formats` | View supported file formats |
| `GET` | `/api/v1/ocr-languages` | View OCR language support |
| `GET` | `/api/v1/config` | View current configuration |
| `GET` | `/api/v1/device-info` | Get compute device information (CPU/GPU) |
| `POST` | `/api/v1/convert` | Upload file and convert |
| `POST` | `/api/v1/convert/youtube` | YouTube video transcription (Faster-Whisper) |
| `POST` | `/api/v1/convert/audio` | Audio file transcription (Faster-Whisper) |
| `POST` | `/api/v1/convert/video` | Video file transcription (Faster-Whisper) |
| `POST` | `/api/v1/convert/url` | Convert from URL |
| `POST` | `/api/v1/convert/clean-html` | Extract clean content from URL or HTML file using Readability |
| `GET` | `/api/v1/convert/languages` | Supported transcription languages |
| `GET` | `/api/v1/admin/storage` | Query storage usage |
| `POST` | `/api/v1/admin/cleanup` | Clean up temporary files |
| `GET` | `/api/v1/admin/models` | Get model cache information |
| `DELETE` | `/api/v1/admin/models` | Clear all cached models |
| `GET` | `/api/v1/admin/queue` | Get queue status |
| `GET` | `/docs` | Swagger UI interactive docs |
| `GET` | `/redoc` | ReDoc documentation |

---

## File Conversion

### POST /api/v1/convert

Upload a file and convert it to Markdown.

#### Request

**Content-Type:** `multipart/form-data`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | File to convert |
| `enable_plugins` | Boolean | No | `false` | Enable OCR for images/scanned PDFs |
| `ocr_lang` | String | No | `chi_tra+eng` | OCR language code (combine with `+`) |
| `return_format` | String | No | `markdown` | Response format: `markdown` or `json` |
| `clean_html` | Boolean | No | `true` | Use Readability to clean HTML files before conversion |

#### Examples

**Basic conversion:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

**With OCR:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md
```

**JSON response:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf" \
  -F "return_format=json" \
  -o response.json
```

#### Response

**Markdown format:**
- Content-Type: `text/markdown`
- Direct Markdown content
- Headers include original filename, conversion time, OCR language

**JSON format:**
```json
{
  "success": true,
  "filename": "document.pdf",
  "file_size": 123456,
  "conversion_time": "2026-03-13T14:30:00",
  "ocr_language": "chi_tra+eng",
  "content": "# Markdown Content...",
  "metadata": {
    "type": "pdf",
    "source": "file",
    "title": "Document Title",
    "author": "Author"
  }
}
```

---

### POST /api/v1/convert/url

Convert content from a URL.

**Note:** YouTube URLs are not supported in this endpoint. Use `/api/v1/convert/youtube` instead.

#### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | String | Yes | Web URL (YouTube URLs will return error) |
| `return_format` | String | No | Response format: `markdown` or `json` |
| `clean_html` | Boolean | No | Use Readability to clean webpage HTML before conversion (default: `true`) |

#### Example

```bash
curl -X POST "http://localhost:51083/api/v1/convert/url?url=https://example.com/article" \
  -o output.md
```

---

## Clean HTML Extraction (New in v0.5.0)

### POST /api/v1/convert/clean-html

Extract clean article content from a URL or uploaded HTML file using Readability algorithm, then convert to Markdown.

Provide either `url` (query parameter) or `file` (multipart form). File takes precedence if both given.

#### Request — URL Mode

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | String | Yes | - | URL to extract content from |

#### Example — URL Mode

```bash
curl -X POST "http://localhost:51083/api/v1/convert/clean-html?url=https://example.com/article" \
  -o output.md
```

#### Request — File Mode

**Content-Type:** `multipart/form-data`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | HTML file to extract content from |

#### Example — File Mode

```bash
curl -X POST "http://localhost:51083/api/v1/convert/clean-html" \
  -F "file=@page.html" \
  -o output.md
```

---

## YouTube Transcription

### POST /api/v1/convert/youtube

Transcribe YouTube videos using hybrid strategy for optimal speed.

**Hybrid Strategy:**
- **Fast Path:** Uses YouTube subtitles if available (2-5 seconds)
- **Slow Path:** Falls back to Faster-Whisper (30-60 minutes for 1hr video)

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | String | Yes | - | YouTube video URL |
| `language` | String | No | `zh` | Language code (zh, en, ja, ko, etc.) |
| `model_size` | String | No | `base` | Model size: tiny, base, small, medium, large |
| `return_format` | String | No | `markdown` | Response format |
| `include_metadata` | Boolean | No | `true` | Include video metadata |
| `prefer_subtitles` | Boolean | No | `true` | Prefer YouTube subtitles if available (faster) |
| `fast_mode` | Boolean | No | `false` | Enable fast mode optimizations for Whisper |
| `device` | String | No | `auto` | Compute device: `cpu`, `cuda`, `mps`, `auto` |
| `cpu_threads` | Integer | No | `0` | CPU threads (0 = auto-detect, max 8) |
| `vad_enabled` | Boolean | No | `true` | Enable Voice Activity Detection |

#### Performance Parameters (New in v0.3.0)

| Parameter | Description |
|-----------|-------------|
| `device` | Compute device selection. `auto` detects GPU if available (CUDA > MPS > CPU). Use `cuda` for NVIDIA GPU, `mps` for Apple Silicon, `cpu` for CPU-only. |
| `cpu_threads` | Number of CPU threads for transcription. `0` auto-detects based on CPU cores (capped at 8). Higher values may improve speed on multi-core systems. |
| `vad_enabled` | Voice Activity Detection filters out silence, reducing processing time by 20-40%. Disable for audio with no silence or if experiencing issues. |

#### Model Sizes

| Model | Speed | Accuracy | Memory |
|-------|-------|----------|--------|
| `tiny` | Fastest | Fair | ~500MB |
| `base` | Fast | Good | ~1GB |
| `small` | Medium | Very Good | ~2GB |
| `medium` | Slow | Excellent | ~5GB |
| `large` | Slowest | Best | ~10GB |

**Recommended:** `base` for balance of speed and accuracy.

#### Examples

**Chinese transcription (auto-detect subtitles):**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&language=zh" \
  -o transcript.md
```

**Force Whisper transcription (skip subtitle check):**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&prefer_subtitles=false" \
  -o transcript.md
```

**Fast mode for quicker Whisper transcription:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&prefer_subtitles=false&fast_mode=true" \
  -o transcript.md
```

**English with JSON output:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&language=en&return_format=json" \
  -o response.json
```

#### Response Metadata

The response includes metadata with transcription source information:

```json
{
  "success": true,
  "title": "Video Title",
  "transcript": "...",
  "metadata": {
    "source": "youtube_subtitles",
    "language": "zh-Hant",
    "is_auto_generated": false,
    "duration": 1800,
    "processing_time_ms": 2500
  }
}
```

**Metadata Fields:**
- `source`: `"youtube_subtitles"` or `"whisper"`
- `language`: Language code used
- `is_auto_generated`: Whether subtitles are auto-generated (for subtitle source)
- `duration`: Video duration in seconds
- `processing_time_ms`: Processing time in milliseconds

---

## Audio Transcription

### POST /api/v1/convert/audio

Upload audio files and transcribe using Faster-Whisper.

#### Supported Formats

MP3, WAV, M4A, FLAC, OGG, etc.

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Audio file to transcribe |
| `language` | String | No | `auto` | Language code (`auto` for auto-detect) |
| `model_size` | String | No | `base` | Model size: tiny, base, small, medium, large |
| `return_format` | String | No | `markdown` | Response format |
| `include_timestamps` | Boolean | No | `false` | Include timestamps in transcript |
| `device` | String | No | `auto` | Compute device: `cpu`, `cuda`, `mps`, `auto` |
| `cpu_threads` | Integer | No | `0` | CPU threads (0 = auto-detect, max 8) |
| `vad_enabled` | Boolean | No | `true` | Enable Voice Activity Detection |

#### Example

```bash
curl -X POST "http://localhost:51083/api/v1/convert/audio?language=zh" \
  -F "file=@audio.mp3" \
  -o transcript.md
```

**With GPU acceleration:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/audio?language=zh&device=cuda" \
  -F "file=@audio.mp3" \
  -o transcript.md
```

---

## Language Support

### GET /api/v1/convert/languages

List all supported transcription languages.

#### Example

```bash
curl http://localhost:51083/api/v1/convert/languages
```

#### Response

```json
{
  "supported_languages": {
    "zh": "中文",
    "zh-TW": "繁體中文",
    "en": "英文",
    "ja": "日文",
    "ko": "韓文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文"
  },
  "models": {
    "tiny": {"speed": "最快", "accuracy": "一般", "memory": "~500MB"},
    "base": {"speed": "快", "accuracy": "好", "memory": "~1GB"},
    "small": {"speed": "中等", "accuracy": "很好", "memory": "~2GB"},
    "medium": {"speed": "慢", "accuracy": "極好", "memory": "~5GB"},
    "large": {"speed": "最慢", "accuracy": "最佳", "memory": "~10GB"}
  },
  "recommended": {
    "fast": "tiny",
    "balanced": "base",
    "accurate": "small"
  }
}
```

---

### GET /api/v1/ocr-languages

View OCR language support.

#### Example

```bash
curl http://localhost:51083/api/v1/ocr-languages
```

#### Response

```json
{
  "supported_languages": {
    "chi_sim": "Simplified Chinese",
    "chi_tra": "Traditional Chinese",
    "eng": "English",
    "jpn": "Japanese",
    "kor": "Korean",
    "tha": "Thai",
    "vie": "Vietnamese"
  },
  "default": "chi_tra+eng",
  "usage": "Combine multiple languages with + symbol, e.g., chi_tra+eng+jpn",
  "examples": [
    {"code": "chi_tra", "name": "Traditional Chinese"},
    {"code": "chi_sim", "name": "Simplified Chinese"},
    {"code": "chi_tra+eng", "name": "Traditional Chinese + English (Default)"}
  ]
}
```

---

## Device Information

### GET /api/v1/device-info

Get compute device information for Whisper transcription.

This endpoint helps users understand what compute resources are available and choose the optimal device for transcription.

#### Example

```bash
curl http://localhost:51083/api/v1/device-info
```

#### Response

```json
{
  "success": true,
  "data": {
    "device": "cpu",
    "cuda_available": false,
    "mps_available": false,
    "cpu_count": 8,
    "recommended_compute_type": "int8"
  },
  "metadata": {},
  "request_id": "req-xxx"
}
```

**With NVIDIA GPU available:**
```json
{
  "success": true,
  "data": {
    "device": "cuda",
    "cuda_available": true,
    "cuda_device_name": "NVIDIA GeForce RTX 3080",
    "cuda_device_count": 1,
    "cuda_memory_gb": 10.0,
    "mps_available": false,
    "cpu_count": 16,
    "recommended_compute_type": "float16"
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `device` | String | Detected device: `cpu`, `cuda`, or `mps` |
| `cuda_available` | Boolean | Whether NVIDIA CUDA is available |
| `mps_available` | Boolean | Whether Apple Silicon MPS is available |
| `cpu_count` | Integer | Number of CPU cores |
| `recommended_compute_type` | String | Recommended compute type: `int8` (CPU), `float16` (GPU) |
| `cuda_device_name` | String | GPU name (if CUDA available) |
| `cuda_device_count` | Integer | Number of CUDA devices |
| `cuda_memory_gb` | Float | GPU memory in GB |

#### Device Selection Guide

| Device | Use Case | Performance |
|--------|----------|-------------|
| `cpu` | Default, no GPU available | Baseline speed |
| `cuda` | NVIDIA GPU (RTX series) | 4-10x faster than CPU |
| `mps` | Apple Silicon (M1/M2/M3) | 2-4x faster than CPU |
| `auto` | Auto-detect best available | Recommended |

---

## Configuration

### GET /api/v1/config

View current configuration.

#### Example

```bash
curl http://localhost:51083/api/v1/config
```

#### Response

```json
{
  "api": {
    "version": "0.3.1",
    "debug": false,
    "max_upload_size": 52428800,
    "max_upload_size_mb": 50
  },
  "ocr": {
    "default_language": "chi_tra+eng",
    "plugins_enabled_by_default": false,
    "supported_languages": {
      "chi_sim": "Simplified Chinese",
      "chi_tra": "Traditional Chinese",
      "eng": "English",
      "jpn": "Japanese",
      "kor": "Korean",
      "tha": "Thai",
      "vie": "Vietnamese"
    }
  },
  "openai": {
    "configured": true,
    "model": "gpt-4o",
    "base_url": "https://api.openai.com/v1"
  }
}
```

---

## System Management

### GET /api/v1/admin/storage

Query storage usage for temporary files.

**Requires:** `X-API-Key` header if API_KEY is configured.

#### Example

```bash
curl http://localhost:51083/api/v1/admin/storage
```

#### Response

```json
{
  "total_bytes": 104857600,
  "total_mb": 100.0,
  "breakdown": {
    "youtube_audio": {"bytes": 52428800, "mb": 50.0, "files": 5},
    "ocr_temp": {"bytes": 10485760, "mb": 10.0, "files": 20},
    "uploads": {"bytes": 41943040, "mb": 40.0, "files": 3}
  },
  "models": {
    "cached_count": 2,
    "estimated_memory_mb": 2000
  }
}
```

---

### POST /api/v1/admin/cleanup

Clean up temporary files.

**Requires:** `X-API-Key` header if API_KEY is configured.

#### Request

```json
{
  "targets": ["temp", "whisper", "all"],
  "dry_run": false
}
```

| Target | Description |
|--------|-------------|
| `temp` | Clean temporary files (youtube audio, OCR temp, uploads) |
| `whisper` | Clear Whisper model cache |
| `all` | Clean both temp and whisper |

#### Example

```bash
curl -X POST http://localhost:51083/api/v1/admin/cleanup \
  -H "Content-Type: application/json" \
  -d '{"targets": ["all"], "dry_run": false}'
```

---

### GET /api/v1/admin/models

Get Whisper model cache information.

#### Example

```bash
curl http://localhost:51083/api/v1/admin/models
```

---

### DELETE /api/v1/admin/models

Clear all cached models.

#### Example

```bash
curl -X DELETE http://localhost:51083/api/v1/admin/models
```

---

### GET /api/v1/admin/queue

Get current queue status.

#### Response

```json
{
  "current_processing": 1,
  "max_concurrent": 3,
  "queue_length": 2,
  "queue": [
    {"request_id": "abc123", "status": "processing", "started_at": "2026-03-17T10:00:00"},
    {"request_id": "def456", "status": "queued", "queued_at": "2026-03-17T10:01:00"}
  ]
}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File size exceeds maximum allowed size",
    "details": {
      "max_size_mb": 50,
      "actual_size_mb": 75
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILE_FORMAT` | 400 | Unsupported file format |
| `FILE_TOO_LARGE` | 413 | File exceeds max upload size |
| `INVALID_URL` | 400 | Invalid or unsupported URL |
| `YOUTUBE_DOWNLOAD_FAILED` | 500 | Failed to download YouTube video |
| `TRANSCRIPTION_FAILED` | 500 | Speech transcription failed |
| `OCR_FAILED` | 500 | OCR processing failed |
| `CONVERSION_FAILED` | 500 | General conversion failure |
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `QUEUE_FULL` | 503 | Request queue is full |

---

## Interactive Documentation

After starting the service, visit:

- **Swagger UI**: http://localhost:51083/docs
- **ReDoc**: http://localhost:51083/redoc