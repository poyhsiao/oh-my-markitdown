# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-03-19

### Added

- GPU acceleration support for Whisper transcription (CUDA, MPS)
- New parameter `device` for compute device selection (cpu, cuda, mps, auto)
- New parameter `cpu_threads` for CPU thread count configuration
- New parameter `vad_enabled` for Voice Activity Detection filtering
- New endpoint `GET /api/v1/device-info` to query available compute devices

### Fixed

- `include_timestamps` parameter now correctly controls timestamp display in Markdown output
- Fixed missing `api/device_utils.py` in Dockerfile

---

## [0.3.0] - 2026-03-17

### Added

- YouTube subtitle priority strategy for faster transcription (2-5 seconds vs 30-60 minutes)
- New parameters: `prefer_subtitles` and `fast_mode` for `/convert/youtube` endpoint
- Multi-threading support for Whisper transcription (`cpu_threads` parameter)
- Low quality audio download option for faster YouTube processing (`audio_quality` parameter)
- Processing time tracking in response metadata

### Changed

- `transcribe_youtube_video()` now checks for subtitles first before falling back to Whisper
- Response metadata now includes `source`, `is_auto_generated`, and `processing_time_ms` fields
- Markdown output includes source information (YouTube Subtitles vs Whisper AI)

---

## [0.2.0] - 2026-03-17

### Added

- System Management API (storage, cleanup, model cache endpoints)
- CLI scripts for storage and cleanup operations
- Auto-convert retry mechanism with exponential backoff
- Request ID middleware for debugging
- Apache-2.0 LICENSE

### Changed

- Translated all API documentation to English
- Updated version to 0.2.0
- Simplified README structure with separate documentation files

### Fixed

- Auto-convert path handling for different platforms
- Test reliability improvements

---

## [0.1.0] - 2026-03-14

### Added

- YouTube video transcription using Faster-Whisper
- Audio file transcription (MP3, WAV, M4A, FLAC, OGG)
- API versioning (`/api/v1` prefix)
- 16+ transcription languages support
- New endpoint: `GET /api/v1/convert/languages`

### Changed

- All endpoints now use `/api/v1` prefix
- Increased memory limit to 4GB for Whisper models

### Fixed

- HTTP header encoding for Chinese filenames
- PDF OCR for scanned documents

---

## [0.0.1] - 2026-03-13

### Added

- Initial release based on Microsoft MarkItDown
- Docker containerization
- 7 Asian language OCR support
- File conversion endpoints
- Auto-convert feature
- CLI tool
- Swagger UI documentation

---

[0.3.1]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/poyhsiao/oh-my-markitdown/releases/tag/v0.0.1