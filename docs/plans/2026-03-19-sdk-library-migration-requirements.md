# External Tool SDK/Library Migration Requirements

**Document ID**: 2026-03-19-sdk-library-migration-requirements  
**Created**: 2026-03-19  
**Author**: Kimhsiao  
**Status**: Draft  
**Priority**: Medium

---

## 1. Executive Summary

This document outlines the requirements for migrating external tool calls from CLI-based `subprocess` invocations to native Python SDK/Library APIs. The goal is to improve performance, code maintainability, and error handling.

---

## 2. Background

### 2.1 Current State

The project currently invokes external tools via CLI commands using `subprocess.run()`:

| Tool | Current Method | Location | Frequency |
|------|---------------|----------|-----------|
| Tesseract | CLI via subprocess | `api/main.py:91-95, 420-424` | Per OCR request |
| yt-dlp | CLI via subprocess | `api/whisper_transcribe.py:286-290, 302-315, 431-436, 646-651, 735-741, 773-789` | Per YouTube request |
| ffmpeg | CLI via subprocess | `api/whisper_transcribe.py:600-616` | Per video transcription |

### 2.2 Problem Statement

1. **Process Overhead**: Each CLI invocation forks a new process (~50-200ms overhead)
2. **Error Handling**: CLI output parsing is fragile and error-prone
3. **Code Maintainability**: String-based command construction is hard to read and debug
4. **Structured Data**: CLI returns strings that require parsing; APIs return structured objects

### 2.3 Performance Impact Analysis

| Tool | Process Overhead | Processing Time | Overhead Ratio | Impact |
|------|------------------|-----------------|----------------|--------|
| Tesseract | ~50ms | 1-30s | <1% | Low |
| yt-dlp | ~100-200ms | 5-300s | <1% | Medium (batch) |
| ffmpeg | ~50ms | 1-60s | <1% | Low |

> **Note**: While overhead ratio is small for single requests, it accumulates significantly in batch processing scenarios.

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: yt-dlp Migration (High Priority)

**Requirement**: Replace all yt-dlp CLI calls with `yt_dlp` Python API.

**Affected Files**:
- `api/whisper_transcribe.py`
  - Line 286-290: `download_youtube_audio()` - Get video info
  - Line 302-315: `download_youtube_audio()` - Download audio
  - Line 431-436: `_get_video_title()` - Get video title
  - Line 646-651: `check_available_subtitles()` - List subtitles
  - Line 735-741: `download_and_convert_subtitles()` - Get video info
  - Line 773-789: `download_and_convert_subtitles()` - Download subtitles

**Acceptance Criteria**:
- [ ] All `subprocess.run(["yt-dlp", ...])` calls replaced with `yt_dlp.YoutubeDL` API
- [ ] Error handling uses Python exceptions instead of return code checking
- [ ] Structured data (title, video_id, duration) obtained directly from API
- [ ] No regression in functionality (all existing features work)
- [ ] Performance improved by at least 50ms per request

#### FR-2: Tesseract Migration (Low Priority)

**Requirement**: Replace Tesseract CLI calls with `pytesseract` Python API.

**Affected Files**:
- `api/main.py`
  - Line 91-95: `ocr_image_pdf()` - OCR on PDF pages
  - Line 420-424: Image OCR in `convert_file_endpoint()`

**Acceptance Criteria**:
- [ ] All `subprocess.run(["tesseract", ...])` calls replaced with `pytesseract.image_to_string()`
- [ ] Image handling uses PIL Image objects directly
- [ ] No regression in OCR accuracy or supported languages
- [ ] Code is more readable and maintainable

#### FR-3: ffmpeg Migration (Medium Priority)

**Requirement**: Replace ffmpeg CLI calls with `ffmpeg-python` Python API.

**Affected Files**:
- `api/whisper_transcribe.py`
  - Line 600-616: `extract_audio_from_video()` - Audio extraction

**Acceptance Criteria**:
- [ ] `subprocess.run(["ffmpeg", ...])` calls replaced with `ffmpeg-python` API
- [ ] All audio parameters (sample rate, channels, codec) preserved
- [ ] Timeout handling implemented correctly
- [ ] Error messages are clear and actionable

---

### 3.2 Non-Functional Requirements

#### NFR-1: Performance

| Metric | Current | Target |
|--------|---------|--------|
| yt-dlp video info fetch | ~200ms | ~100ms |
| yt-dlp audio download | Unchanged | Unchanged |
| Process memory | +50MB per fork | No forks |
| Batch processing (10 videos) | +1s overhead | +0.1s overhead |

#### NFR-2: Maintainability

- Code using native Python APIs should be more readable
- No string concatenation for command building
- IDE autocomplete and type hints available
- Unit testing easier (mock Python objects vs subprocess)

#### NFR-3: Backward Compatibility

- All existing API endpoints work unchanged
- All environment variables continue to work
- Docker image size should not increase significantly (<50MB)

---

## 4. Technical Design

### 4.1 yt-dlp Migration Design

#### Current Implementation

```python
# api/whisper_transcribe.py:286-298
result = subprocess.run(
    ["yt-dlp", "--no-check-certificate", "--print", "%(title)s|||%(id)s", url],
    capture_output=True, text=True, timeout=YOUTUBE_INFO_TIMEOUT
)

if result.returncode != 0:
    raise Exception(f"Failed to get YouTube info: {result.stderr}")

parts = result.stdout.strip().split("|||")
title = parts[0] if len(parts) > 0 else "Unknown"
video_id = parts[1] if len(parts) > 1 else "unknown"
```

#### Proposed Implementation

```python
import yt_dlp

def get_youtube_info(url: str) -> dict:
    """Get YouTube video information using yt-dlp Python API."""
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'video_id': info.get('id', 'unknown'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
            }
    except yt_dlp.utils.DownloadError as e:
        raise Exception(f"Failed to get YouTube info: {e}")

def download_youtube_audio(url: str, output_dir: str = "/tmp", audio_quality: str = "128K") -> Tuple[str, str]:
    """Download audio from YouTube video using yt-dlp Python API."""
    info = get_youtube_info(url)
    video_id = info['video_id']
    output_path = os.path.join(output_dir, f"{video_id}.mp3")
    
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality,
        }],
        'outtmpl': output_path,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return output_path, info['title']
```

### 4.2 Tesseract Migration Design

#### Current Implementation

```python
# api/main.py:91-95
result = subprocess.run(
    ["tesseract", temp_img, "stdout", "-l", ocr_lang],
    capture_output=True, text=True
)
ocr_text = result.stdout.strip()
```

#### Proposed Implementation

```python
import pytesseract
from PIL import Image

def ocr_image(image_path: str, ocr_lang: str = "chi_tra+eng") -> str:
    """Perform OCR on image using pytesseract."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang=ocr_lang)
    return text.strip()
```

### 4.3 ffmpeg Migration Design

#### Current Implementation

```python
# api/whisper_transcribe.py:600-616
cmd = [
    "ffmpeg", "-threads", str(threads), "-i", video_path,
    "-vn", "-ac", str(AUDIO_CHANNELS), "-ar", str(AUDIO_SAMPLE_RATE),
    "-acodec", AUDIO_CODEC, "-y", output_audio_path
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=AUDIO_EXTRACT_TIMEOUT)
```

#### Proposed Implementation

```python
import ffmpeg

def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None,
    threads: int = AUDIO_FFMPEG_THREADS
) -> str:
    """Extract audio from video file using ffmpeg-python."""
    if output_audio_path is None:
        output_audio_path = tempfile.mktemp(suffix=".wav")
    
    try:
        (
            ffmpeg
            .input(video_path, threads=threads)
            .output(
                output_audio_path,
                vn=None,  # No video
                ac=AUDIO_CHANNELS,
                ar=AUDIO_SAMPLE_RATE,
                acodec=AUDIO_CODEC
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, timeout=AUDIO_EXTRACT_TIMEOUT)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")
    
    return output_audio_path
```

---

## 5. Dependencies

### 5.1 Required Packages

| Package | Version | Purpose | Docker Layer |
|---------|---------|---------|--------------|
| `yt-dlp` | Already installed | YouTube download (Python API) | Already present |
| `pytesseract` | ^0.3.10 | Tesseract Python wrapper | New (minimal) |
| `ffmpeg-python` | ^0.2.0 | ffmpeg Python wrapper | New (minimal) |

### 5.2 Dockerfile Changes

```dockerfile
# Add to pip install section
RUN pip install --no-cache-dir \
    pytesseract \
    ffmpeg-python
```

> **Note**: Both packages are thin Python wrappers, adding <1MB to image size.

---

## 6. Implementation Plan

### Phase 1: yt-dlp Migration (High Priority)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Create wrapper module `api/youtube_client.py` | 2h | None |
| Migrate `download_youtube_audio()` | 2h | Phase 1.1 |
| Migrate `_get_video_title()` | 1h | Phase 1.1 |
| Migrate `check_available_subtitles()` | 2h | Phase 1.1 |
| Migrate `download_and_convert_subtitles()` | 2h | Phase 1.2, 1.3 |
| Update unit tests | 2h | Phase 1.1-1.4 |
| Integration testing | 2h | Phase 1.1-1.5 |

**Total Effort**: ~13 hours

### Phase 2: ffmpeg Migration (Medium Priority)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Add `ffmpeg-python` to dependencies | 0.5h | None |
| Migrate `extract_audio_from_video()` | 2h | Phase 2.1 |
| Update unit tests | 1h | Phase 2.2 |
| Integration testing | 1h | Phase 2.2-2.3 |

**Total Effort**: ~4.5 hours

### Phase 3: Tesseract Migration (Low Priority)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Add `pytesseract` to dependencies | 0.5h | None |
| Migrate `ocr_image_pdf()` | 2h | Phase 3.1 |
| Migrate image OCR in `convert_file_endpoint()` | 1h | Phase 3.1 |
| Update unit tests | 1h | Phase 3.2-3.3 |
| Integration testing | 1h | Phase 3.2-3.4 |

**Total Effort**: ~5.5 hours

---

## 7. Testing Requirements

### 7.1 Unit Tests

- [ ] Test yt-dlp wrapper with mock responses
- [ ] Test pytesseract wrapper with sample images
- [ ] Test ffmpeg-python wrapper with sample videos
- [ ] Test error handling for each wrapper

### 7.2 Integration Tests

- [ ] YouTube video transcription (with subtitles)
- [ ] YouTube video transcription (without subtitles, Whisper fallback)
- [ ] PDF OCR with various languages
- [ ] Image OCR with various formats
- [ ] Video audio extraction

### 7.3 Regression Tests

- [ ] All existing API endpoints return same results
- [ ] Performance benchmarks show improvement

---

## 8. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| yt-dlp API behavior differs from CLI | Medium | Medium | Comprehensive unit tests, compare outputs |
| Python wrappers add unexpected dependencies | Low | Low | Review dependencies before adding |
| Performance regression | Low | Medium | Benchmark before/after migration |
| Breaking changes in wrapper libraries | Low | Medium | Pin versions in requirements |

---

## 9. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Process overhead reduction | 50-200ms per request | Timing logs |
| Code coverage | >80% for new modules | pytest-cov |
| API response time | No regression | Integration tests |
| Docker image size | +<5MB | `docker images` |

---

## 10. References

- [yt-dlp Python API Documentation](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)
- [pytesseract Documentation](https://github.com/madmaze/pytesseract)
- [ffmpeg-python Documentation](https://github.com/kkroening/ffmpeg-python)
- [Faster-Whisper Documentation](https://github.com/guillaumekln/faster-whisper)

---

## 11. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Kimhsiao | 2026-03-19 | - |
| Reviewer | - | - | - |
| Approver | - | - | - |

---

## 12. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-19 | Kimhsiao | Initial draft |