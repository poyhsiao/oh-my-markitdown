# System Management Guide

## Overview

The System Management API provides endpoints for monitoring and managing server resources, temporary files, model caches, and configuration.

## Authentication

If `API_KEY` environment variable is set, all system endpoints require authentication via `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:51083/api/v1/system/storage
```

If `API_KEY` is not set, authentication is skipped.

## Endpoints

### Storage Query

```bash
GET /api/v1/system/storage
```

Returns detailed storage breakdown by category.

**Response:**
```json
{
  "total_bytes": 12345678,
  "total_mb": 11.77,
  "breakdown": {
    "youtube_audio": {
      "bytes": 5242880,
      "mb": 5.0,
      "files": 3
    },
    "ocr_temp": {
      "bytes": 2097152,
      "mb": 2.0,
      "files": 15
    },
    "uploads": {
      "bytes": 3145728,
      "mb": 3.0,
      "files": 5
    },
    "failed": {
      "bytes": 1857918,
      "mb": 1.77,
      "files": 2
    }
  },
  "models": {
    "max_size": 3,
    "current_size": 1,
    "cached_models": ["base"]
  }
}
```

### Cleanup

```bash
POST /api/v1/system/cleanup
Content-Type: application/json

{
  "types": ["youtube", "ocr", "uploads", "failed", "models", "all"]
}
```

**Cleanup Types:**
- `youtube` - YouTube downloaded audio files
- `ocr` - OCR temporary images
- `uploads` - Upload temporary files
- `models` - Whisper model cache (memory)
- `failed` - Failed conversion files
- `all` - All of the above

**Response:**
```json
{
  "success": true,
  "cleaned": {
    "youtube_audio": {"files": 3, "bytes": 5242880},
    "ocr_temp": {"files": 15, "bytes": 2097152},
    "uploads": {"files": 5, "bytes": 3145728},
    "failed": {"files": 2, "bytes": 1857918},
    "models": {"cleared": 1, "freed_memory_mb": 1024}
  },
  "total_freed_bytes": 12345678,
  "total_freed_mb": 11.77
}
```

### Model Cache Management

```bash
# Get cache info
GET /api/v1/system/models

# Clear all cached models
DELETE /api/v1/system/models

# Remove specific model
DELETE /api/v1/system/models/{key}

# Update cache configuration
PATCH /api/v1/system/models/config
Content-Type: application/json
{"max_size": 5}
```

**Get Cache Info Response:**
```json
{
  "max_size": 3,
  "current_size": 1,
  "cached_models": ["base"]
}
```

### Configuration Endpoints

```bash
# Get timeout configuration
GET /api/v1/system/config/timeouts

# Update timeout configuration
PATCH /api/v1/system/config/timeouts
Content-Type: application/json
{
  "convert": 600,
  "youtube_transcribe": 1200,
  "audio_transcribe": 900
}

# Get cache configuration
GET /api/v1/system/config/cache
```

## CLI Scripts

### Storage Query

```bash
# Human-readable output
python scripts/storage.py

# JSON output
python scripts/storage.py --json
```

**Output:**
```
=== MarkItDown Storage Usage ===

youtube_audio:
  Files: 3
  Size:  5.00 MB

ocr_temp:
  Files: 15
  Size:  2.00 MB

uploads:
  Files: 5
  Size:  3.00 MB

failed:
  Files: 2
  Size:  1.77 MB

Total: 11.77 MB (12345678 bytes)
```

### Cleanup

```bash
# Preview what would be cleaned
python scripts/cleanup.py --dry-run

# Clean YouTube audio files
python scripts/cleanup.py --types youtube --force

# Clean all temporary files
python scripts/cleanup.py --types all --force

# Clean specific types
python scripts/cleanup.py --types ocr,uploads --force

# JSON output
python scripts/cleanup.py --types all --force --json
```

**Options:**
- `--types, -t` - Types to clean (default: all)
- `--dry-run, -n` - Preview without cleaning
- `--force, -f` - Actually perform cleanup (required for safety)
- `--json, -j` - Output in JSON format

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | - | Optional API key for system endpoints |
| `TEMP_DIR` | `/tmp` | Root directory for temporary files |
| `WHISPER_MODEL_CACHE_SIZE` | `3` | Maximum number of cached Whisper models |
| `CONVERT_TIMEOUT` | `300` | File conversion timeout (seconds) |
| `YOUTUBE_TRANSCRIBE_TIMEOUT` | `600` | YouTube transcription timeout (seconds) |
| `AUDIO_TRANSCRIBE_TIMEOUT` | `600` | Audio transcription timeout (seconds) |
| `YOUTUBE_INFO_TIMEOUT` | `300` | YouTube video info fetch timeout (seconds) |
| `YOUTUBE_DOWNLOAD_TIMEOUT` | `600` | YouTube audio download timeout (seconds) |
| `AUDIO_EXTRACT_TIMEOUT` | `300` | Audio extraction from video timeout (seconds) |
| `AUTO_MAX_RETRIES` | `3` | Maximum retry attempts |
| `AUTO_RETRY_BASE_DELAY` | `2` | Base delay for exponential backoff |
| `AUTO_RETRY_MAX_DELAY` | `60` | Maximum delay between retries |

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `404` - Not found (e.g., model not in cache)
- `500` - Internal server error

## Retry Mechanism

The auto-convert service includes exponential backoff retry:

1. **First failure**: Wait `BASE_DELAY` seconds (default: 2s)
2. **Second failure**: Wait `BASE_DELAY * 2` seconds (default: 4s)
3. **Third failure**: Wait `BASE_DELAY * 4` seconds (default: 8s)
4. **Max retries exhausted**: Move file to `.failed` directory

Failed files are stored in `{TEMP_DIR}/.failed/` with an accompanying `.error` file containing:

```json
{
  "timestamp": "2026-03-16T12:00:00",
  "error": "Error message",
  "retries": 3,
  "file": "document.pdf"
}
```

## Logging

All requests are logged with:
- Request ID (returned in `X-Request-ID` header)
- HTTP method and path
- Client IP
- Request/response sizes
- Processing time

Configure logging via environment variables:
- `LOG_FORMAT` - Output format: `text` (default) or `json`
- `LOG_OUTPUT` - Output target: `stdout`, `file`, or `stdout,file`
- `LOG_FILE` - Log file path (when `LOG_OUTPUT` includes `file`)
- `LOG_FILE_MAX_SIZE` - Max size per log file (default: `10m`)
- `LOG_FILE_MAX_COUNT` - Number of log files to keep (default: `3`)

## Examples

### Check storage usage

```bash
# API
curl http://localhost:51083/api/v1/system/storage | jq

# CLI
python scripts/storage.py
```

### Clean up all temporary files

```bash
# API
curl -X POST http://localhost:51083/api/v1/system/cleanup \
  -H "Content-Type: application/json" \
  -d '{"types": ["all"]}'

# CLI
python scripts/cleanup.py --types all --force
```

### Manage model cache

```bash
# Check cache status
curl http://localhost:51083/api/v1/system/models

# Clear all models
curl -X DELETE http://localhost:51083/api/v1/system/models

# Update cache size
curl -X PATCH http://localhost:51083/api/v1/system/models/config \
  -H "Content-Type: application/json" \
  -d '{"max_size": 5}'
```

### Configure timeouts

```bash
# Get current timeouts
curl http://localhost:51083/api/v1/system/config/timeouts

# Update timeouts
curl -X PATCH http://localhost:51083/api/v1/system/config/timeouts \
  -H "Content-Type: application/json" \
  -d '{"convert": 600}'
```