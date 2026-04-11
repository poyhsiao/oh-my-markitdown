# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-04-11

### Added
- **Unified `return_format` Parameter**: All convert endpoints (`/convert/file`, `/convert/url`, `/convert/youtube`, `/convert/audio`, `/convert/video`, `/convert/clean-html`) now support a unified `return_format` query/form parameter with three modes:
  - `json`: Returns a structured JSON envelope (default for most endpoints)
  - `markdown`: Returns raw Markdown as plain text (`text/plain`)
  - `download`: Returns Markdown as a downloadable file attachment
- **`build_convert_response()` Helper**: New shared response builder in `api/response.py` that standardises all convert endpoint responses, reducing boilerplate and ensuring a consistent JSON envelope.
- **E2E Smoke Tests for `return_format`**: New end-to-end tests in `tests/e2e/` covering all six convert endpoints and all three output modes, verifying correct `Content-Type` headers and response shape.

### Changed
- **Version Bump**: `pyproject.toml`, FastAPI app metadata, and `/api/v1/config` endpoint all updated to `0.8.0`.
- **`uv.lock`**: Lock file updated to reflect the new project version (`0.8.0`).

### Fixed
- Corrected stale version strings (`0.6.0` in FastAPI app initialisation, `0.4.0` in `/api/v1/config` endpoint) to align with the current release.

---

## [0.7.0] - 2026-04-06

### Added
- **Smart Device Detection**: Multi-layer detection (`env` > `nvidia-smi` > `torch` > `CPU`) for optimal compute resource utilization without requiring PyTorch in base image.
- **Apple Silicon MPS Support**: Native execution support for macOS Apple Silicon via `scripts/run.sh` (bypasses Docker Linux VM limitation).
- **GPU Deployment Guide**: Added `docs/GPU_DEPLOYMENT.md` for NVIDIA CUDA server setup and verification.
- **GPU Verification Tool**: Added `scripts/verify_gpu_detection.py` to validate hardware detection and compute type mapping.
- **Device Info API**: Enhanced `/api/v1/device-info` endpoint to report Docker limitations and active hardware resources.
- **Timestamp Support**: Added `include_timestamps` parameter to `/api/v1/convert/youtube` for `[HH:MM:SS]` formatted transcripts.

### Changed
- **API Simplification**: Reduced parameters for `/convert/youtube`, `/convert/audio`, and `/convert/video` from 17+ to 5 core parameters (`url/file`, `language`, `model_size`, `return_format`, `quality_mode`).
- **Quality Mode Refactoring**: Simplified `quality_mode` values from `speed/balanced/quality` to `fast/standard/best`.
- **Default Format**: Changed default `return_format` for YouTube transcription from `markdown` to `json`.
- **Compute Type Auto-detection**: Fixed `compute_type` to automatically select `int8` for CPU and `float16` for CUDA/MPS instead of returning `"auto"`.
- **Device Parameter**: Added explicit `device` parameter to `/api/v1/convert/youtube` for manual GPU override.

### Fixed
- Fixed `include_timestamps` logic in `transcribe_youtube_video` to correctly pass through to the transcription engine.
- Fixed LSP type errors in `device_utils.py` and `whisper_transcribe.py`.

---

## [0.6.0] - 2026-04-03

### Added

- New `/api/v1/convert/clean-html` endpoint — extract clean article content from URL or uploaded HTML file using Readability
- New `clean_html` parameter for `/api/v1/convert/file` and `/api/v1/convert/url` endpoints (default: `true`)
  - `true`: use Readability to clean HTML before conversion (removes nav, header, footer, aside)
  - `false`: direct HTML-to-Markdown conversion (preserves all content)
- SSRF protection for URL-based endpoints — blocks requests to private/internal IP addresses
- `readability-lxml` dependency for article content extraction

### Fixed

- Added User-Agent headers to all HTTP requests to prevent blocking by websites
- Fixed legacy `/api/v1/convert/convert` endpoint missing route decorator
- Fixed missing timeout/headers on several `requests.get()` calls in `/api/v1/convert/url`

### Changed

- Extracted HTML-to-Markdown conversion to shared `_html_to_markdown()` helper function
- Updated API documentation with new endpoints and parameters

---

## [0.5.0] - 2026-04-03

### Added

- Comprehensive URL type detection with Content-Type header, Content-Disposition filename, extension fallback, and magic bytes detection
- New `ocr_mode` parameter for `/api/v1/convert/url` endpoint:
  - `auto` (default): auto-detect and run OCR when needed
  - `true`: force OCR for all files
  - `false`: disable OCR
- New URL types supported:
  - `json`: Returns JSON content as code block
  - `markdown`: Returns raw Markdown content
  - `text`: Returns plain text content
  - `image`: Image OCR with configurable language
- Magic bytes detection for octet-stream Content-Type
- Extension-based type detection for JSON, Markdown, and text files

### Changed

- Refactored `detect_url_type` to return tuple `(type, metadata)` for better type info passing
- Simplified import statements in convert_url function

### Fixed

- Removed redundant local imports causing UnboundLocalError

---

## [0.4.1] - 2026-03-29

### Changed

- Simplified STT (Speech-to-Text) parameters across all audio/video transcription endpoints
- All transcription endpoints now use fixed optimal settings:
  - `device=auto` (auto-detect CPU/GPU)
  - `cpu_threads=0` (auto-detect)
  - `vad_enabled=true` (Voice Activity Detection)
  - `enable_chunking=true` (chunked transcription for long files)
  - `chunk_duration=60` (seconds per chunk)
  - `chunk_overlap=2` (seconds overlap between chunks)
  - `auto_chunk_threshold=90` (auto-enable chunking for files > 90 seconds)

### Fixed

- Latin-1 encoding error when downloading files with non-ASCII (Chinese) filenames
- LSP type error: `accept_language: str = None` → `accept_language: Optional[str] = None`
- LSP error: `transcribe_youtube_video` receiving `None` for language parameter

### Added

- New `api/chunking.py` module for audio chunking support
- Unit tests for chunking functionality

---

## [0.4.0] - 2026-03-19

### Changed

- Migrated from subprocess CLI calls to native Python SDK APIs for better performance and error handling
- yt-dlp CLI calls replaced with yt-dlp Python SDK (`YouTubeClient` module)
- ffmpeg CLI calls replaced with ffmpeg-python SDK (`audio_extractor` module)
- tesseract CLI calls replaced with pytesseract SDK (`ocr_client` module)
- Python dependency management switched from pip to uv
- Removed `markitdown-ocr` dependency (using custom `ocr_client` module instead)

### Added

- New SDK modules: `api/youtube_client.py`, `api/audio_extractor.py`, `api/ocr_client.py`
- Unit tests for all new SDK modules with >80% coverage
- `pyproject.toml` for modern Python project configuration
- `Makefile` with common development commands
- Proper exception hierarchy for each SDK module
- `DEFAULT_OCR_LANG` constant to `api/constants.py`

### Performance

- Reduced process fork overhead (~50-200ms per call) by using native SDK APIs
- Improved error handling with structured Python exceptions

---

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

[0.8.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/poyhsiao/oh-my-markitdown/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/poyhsiao/oh-my-markitdown/releases/tag/v0.0.1