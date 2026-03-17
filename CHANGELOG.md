# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-17

### Added

#### System Management API

- **New endpoint:** `GET /api/v1/admin/storage` - Query storage usage for temporary files
- **New endpoint:** `POST /api/v1/admin/cleanup` - Clean up temporary files (temp, whisper, all)
- **New endpoint:** `GET /api/v1/admin/models` - Get Whisper model cache information
- **New endpoint:** `DELETE /api/v1/admin/models` - Clear all cached models
- **New endpoint:** `GET /api/v1/admin/queue` - Get current queue status
- **New endpoint:** `GET /api/v1/config` - Enhanced configuration endpoint with validation

#### CLI Scripts

- **New script:** `scripts/storage.py` - CLI tool for checking storage usage
- **New script:** `scripts/cleanup.py` - CLI tool for cleaning temporary files with dry-run support

#### Auto-Convert Enhancements

- **Retry mechanism:** Automatic retry with exponential backoff for failed conversions
- **Configurable retry:** `AUTO_MAX_RETRIES` and `AUTO_RETRY_DELAY` environment variables
- **Improved error handling:** Better logging and error recovery

#### Error Handling

- **Request ID middleware:** Unique request IDs for tracing and debugging
- **Global error handler:** Consistent error responses across all endpoints
- **Input validation:** Environment variable validation on startup

#### Documentation

- **API Reference:** New `docs/API_REFERENCE.md` with complete endpoint documentation
- **Code Examples:** New `docs/CODE_EXAMPLES.md` with Python/cURL/Node.js examples
- **Advanced Configuration:** New `docs/ADVANCED_CONFIG.md` for OpenAI/Azure/Docker setup
- **Troubleshooting:** New `docs/TROUBLESHOOTING.md` with common issues and solutions
- **System Management:** New `docs/SYSTEM_MANAGEMENT.md` for admin operations

### Changed

#### Documentation Structure

- **README.md:** Simplified and reorganized with links to detailed documentation
- **Language switcher:** Removed flag emojis from language links
- **Version bump:** Updated to 0.2.0

#### API Improvements

- **Consistent error responses:** All errors now follow a standard format
- **Better logging:** Structured logging with request IDs
- **Health checks:** Enhanced health check endpoints

### Fixed

- **Path conversion bug:** Fixed auto-convert path handling for different platforms
- **Test assertions:** Fixed test cases for cleanup_types_mapping and error messages
- **File operation mocking:** Improved test reliability for retry mechanism tests

### Technical Details

#### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_MAX_RETRIES` | `3` | Maximum retry attempts for auto-convert |
| `AUTO_RETRY_DELAY` | `5` | Delay between retries (seconds) |
| `API_KEY` | - | Optional API key for admin endpoints |

#### Storage Management

The new storage endpoint provides detailed breakdown:

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

#### Queue Management

Queue status endpoint provides real-time monitoring:

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

## [0.1.0] - 2026-03-14

### Added

#### YouTube Video Transcription (Faster-Whisper)

- **New endpoint:** `POST /api/v1/convert/youtube` - Transcribe YouTube videos using Faster-Whisper
- Download YouTube audio and convert to text locally (no API limits!)
- Support for 16+ languages including Chinese, English, Japanese, Korean, etc.
- Configurable model sizes (tiny, base, small, medium, large)
- JSON and Markdown output formats
- Automatic metadata extraction (title, duration, uploader, view count)

#### Audio File Transcription (Faster-Whisper)

- **New endpoint:** `POST /api/v1/convert/audio` - Upload and transcribe audio files
- Support for MP3, WAV, M4A, FLAC, OGG formats
- Local processing with Faster-Whisper (no external API required)
- Multi-language support with automatic language detection
- No rate limits or API quotas

#### API Versioning

- All API endpoints now use `/api/v1` prefix
- Improved API organization and future compatibility

#### Language Support

- **New endpoint:** `GET /api/v1/convert/languages` - List supported transcription languages
- 16+ languages supported:
  - Chinese (Traditional & Simplified)
  - English
  - Japanese
  - Korean
  - French
  - German
  - Spanish
  - Portuguese
  - Russian
  - Arabic
  - Hindi
  - Thai
  - Vietnamese

#### Dependencies

- Added `faster-whisper` package for local speech-to-text
- Added `yt-dlp` for YouTube audio extraction
- Increased default memory limit to 4GB for Whisper models

### Changed

#### API Endpoints

- Removed `/convert/url` endpoint (no longer needed)
- All endpoints now use `/api/v1` prefix for better versioning
- Endpoints renamed:
  - `/convert` → `/api/v1/convert`
  - `/formats` → `/api/v1/formats`
  - `/ocr-languages` → `/api/v1/ocr-languages`
  - `/config` → `/api/v1/config`

#### Docker Configuration

- Increased memory limit from 2GB to 4GB (required for Whisper models)
- Added Whisper-specific environment variables:
  - `WHISPER_MODEL` (default: base)
  - `WHISPER_DEVICE` (default: cpu)
  - `WHISPER_COMPUTE_TYPE` (default: int8)

### Fixed

- Fixed HTTP header encoding issue with Chinese filenames
- Fixed PDF OCR for scanned documents
- Fixed audio transcription for non-English content

### Technical Details

#### Whisper Model Sizes

| Model | Speed | Accuracy | Memory | Use Case |
|-------|-------|----------|--------|----------|
| tiny | Fastest | Fair | ~500MB | Quick drafts |
| base | Fast | Good | ~1GB | General use (recommended) |
| small | Medium | Very Good | ~2GB | Higher accuracy needed |
| medium | Slow | Excellent | ~5GB | Professional transcription |
| large | Slowest | Best | ~10GB | Maximum accuracy |

#### Performance

- 9-minute Chinese video transcribed in ~60 seconds (base model)
- Accurate Chinese character recognition
- No internet required after model download (runs locally)

---

## [0.0.1] - 2026-03-13

### Added

- Initial release
- Based on Microsoft MarkItDown
- Docker containerization
- 7 Asian language OCR support (Traditional Chinese, Simplified Chinese, English, Japanese, Korean, Thai, Vietnamese)
- File conversion endpoints
- URL conversion endpoint
- Auto-convert feature for batch processing
- CLI tool for command-line usage
- Swagger UI documentation
- Health check endpoints
- Environment variable configuration

---

## Roadmap

### Planned for 0.3.0

- [ ] GPU support for faster transcription
- [ ] Batch YouTube video transcription
- [ ] Timestamp support in transcripts
- [ ] Speaker diarization (identify different speakers)
- [ ] Whisper model pre-loading on startup
- [ ] WebSocket endpoint for real-time transcription progress

### Planned for 0.4.0

- [ ] Real-time transcription WebSocket endpoint
- [ ] Support for video files (extract audio + transcribe)
- [ ] Custom vocabulary for domain-specific terms
- [ ] Multi-language auto-detection
- [ ] Webhook notifications for completed jobs

---

## Migration Guide

### Migrating from 0.1.0 to 0.2.0

#### New Admin Endpoints

All admin endpoints are now available:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/admin/storage` | Query storage usage |
| `POST /api/v1/admin/cleanup` | Clean temporary files |
| `GET /api/v1/admin/models` | Model cache info |
| `DELETE /api/v1/admin/models` | Clear model cache |
| `GET /api/v1/admin/queue` | Queue status |

#### New Environment Variables

```bash
# .env file
AUTO_MAX_RETRIES=3
AUTO_RETRY_DELAY=5
API_KEY=your-optional-api-key  # For admin endpoints
```

#### CLI Scripts

New management scripts available:

```bash
# Check storage
python scripts/storage.py

# Clean up (dry-run)
python scripts/cleanup.py --dry-run

# Clean up (execute)
python scripts/cleanup.py --force
```

### Migrating from 0.0.1 to 0.1.0

#### API Endpoint Changes

All endpoints now use `/api/v1` prefix:

| Old Endpoint | New Endpoint |
|--------------|--------------|
| `POST /convert` | `POST /api/v1/convert` |
| `POST /convert/url` | Removed (use `/api/v1/convert/youtube` for YouTube) |
| `GET /formats` | `GET /api/v1/formats` |
| `GET /ocr-languages` | `GET /api/v1/ocr-languages` |
| `GET /config` | `GET /api/v1/config` |

#### YouTube URLs

- **Before:** `POST /convert/url?url=YouTube_URL` (rate limited)
- **After:** `POST /api/v1/convert/youtube?url=YouTube_URL&language=zh` (local, no limits)

#### Docker Configuration

Update your `.env` file:

```bash
# New memory requirement for Whisper
MEMORY_LIMIT=4G

# Optional: Configure Whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
```

---

[0.2.0]: https://github.com/kimhsiao/markitdown-kim/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kimhsiao/markitdown-kim/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/kimhsiao/markitdown-kim/releases/tag/v0.0.1