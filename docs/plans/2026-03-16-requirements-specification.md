# Requirements Specification

**Project:** oh-my-markitdown  
**Version:** 1.0.0  
**Date:** 2026-03-16  
**Status:** Approved

---

## Table of Contents

1. [Overview](#1-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [API Endpoint Design](#3-api-endpoint-design)
4. [CLI Command Design](#4-cli-command-design)
5. [Environment Variables](#5-environment-variables)
6. [Script Design](#6-script-design)
7. [Documentation Structure](#7-documentation-structure)
8. [Implementation Priority](#8-implementation-priority)
9. [Glossary](#9-glossary)

---

## 1. Overview

### 1.1 Project Description

**oh-my-markitdown** is a file conversion and speech transcription API service that supports:

- Document conversion (PDF, DOCX, PPTX, images, etc.) to Markdown with OCR support
- YouTube video transcription using Faster-Whisper
- Audio file transcription (MP3, WAV, M4A, etc.)
- Video file transcription (MP4, MKV, WebM, etc.)
- Unified URL processing endpoint
- Cache and temporary file cleanup

### 1.2 Core Features

| Feature | Description |
|---------|-------------|
| File Conversion | PDF/DOCX/PPTX/Images → Markdown (with OCR) |
| YouTube Transcription | YouTube URL → Audio → Whisper → Markdown/SRT/VTT/JSON |
| Audio Transcription | MP3/WAV/M4A → Whisper → Multi-format output |
| Video Transcription | MP4/MKV/WebM/AVI/MOV/FLV/TS → Audio → Whisper |
| URL Unified Entry | Auto-detect URL type (YouTube/Webpage/Direct link) |
| Cache Cleanup | Clean temporary files and Whisper model cache |

### 1.3 Universal Characteristics

- Streaming upload support for large files
- Concurrency control with queue waiting
- Request ID tracking
- IP whitelist (CIDR support)
- Environment variable validation
- Unified JSON response format
- Unified logging (English)
- Dual CLI and API interfaces

---

## 2. Functional Requirements

### 2.1 Streaming Upload

| Parameter | Value | Configurable |
|-----------|-------|--------------|
| Chunk Size | 1MB | Yes (`UPLOAD_CHUNK_SIZE`) |
| Resume Support | No | - |
| Upload Timeout | 30 minutes | Yes (`UPLOAD_TIMEOUT`) |
| Memory Buffer | 10MB | Yes (`UPLOAD_BUFFER_SIZE`) |

### 2.2 Temporary File Cleanup

| Parameter | Default | Description |
|-----------|---------|-------------|
| Dry-run Mode | Enabled | Preview only by default |
| Failed Files | Auto-delete | Clean up on failure |
| Cleanup Threshold | None | User-specified via API/Script |

### 2.3 Whisper Model Strategy

- Pre-download `base` model in Dockerfile
- Only one model exists at a time
- Model switching: download new → delete old (atomic operation)
- Return "downloading model" message during download

### 2.4 Concurrency Control

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Concurrent | 3 | Maximum simultaneous requests |
| Queue Timeout | 10 minutes | Wait time before error |
| Queue Position | Included in response | Position in queue |

### 2.5 Timestamp in Markdown

| Parameter | Default | Configurable |
|-----------|---------|--------------|
| Include Timestamps | False | Yes (via `include_timestamps` parameter) |

### 2.6 Language Detection

| Mode | Description |
|------|-------------|
| Default | Auto-detect by Whisper |
| User-specified | Override with `language` parameter |

---

## 3. API Endpoint Design

### 3.1 Endpoint Structure

```
/api/v1/
├── convert/
│   ├── POST /file          # File conversion
│   ├── POST /url           # URL unified entry
│   ├── POST /youtube       # YouTube transcription
│   ├── POST /audio         # Audio transcription
│   └── POST /video         # Video transcription
├── admin/
│   ├── POST /cleanup       # Cache cleanup
│   ├── GET /queue          # Queue status
│   └── GET /config         # Configuration query
├── languages/
│   ├── GET /ocr            # OCR supported languages
│   └── GET /transcribe     # Transcription supported languages
├── GET /formats            # Supported formats
└── GET /health             # Health check
```

---

### 3.2 POST /api/v1/convert/file

**File upload and conversion to Markdown**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | File | Yes | - | File to convert |
| enable_ocr | bool | No | false | Enable OCR |
| ocr_lang | str | No | `OCR_DEFAULT_LANG` | OCR language code |
| return_format | str | No | markdown | Output format |

#### Response

```json
{
  "success": true,
  "data": {
    "content": "# Markdown content...",
    "format": "markdown"
  },
  "metadata": {
    "filename": "document.pdf",
    "file_size": 123456,
    "conversion_time": "2026-03-16T14:30:00Z",
    "ocr_language": "chi_tra+eng"
  },
  "request_id": "req-abc123"
}
```

---

### 3.3 POST /api/v1/convert/url

**URL unified entry with auto-detection**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | str | Yes | - | URL address |
| type_hint | str | No | auto | Type hint: auto/youtube/document/audio/video/webpage |
| language | str | No | auto | Transcription language (auto=detect) |
| model_size | str | No | base | Whisper model size |
| ocr_lang | str | No | `OCR_DEFAULT_LANG` | OCR language |
| output_formats | str | No | markdown | Output formats (comma-separated) |
| include_timestamps | bool | No | false | Include timestamps in Markdown |

#### Response

```json
{
  "success": true,
  "data": {
    "formats": {
      "markdown": "# Transcription content...",
      "srt": "1\n00:00:00,000 --> 00:00:05,000\n...",
      "vtt": "WEBVTT\n..."
    },
    "default_format": "markdown"
  },
  "metadata": {
    "source_type": "youtube",
    "title": "Video title",
    "duration": 1234.5,
    "language": "zh",
    "model": "base"
  },
  "request_id": "req-abc123"
}
```

---

### 3.4 POST /api/v1/convert/youtube

**YouTube video transcription**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | str | Yes | - | YouTube URL |
| language | str | No | auto | Language code |
| model_size | str | No | base | Model size |
| output_formats | str | No | markdown | Output formats |
| include_timestamps | bool | No | false | Include timestamps |
| include_metadata | bool | No | true | Include metadata |

---

### 3.5 POST /api/v1/convert/audio

**Audio file transcription**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | File | Yes | - | Audio file |
| language | str | No | auto | Language code |
| model_size | str | No | base | Model size |
| output_formats | str | No | markdown | Output formats |
| include_timestamps | bool | No | false | Include timestamps |

---

### 3.6 POST /api/v1/convert/video

**Video file transcription**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | File | Yes | - | Video file (MP4/MKV/WebM/AVI/MOV/FLV/TS) |
| language | str | No | auto | Language code |
| model_size | str | No | base | Model size |
| output_formats | str | No | markdown | Output formats |
| include_timestamps | bool | No | false | Include timestamps |

---

### 3.7 POST /api/v1/admin/cleanup

**Cache cleanup**

#### Request

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| targets | str | No | temp | Cleanup targets: temp/whisper/all (comma-separated) |
| dry_run | bool | No | true | Preview only without deletion |

#### Response

```json
{
  "success": true,
  "data": {
    "cleaned": {
      "temp_files": {
        "count": 5,
        "size_mb": 125.3,
        "files": ["/tmp/abc123.mp3", ...]
      },
      "whisper_cache": {
        "count": 1,
        "size_mb": 150.0,
        "models": ["base"]
      }
    },
    "total_freed_mb": 275.3,
    "dry_run": true
  },
  "request_id": "req-abc123"
}
```

---

### 3.8 GET /api/v1/admin/queue

**Query queue status**

#### Response

```json
{
  "success": true,
  "data": {
    "current_processing": 2,
    "max_concurrent": 3,
    "queue_length": 5,
    "queue": [
      {"request_id": "req-111", "type": "youtube", "status": "processing"},
      {"request_id": "req-222", "type": "video", "status": "processing"},
      {"request_id": "req-333", "type": "convert", "status": "queued", "position": 1}
    ]
  },
  "request_id": "req-abc123"
}
```

---

### 3.9 GET /api/v1/admin/config

**Query current configuration**

#### Response

```json
{
  "success": true,
  "data": {
    "api": {
      "version": "1.0.0",
      "port": 51083,
      "debug": false,
      "max_upload_size_mb": 500,
      "upload_timeout_minutes": 30,
      "max_concurrent_requests": 3
    },
    "ocr": {
      "enabled": false,
      "default_language": "chi_tra+eng",
      "openai_enabled": false
    },
    "whisper": {
      "model": "base",
      "device": "cpu",
      "compute_type": "int8"
    },
    "cleanup": {
      "temp_threshold_hours": 1,
      "auto_cleanup_enabled": false
    },
    "admin": {
      "ip_restriction_enabled": false,
      "allowed_ips": []
    }
  },
  "request_id": "req-abc123"
}
```

---

### 3.10 GET /api/v1/languages/ocr

**OCR supported languages**

#### Response

```json
{
  "success": true,
  "data": {
    "languages": {
      "chi_tra": "Traditional Chinese",
      "chi_sim": "Simplified Chinese",
      "eng": "English",
      "jpn": "Japanese",
      "kor": "Korean",
      "tha": "Thai",
      "vie": "Vietnamese"
    },
    "default": "chi_tra+eng",
    "combinations": ["chi_tra+eng", "chi_sim+eng", "chi_tra+jpn+kor+eng"]
  },
  "request_id": "req-abc123"
}
```

---

### 3.11 GET /api/v1/languages/transcribe

**Transcription supported languages**

#### Response

```json
{
  "success": true,
  "data": {
    "languages": {
      "zh": "Chinese",
      "en": "English",
      "ja": "Japanese",
      "ko": "Korean"
    },
    "models": {
      "tiny": {"speed": "fastest", "accuracy": "fair", "memory_mb": 500},
      "base": {"speed": "fast", "accuracy": "good", "memory_mb": 1000},
      "small": {"speed": "medium", "accuracy": "very good", "memory_mb": 2000},
      "medium": {"speed": "slow", "accuracy": "excellent", "memory_mb": 5000},
      "large": {"speed": "slowest", "accuracy": "best", "memory_mb": 10000}
    }
  },
  "request_id": "req-abc123"
}
```

---

### 3.12 GET /api/v1/formats

**Supported file formats**

#### Response

```json
{
  "success": true,
  "data": {
    "documents": ["pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls"],
    "images": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"],
    "audio": ["mp3", "wav", "m4a", "flac", "ogg"],
    "video": ["mp4", "mkv", "webm", "avi", "mov", "flv", "ts"],
    "web": ["html", "htm", "url"],
    "data": ["csv", "json", "xml"]
  },
  "request_id": "req-abc123"
}
```

---

### 3.13 GET /health

**Health check**

#### Response

```json
{
  "status": "ok"
}
```

---

### 3.14 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": "Additional details"
  },
  "request_id": "req-abc123",
  "timestamp": "2026-03-16T14:30:00Z"
}
```

---

### 3.15 Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `UNSUPPORTED_FORMAT` | 400 | Unsupported file format |
| `INVALID_OCR_LANGUAGE` | 400 | Invalid OCR language code |
| `YOUTUBE_DOWNLOAD_FAILED` | 500 | YouTube download failed |
| `WHISPER_DOWNLOADING` | 202 | Downloading Whisper model |
| `WHISPER_TRANSCRIPTION_FAILED` | 500 | Whisper transcription failed |
| `VIDEO_CONVERSION_FAILED` | 500 | Video conversion failed |
| `QUEUE_WAITING` | 202 | Request waiting in queue |
| `IP_NOT_ALLOWED` | 403 | IP not in whitelist |
| `INVALID_CONFIG` | 500 | Configuration validation failed |
| `NOT_FOUND` | 404 | Route not found |

---

## 4. CLI Command Design

### 4.1 Command Structure

```bash
./cli.py <command> [options]
```

### 4.2 Command List

| Command | Description |
|---------|-------------|
| `convert` | File conversion |
| `youtube` | YouTube transcription |
| `video` | Video transcription |
| `audio` | Audio transcription |
| `url` | URL processing |
| `cleanup` | Cache cleanup |
| `queue` | Queue status |
| `config` | Configuration display |
| `health` | Health check |

### 4.3 Detailed Commands

---

#### 4.3.1 convert - File Conversion

```bash
# Basic usage
./cli.py convert document.pdf

# Specify output file
./cli.py convert document.pdf --output result.md

# Enable OCR
./cli.py convert scanned.pdf --enable-ocr --ocr-lang chi_tra+eng

# Specify output format
./cli.py convert document.pdf --format json
```

**Options:**

| Option | Description |
|--------|-------------|
| `--output, -o` | Output file path |
| `--enable-ocr` | Enable OCR |
| `--ocr-lang` | OCR language code |
| `--format` | Output format (markdown/json) |

---

#### 4.3.2 youtube - YouTube Transcription

```bash
# Basic usage
./cli.py youtube "https://youtube.com/watch?v=xxx"

# Specify language and model
./cli.py youtube <url> --language en --model small

# Multi-format output
./cli.py youtube <url> --formats markdown,srt,vtt

# Include timestamps
./cli.py youtube <url> --include-timestamps
```

**Options:**

| Option | Description |
|--------|-------------|
| `--language, -l` | Language code |
| `--model, -m` | Whisper model size |
| `--formats, -f` | Output formats (comma-separated) |
| `--include-timestamps` | Include timestamps in Markdown |
| `--output, -o` | Output file path |

---

#### 4.3.3 video - Video Transcription

```bash
# Basic usage
./cli.py video recording.mp4

# Specify language
./cli.py video recording.mp4 --language zh

# Multi-format output
./cli.py video recording.mp4 --formats markdown,srt
```

---

#### 4.3.4 audio - Audio Transcription

```bash
# Basic usage
./cli.py audio podcast.mp3

# Specify model
./cli.py audio podcast.mp3 --model medium
```

---

#### 4.3.5 url - URL Processing

```bash
# Auto-detect
./cli.py url "https://youtube.com/watch?v=xxx"
./cli.py url "https://example.com/document.pdf"

# Specify type
./cli.py url <url> --type youtube
./cli.py url <url> --type document
```

**Options:**

| Option | Description |
|--------|-------------|
| `--type, -t` | Type hint (auto/youtube/document/audio/video) |
| `--language, -l` | Language code |
| `--model, -m` | Whisper model size |
| `--formats, -f` | Output formats |

---

#### 4.3.6 cleanup - Cache Cleanup

```bash
# Preview mode (default)
./cli.py cleanup --target temp

# Execute deletion
./cli.py cleanup --target temp --execute

# Cleanup all
./cli.py cleanup --target all --execute

# Cleanup Whisper cache
./cli.py cleanup --target whisper --execute
```

**Options:**

| Option | Description |
|--------|-------------|
| `--target, -t` | Cleanup target (temp/whisper/all) |
| `--dry-run` | Preview only (default) |
| `--execute` | Execute deletion |

**Output Example:**

```
Cleanup Preview (dry-run)
========================
Target: temp

Temporary Files:
  /tmp/abc123.mp3          15.3 MB
  /tmp/def456.mp3          22.1 MB
  /tmp/page_0.png           0.5 MB
  /tmp/page_1.png           0.4 MB
  /tmp/temp_xxx.pdf         3.2 MB

Total: 5 files, 41.5 MB

Run with --execute to delete.
```

---

#### 4.3.7 queue - Queue Status

```bash
./cli.py queue
```

**Output Example:**

```
Queue Status
============
Current Processing: 2/3
Queue Length: 5

Processing:
  - req-111: youtube (processing)
  - req-222: video (processing)

Queued:
  1. req-333: convert
  2. req-444: youtube
  3. req-555: audio
  4. req-666: video
  5. req-777: url
```

---

#### 4.3.8 config - Configuration Display

```bash
./cli.py config
```

**Output Example:**

```
Configuration
=============

API:
  Version: 1.0.0
  Port: 51083
  Debug: false
  Max Upload Size: 500 MB
  Upload Timeout: 30 minutes
  Max Concurrent Requests: 3

OCR:
  Enabled: false
  Default Language: chi_tra+eng
  OpenAI Enabled: false

Whisper:
  Model: base
  Device: cpu
  Compute Type: int8

Cleanup:
  Temp Threshold: 1 hour
  Auto Cleanup: false

Admin:
  IP Restriction: false
  Allowed IPs: (all)
```

---

#### 4.3.9 health - Health Check

```bash
./cli.py health
```

**Output Example:**

```
Health Check: OK
API Version: 1.0.0
Uptime: 2h 30m
Whisper Model: base (cached)
```

---

## 5. Environment Variables

### 5.1 Category Table

| Category | Prefix | Description |
|----------|--------|-------------|
| API Service | `API_` | API configuration |
| Upload Limits | `UPLOAD_` | Upload size, timeout |
| OCR Config | `OCR_` | OCR language, enable status |
| OpenAI OCR | `VISION_OCR_` | OpenAI Vision OCR (optional) |
| Whisper Config | `WHISPER_` | Model, device, compute type |
| Concurrency | `CONCURRENT_` | Max concurrent requests |
| Cleanup Config | `CLEANUP_` | Cleanup settings |
| Admin Config | `ADMIN_` | IP whitelist |
| Log Config | `LOG_` | Log level, format |
| Auto Convert | `AUTO_` | Auto-convert service |

---

### 5.2 Complete Variable List

#### API Service

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Listen address |
| `API_PORT` | `51083` | External port |
| `API_PORT_INTERNAL` | `8000` | Internal port |
| `API_DEBUG` | `false` | Debug mode |
| `API_WORKERS` | `1` | Worker count |

#### Upload Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_MAX_SIZE` | `524288000` | Max upload size (500MB) |
| `UPLOAD_TIMEOUT` | `1800` | Upload timeout (30 min) |
| `UPLOAD_CHUNK_SIZE` | `1048576` | Chunk size (1MB) |
| `UPLOAD_BUFFER_SIZE` | `10485760` | Buffer size (10MB) |

#### OCR Config

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_DEFAULT_LANG` | `chi_tra+eng` | Default OCR language |
| `OCR_ENABLED_DEFAULT` | `false` | Enable by default |

#### OpenAI Vision OCR (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_OCR_ENABLED` | `false` | Enable OpenAI OCR |
| `VISION_OCR_API_KEY` | - | OpenAI API Key |
| `VISION_OCR_MODEL` | `gpt-4o` | Model |

#### Whisper Config

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Default model |
| `WHISPER_DEVICE` | `cpu` | Device |
| `WHISPER_COMPUTE_TYPE` | `int8` | Compute type |
| `WHISPER_DEFAULT_LANGUAGE` | `auto` | Default language (auto=detect) |

#### Concurrency Control

| Variable | Default | Description |
|----------|---------|-------------|
| `CONCURRENT_MAX_REQUESTS` | `3` | Max concurrent requests |
| `CONCURRENT_QUEUE_TIMEOUT` | `600` | Queue timeout (10 min) |

#### Cleanup Config

| Variable | Default | Description |
|----------|---------|-------------|
| `CLEANUP_TEMP_THRESHOLD_HOURS` | `1` | Temp file cleanup threshold |
| `CLEANUP_AUTO_ENABLED` | `false` | Auto cleanup |

#### Admin Config

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_IP_RESTRICTION_ENABLED` | `false` | Enable IP restriction |
| `ADMIN_ALLOWED_IPS` | - | Allowed IPs (CIDR supported) |

#### Log Config

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `json` | Log format |

#### Auto Convert

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_INPUT_DIR` | `/app/input` | Input directory |
| `AUTO_OUTPUT_DIR` | `/app/output` | Output directory |
| `AUTO_ENABLE_OCR` | `true` | Enable OCR |
| `AUTO_OCR_LANG` | `chi_tra+eng` | OCR language |
| `AUTO_POLL_INTERVAL` | `5` | Poll interval (seconds) |

---

## 6. Script Design

### 6.1 Script List

| Script | Path | Description |
|--------|------|-------------|
| Start Service | `scripts/start.sh` | Start Docker service |
| Stop Service | `scripts/stop.sh` | Stop Docker service |
| Batch Convert | `scripts/batch-convert.sh` | Batch file conversion |
| Cleanup Cache | `scripts/cleanup.sh` | Clean temp files and cache |
| Queue Status | `scripts/queue-status.sh` | View queue status |
| Health Check | `scripts/health-check.sh` | Service health check |
| Test Dependencies | `scripts/test-deps.sh` | Test system dependencies |

---

### 6.2 cleanup.sh Detailed Design

```bash
#!/bin/bash

# Usage
./scripts/cleanup.sh [OPTIONS]

OPTIONS:
  --target <type>    Cleanup target: temp, whisper, all (default: temp)
  --dry-run          Preview only without deletion (default)
  --execute          Execute deletion
  --help             Show help

EXAMPLES:
  # Preview temp files
  ./scripts/cleanup.sh --target temp

  # Delete temp files
  ./scripts/cleanup.sh --target temp --execute

  # Cleanup all (requires confirmation)
  ./scripts/cleanup.sh --target all --execute
```

---

## 7. Documentation Structure

```
oh-my-markitdown/
├── README.md                      # Quick Start (English)
├── README_ZH_TW.md               # Quick Start (Traditional Chinese, no flag)
├── CHANGELOG.md                   # Version history
├── CONTRIBUTING.md                # Contribution guide
├── docs/
│   ├── API.md                     # API documentation
│   ├── API_ZH_TW.md              # API documentation (Chinese)
│   ├── CLI.md                     # CLI usage
│   ├── CLI_ZH_TW.md              # CLI usage (Chinese)
│   ├── CONFIGURATION.md           # Configuration guide
│   ├── CONFIGURATION_ZH_TW.md    # Configuration guide (Chinese)
│   ├── DEPLOYMENT.md              # Deployment guide
│   ├── DEPLOYMENT_ZH_TW.md       # Deployment guide (Chinese)
│   ├── ERROR_CODES.md            # Error code reference
│   └── ERROR_CODES_ZH_TW.md      # Error code reference (Chinese)
```

---

## 8. Implementation Priority

### Phase 1: Basic Fixes (P0)

| Task | Description |
|------|-------------|
| YouTube audio cleanup bug | Fix temporary file not being cleaned |
| Add logging module | Unified logging system |
| Remove `/` endpoint | Keep only `/health` |
| Add 404 handler | Return empty content |
| Environment variable validation | Check config on startup |

### Phase 2: Core Features (P1)

| Task | Description |
|------|-------------|
| Unified JSON response format | All APIs return unified format |
| Request ID tracking | Unique ID per request |
| Video transcription API | New `/api/v1/convert/video` |
| URL unified entry | New `/api/v1/convert/url` |
| Subtitle format output | SRT/VTT support |
| Concurrency control | Queue waiting mechanism |

### Phase 3: Admin Features (P2)

| Task | Description |
|------|-------------|
| Cleanup API | `/api/v1/admin/cleanup` |
| Cleanup Script | `scripts/cleanup.sh` |
| Queue status API | `/api/v1/admin/queue` |
| Config query API | `/api/v1/admin/config` |
| IP whitelist | CIDR support |

### Phase 4: CLI Enhancement (P3)

| Task | Description |
|------|-------------|
| CLI refactoring | Unified command format |
| All features CLI | CLI for every feature |

### Phase 5: Documentation (P4)

| Task | Description |
|------|-------------|
| Document split | Restructure per design |
| README simplification | Move details to docs/ |
| Add CHANGELOG | Version history |
| Add CONTRIBUTING | Contribution guide |

---

## 9. Glossary

| Term | Description |
|------|-------------|
| Transcribe / Transcription | Audio/Video to text conversion |
| Convert / Conversion | File format conversion |
| OCR | Optical Character Recognition |
| Language | Language code (zh, en, ja...) |
| Model | Whisper model size |
| Queue | Waiting queue |
| Concurrent | Simultaneous processing count |
| Cleanup | Cache/temporary file cleanup |
| Timestamp | Time marker |
| Dry-run | Preview mode without execution |
| CIDR | Classless Inter-Domain Routing for IP ranges |

---

## Appendix A: Queue Waiting Response Format

```json
{
  "success": false,
  "error": {
    "code": "QUEUE_WAITING",
    "message": "Service busy, request is queuing",
    "details": {
      "queue_position": 3,
      "estimated_wait_seconds": 45,
      "current_processing": 3,
      "max_concurrent": 3
    }
  },
  "request_id": "req-abc123",
  "retry_after": 45
}
```

---

## Appendix B: 404 Handler Implementation

```python
from fastapi import Request
from fastapi.responses import Response

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Return empty 404 response"""
    return Response(status_code=404)
```

---

## Appendix C: Whisper Model Switching Logic

```python
def switch_whisper_model(new_model: str) -> bool:
    """
    Switch Whisper model with atomic operation.
    
    1. Download new model
    2. On success: delete old model
    3. On failure: keep old model
    
    Returns True if successful.
    """
    if new_model == current_model:
        return True  # No change needed
    
    try:
        # Download new model (blocking)
        download_whisper_model(new_model)
        
        # Atomic switch
        old_model = current_model
        current_model = new_model
        
        # Delete old model
        delete_whisper_model(old_model)
        
        return True
    except Exception as e:
        logger.error(f"Failed to switch model: {e}")
        return False
```

---

## Appendix D: Streaming Upload Implementation

```python
from fastapi import UploadFile
import tempfile
import shutil

async def handle_streaming_upload(
    file: UploadFile,
    chunk_size: int = 1048576,  # 1MB
    buffer_size: int = 10485760   # 10MB
) -> str:
    """
    Handle streaming upload for large files.
    
    Returns path to temporary file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    
    try:
        buffer = bytearray()
        
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            
            buffer.extend(chunk)
            
            # Write to disk when buffer exceeds threshold
            if len(buffer) >= buffer_size:
                temp_file.write(buffer)
                buffer = bytearray()
        
        # Write remaining buffer
        if buffer:
            temp_file.write(buffer)
        
        return temp_file.name
        
    except Exception as e:
        # Cleanup on failure
        temp_file.close()
        os.unlink(temp_file.name)
        raise e
```

---

**Document End**

*Generated: 2026-03-16*