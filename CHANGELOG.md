# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-14

### Added

#### YouTube Video Transcription (Faster-Whisper)
- **New endpoint:** `POST /convert/youtube` - Transcribe YouTube videos using Faster-Whisper
- Download YouTube audio and convert to text locally (no API limits!)
- Support for 16+ languages including Chinese, English, Japanese, Korean, etc.
- Configurable model sizes (tiny, base, small, medium, large)
- JSON and Markdown output formats
- Automatic metadata extraction (title, duration, uploader, view count)

#### Audio File Transcription (Faster-Whisper)
- **New endpoint:** `POST /convert/audio` - Upload and transcribe audio files
- Support for MP3, WAV, M4A, FLAC, OGG formats
- Local processing with Faster-Whisper (no external API required)
- Multi-language support with automatic language detection
- No rate limits or API quotas

#### Language Support
- **New endpoint:** `GET /convert/languages` - List supported transcription languages
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
- Removed old `/convert/youtube` endpoint (MarkItDown internal, had YouTube API rate limits)
- Modified `/convert/url` to reject YouTube URLs with helpful error message
- All YouTube-related functionality now uses Faster-Whisper

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

### Planned for 0.2.0
- [ ] GPU support for faster transcription
- [ ] Batch YouTube video transcription
- [ ] Timestamp support in transcripts
- [ ] Speaker diarization (identify different speakers)
- [ ] Whisper model pre-loading on startup

### Planned for 0.3.0
- [ ] Real-time transcription WebSocket endpoint
- [ ] Support for video files (extract audio + transcribe)
- [ ] Custom vocabulary for domain-specific terms
- [ ] Multi-language auto-detection

---

## Migration Guide

### Migrating from 0.0.1 to 0.1.0

#### YouTube URLs
- **Before:** `POST /convert/url?url=YouTube_URL` (rate limited)
- **After:** `POST /convert/youtube?url=YouTube_URL&language=zh` (local, no limits)

#### API Response Changes
The new transcription endpoints return structured metadata:

```json
{
  "success": true,
  "title": "Video Title",
  "transcript": "Transcribed text...",
  "metadata": {
    "language": "zh",
    "duration": 534.8,
    "model": "base"
  }
}
```

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

[0.1.0]: https://github.com/kimhsiao/markitdown-kim/releases/tag/v0.1.0
[0.0.1]: https://github.com/kimhsiao/markitdown-kim/releases/tag/v0.0.1