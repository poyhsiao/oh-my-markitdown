# SDK/Library Migration Tasks

**Document ID**: 2026-03-19-sdk-library-migration-tasks  
**Created**: 2026-03-19  
**Author**: Kimhsiao  
**Status**: Draft  
**Related**: [Requirements](./2026-03-19-sdk-library-migration-requirements.md) | [Design](./2026-03-19-sdk-library-migration-design.md)

---

## Task Overview

| Phase | Description | Effort | Status |
|-------|-------------|--------|--------|
| Phase 0 | 基礎設施設置 | 1h | [x] Completed |
| Phase 1 | yt-dlp SDK 遷移 | 13h | [x] Completed |
| Phase 2 | ffmpeg-python SDK 遷移 | 4.5h | [x] Completed |
| Phase 3 | pytesseract SDK 遷移 | 5.5h | [x] Completed |
| Phase 4 | 集成測試與文檔 | 3h | [ ] Pending |
| **Total** | | **27h** | |

---

## Phase 0: Infrastructure Setup (1h)

### 0.1 Create pyproject.toml
- [x] Create `pyproject.toml` with project configuration
- [x] Add all dependencies (existing + new)
- [x] Configure ruff, mypy, pytest
- **Effort**: 15min
- **Acceptance**: `uv sync` succeeds

### 0.2 Create .python-version
- [x] Create `.python-version` file with "3.12"
- **Effort**: 5min
- **Acceptance**: File exists

### 0.3 Update .gitignore
- [x] Add uv-related entries (`.uv/`, `uv.lock`)
- [x] Add Python cache entries
- **Effort**: 5min
- **Acceptance**: File updated

### 0.4 Update Dockerfile
- [x] Add uv installation step
- [x] Replace pip install with uv sync
- [x] Remove hardcoded package installation
- **Effort**: 15min
- **Acceptance**: `docker compose build` succeeds

### 0.5 Create Makefile
- [x] Add install, test, lint, format targets
- [x] Add Docker-related targets (build, up, down)
- **Effort**: 10min
- **Acceptance**: `make test` runs successfully

### 0.6 Generate uv.lock
- [x] Run `uv lock` to generate lock file
- **Effort**: 5min
- **Acceptance**: `uv.lock` file exists

### 0.7 Verify Docker Build
- [ ] Build Docker image
- [ ] Start container
- [ ] Verify health check passes
- **Effort**: 5min
- **Acceptance**: `curl http://localhost:51083/health` returns 200

---

## Phase 1: yt-dlp SDK Migration (13h)

### 1.1 Create Module Skeleton
- [x] Create `api/youtube_client.py`
- [x] Add module docstring
- [x] Add imports
- **Effort**: 30min
- **Dependencies**: Phase 0
- **Acceptance**: File exists, `import api.youtube_client` succeeds

### 1.2 Implement Data Classes
- [x] Implement `VideoInfo` dataclass
- [x] Implement `SubtitleTrack` dataclass
- [x] Implement `SubtitleInfo` dataclass
- [x] Add helper methods (duration_formatted, has_subtitles, get_best_track)
- **Effort**: 30min
- **Dependencies**: 1.1
- **Acceptance**: Unit tests pass

### 1.3 Implement Exception Classes
- [x] Implement `YouTubeClientError`
- [x] Implement `VideoNotFoundError`
- [x] Implement `SubtitleNotAvailableError`
- [x] Implement `DownloadError`
- [x] Implement `InfoExtractionError`
- **Effort**: 15min
- **Dependencies**: 1.1
- **Acceptance**: Exceptions can be raised and caught

### 1.4 Implement get_video_info()
- [x] Implement `YouTubeClient._get_base_opts()`
- [x] Implement `YouTubeClient.get_video_info()`
- [x] Handle yt_dlp.utils.DownloadError
- [x] Return VideoInfo object
- **Effort**: 1h
- **Dependencies**: 1.2, 1.3
- **Acceptance**: Unit tests pass

### 1.5 Implement download_audio()
- [x] Implement `YouTubeClient.download_audio()`
- [x] Configure FFmpegExtractAudio postprocessor
- [x] Handle download errors
- [x] Return (path, title) tuple
- **Effort**: 1.5h
- **Dependencies**: 1.4
- **Acceptance**: Unit tests pass

### 1.6 Implement list_subtitles()
- [x] Implement `YouTubeClient.list_subtitles()`
- [x] Parse subtitles and automatic_captions from info
- [x] Return SubtitleInfo object
- [x] Handle errors gracefully (return empty result)
- **Effort**: 1h
- **Dependencies**: 1.2
- **Acceptance**: Unit tests pass

### 1.7 Implement download_subtitles()
- [x] Implement `YouTubeClient.download_subtitles()`
- [x] Configure writesubtitles, writeautomaticsub
- [x] Find and return VTT file path
- [x] Handle errors gracefully
- **Effort**: 1.5h
- **Dependencies**: 1.6
- **Acceptance**: Unit tests pass

### 1.8 Implement get_best_subtitles()
- [x] Implement `YouTubeClient.get_best_subtitles()`
- [x] Use language priority from constants
- [x] Integrate list_subtitles and download_subtitles
- **Effort**: 1h
- **Dependencies**: 1.6, 1.7
- **Acceptance**: Unit tests pass

### 1.9 Write Unit Tests
- [x] Create `tests/unit/test_youtube_client.py`
- [x] Test VideoInfo and SubtitleInfo dataclasses
- [x] Test YouTubeClient methods with mocked yt_dlp
- [x] Test error handling
- [x] Achieve >80% coverage
- **Effort**: 2h
- **Dependencies**: 1.1-1.8
- **Acceptance**: `uv run pytest tests/unit/test_youtube_client.py --cov=api/youtube_client` shows >80%

### 1.10 Migrate whisper_transcribe.py
- [x] Update imports in `api/whisper_transcribe.py`
- [x] Replace `download_youtube_audio()` implementation
- [x] Replace `_get_video_title()` implementation
- [x] Replace `check_available_subtitles()` implementation
- [x] Replace `download_and_convert_subtitles()` implementation
- [x] Remove unused subprocess imports
- **Effort**: 2h
- **Dependencies**: 1.9
- **Acceptance**: All existing tests pass

### 1.11 Update Existing Tests
- [x] Update `tests/api/test_subtitles.py` to use new API
- [x] Mock YouTubeClient instead of subprocess
- [x] Verify all tests pass
- **Effort**: 1h
- **Dependencies**: 1.10
- **Acceptance**: `uv run pytest tests/` passes

### 1.12 Integration Testing
- [ ] Test YouTube video transcription (with subtitles)
- [ ] Test YouTube video transcription (without subtitles)
- [ ] Test subtitle download
- [ ] Verify API endpoint `/api/v1/convert/youtube`
- **Effort**: 1h
- **Dependencies**: 1.11
- **Acceptance**: Manual testing confirms functionality

---

## Phase 2: ffmpeg-python SDK Migration (4.5h)

### 2.1 Create Module Skeleton
- [x] Create `api/audio_extractor.py`
- [x] Add module docstring
- [x] Add imports
- **Effort**: 30min
- **Dependencies**: Phase 0
- **Acceptance**: File exists

### 2.2 Implement extract_audio_from_video()
- [x] Implement `AudioExtractionError` exception
- [x] Implement `extract_audio_from_video()`
- [x] Use ffmpeg.input() and ffmpeg.output() chain
- [x] Handle ffmpeg.Error
- [x] Verify output file creation
- **Effort**: 1h
- **Dependencies**: 2.1
- **Acceptance**: Unit tests pass

### 2.3 Implement Helper Functions
- [x] Implement `get_audio_info()`
- [x] Implement `validate_video_file()`
- [x] Use ffmpeg.probe() for information
- **Effort**: 1h
- **Dependencies**: 2.2
- **Acceptance**: Unit tests pass

### 2.4 Write Unit Tests
- [x] Create `tests/unit/test_audio_extractor.py`
- [x] Test extract_audio_from_video with mocked ffmpeg
- [x] Test get_audio_info
- [x] Test validate_video_file
- [x] Test error handling
- [x] Achieve >80% coverage
- **Effort**: 1h
- **Dependencies**: 2.1-2.3
- **Acceptance**: Coverage >80%

### 2.5 Migrate whisper_transcribe.py
- [x] Add import for audio_extractor
- [x] Replace `extract_audio_from_video()` implementation
- [x] Remove old subprocess-based code
- **Effort**: 30min
- **Dependencies**: 2.4
- **Acceptance**: All tests pass

### 2.6 Integration Testing
- [ ] Test video file transcription
- [ ] Test various video formats (MP4, MKV, AVI)
- [ ] Verify API endpoint `/api/v1/convert/video`
- **Effort**: 30min
- **Dependencies**: 2.5
- **Acceptance**: Manual testing confirms functionality

---

## Phase 3: pytesseract SDK Migration (5.5h)

### 3.1 Create Module Skeleton
- [x] Create `api/ocr_client.py`
- [x] Add module docstring
- [x] Add imports
- **Effort**: 30min
- **Dependencies**: Phase 0
- **Acceptance**: File exists

### 3.2 Implement Exception and Validation
- [x] Implement `OCRError` exception
- [x] Implement `UnsupportedLanguageError` exception
- [x] Implement `validate_ocr_languages()`
- **Effort**: 30min
- **Dependencies**: 3.1
- **Acceptance**: Unit tests pass

### 3.3 Implement Image OCR Functions
- [x] Implement `ocr_image()`
- [x] Implement `ocr_image_object()`
- [x] Use pytesseract.image_to_string()
- [x] Handle pytesseract.TesseractError
- **Effort**: 1h
- **Dependencies**: 3.2
- **Acceptance**: Unit tests pass

### 3.4 Implement PDF OCR Function
- [x] Implement `ocr_pdf()`
- [x] Use PyMuPDF for page rendering
- [x] Detect scanned pages (no text)
- [x] Render to image and OCR
- [x] Handle temporary file cleanup
- **Effort**: 1.5h
- **Dependencies**: 3.3
- **Acceptance**: Unit tests pass

### 3.5 Implement Additional Functions
- [x] Implement `ocr_pdf_pages()` (optional, for per-page results)
- [x] Implement `get_tesseract_languages()`
- [x] Implement `is_tesseract_available()`
- **Effort**: 30min
- **Dependencies**: 3.4
- **Acceptance**: Unit tests pass

### 3.6 Write Unit Tests
- [x] Create `tests/unit/test_ocr_client.py`
- [x] Test validate_ocr_languages
- [x] Test ocr_image with mocked pytesseract
- [x] Test ocr_pdf with mocked fitz
- [x] Test error handling
- [x] Achieve >80% coverage
- **Effort**: 1h
- **Dependencies**: 3.1-3.5
- **Acceptance**: Coverage >80%

### 3.7 Migrate main.py
- [x] Update imports in `api/main.py`
- [x] Replace `ocr_image_pdf()` implementation
- [x] Replace image OCR in `convert_file_endpoint()`
- [x] Replace language validation logic
- [x] Remove unused subprocess imports
- **Effort**: 1h
- **Dependencies**: 3.6
- **Acceptance**: All tests pass

### 3.8 Integration Testing
- [ ] Test PDF OCR with various languages
- [ ] Test image OCR with various formats
- [ ] Test OCR language combinations
- [ ] Verify API endpoint `/api/v1/convert`
- **Effort**: 30min
- **Dependencies**: 3.7
- **Acceptance**: Manual testing confirms functionality

---

## Phase 4: Integration Testing & Documentation (3h)

### 4.1 End-to-End Integration Tests
- [ ] Create `tests/integration/test_sdk_migration.py`
- [ ] Test complete YouTube transcription workflow
- [ ] Test complete video transcription workflow
- [ ] Test complete OCR workflow
- **Effort**: 1h
- **Dependencies**: Phase 1-3
- **Acceptance**: All integration tests pass

### 4.2 Update API Documentation
- [ ] Update OpenAPI schema if needed
- [ ] Verify Swagger UI shows correct info
- [ ] Update API reference documentation
- **Effort**: 30min
- **Dependencies**: 4.1
- **Acceptance**: `/docs` endpoint shows updated info

### 4.3 Update README.md
- [ ] Add SDK migration note to changelog section
- [ ] Update dependency management section (mention uv)
- [ ] Update development setup instructions
- **Effort**: 30min
- **Dependencies**: 4.1
- **Acceptance**: README reflects changes

### 4.4 Update CHANGELOG.md
- [ ] Add version 0.4.0 entry
- [ ] List all changes
- [ ] Note breaking changes (if any)
- **Effort**: 15min
- **Dependencies**: 4.1
- **Acceptance**: CHANGELOG updated

### 4.5 Performance Benchmarks
- [ ] Measure YouTube info fetch time (before/after)
- [ ] Measure batch processing time (before/after)
- [ ] Document improvements
- **Effort**: 30min
- **Dependencies**: Phase 1
- **Acceptance**: Documented performance improvement

### 4.6 Docker Image Size Verification
- [ ] Build new Docker image
- [ ] Compare size with previous version
- [ ] Verify increase <5MB
- **Effort**: 15min
- **Dependencies**: Phase 0
- **Acceptance**: Size increase <5MB

---

## Acceptance Checklist

### Functional
- [ ] YouTube video transcription (with subtitles) works
- [ ] YouTube video transcription (without subtitles, Whisper fallback) works
- [ ] YouTube subtitle download works
- [ ] Video file audio extraction works
- [ ] PDF OCR works (multiple languages)
- [ ] Image OCR works (multiple languages)
- [ ] All existing API endpoints work unchanged

### Performance
- [ ] yt-dlp info fetch reduced by ~100ms
- [ ] Batch processing (10 videos) reduced by ~1s overhead
- [ ] No process fork memory overhead

### Code Quality
- [ ] All new modules have >80% test coverage
- [ ] `ruff check api tests` passes
- [ ] `mypy api` passes
- [ ] No `subprocess` calls remaining for migrated tools

### Docker
- [ ] `docker compose build` succeeds
- [ ] Docker image size increase <5MB
- [ ] All environment variables still work
- [ ] Health check passes

---

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/sdk-library-migration

# Phase 0 commits
git add pyproject.toml .python-version .gitignore Dockerfile Makefile
git commit -m "chore: add uv package management configuration"

# Phase 1 commits
git add api/youtube_client.py tests/unit/test_youtube_client.py
git commit -m "feat: add YouTubeClient with yt-dlp SDK integration"

# Phase 2 commits
git add api/audio_extractor.py tests/unit/test_audio_extractor.py
git commit -m "feat: add audio_extractor with ffmpeg-python SDK integration"

# Phase 3 commits
git add api/ocr_client.py tests/unit/test_ocr_client.py
git commit -m "feat: add ocr_client with pytesseract SDK integration"

# Phase 4 commits
git add docs/ README.md CHANGELOG.md
git commit -m "docs: update documentation for SDK migration"

# Final merge
git checkout main
git merge feature/sdk-library-migration
git tag v0.4.0
```

---

## Rollback Plan

If migration fails:

```bash
# Option 1: Git revert
git revert <commit-hash>

# Option 2: Use backup Docker image
docker tag oh-my-markitdown:latest oh-my-markitdown:backup
docker compose down
# Rebuild with old Dockerfile
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-19 | Kimhsiao | Initial task document |