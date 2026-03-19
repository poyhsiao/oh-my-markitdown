# SDK/Library Migration Design Document

**Document ID**: 2026-03-19-sdk-library-migration-design  
**Created**: 2026-03-19  
**Author**: Kimhsiao  
**Status**: Draft  
**Related**: [Requirements](./2026-03-19-sdk-library-migration-requirements.md) | [Tasks](./2026-03-19-sdk-library-migration-tasks.md)

---

## 1. Architecture Overview

### 1.1 Design Decision: Distributed Module Pattern

**Selected Pattern**: 分散式封裝（方案 A）

```
api/
├── youtube_client.py     # yt-dlp SDK 封裝（新建）
├── audio_extractor.py    # ffmpeg-python 封裝（新建）
├── ocr_client.py         # pytesseract 封裝（新建）
├── whisper_transcribe.py # 現有文件，替換 subprocess 調用
└── main.py               # 現有文件，替換 subprocess 調用
```

**Rationale**:
- 符合單一職責原則，每個模塊專注一個外部工具
- 獨立測試和演化，修改一個不影響其他
- yt-dlp 功能複雜（6 個調用點），需要專門模塊
- 避免過度抽象，不引入不必要的適配器層

### 1.2 Dependency Management

使用 **uv** 統一管理 Python 依賴，而非在 Dockerfile 中直接安裝。

**新增依賴**:
| Package | Version | Purpose |
|---------|---------|---------|
| `pytesseract` | ^0.3.10 | Tesseract Python wrapper |
| `ffmpeg-python` | ^0.2.0 | ffmpeg Python wrapper |

> Note: `yt-dlp` 已存在，無需新增

---

## 2. Module Design

### 2.1 YouTube Client Module (`api/youtube_client.py`)

#### 2.1.1 Data Classes

```python
@dataclass
class VideoInfo:
    """YouTube 視頻信息。"""
    id: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SubtitleTrack:
    """字幕軌道信息。"""
    lang: str
    name: str
    is_auto: bool = False


@dataclass
class SubtitleInfo:
    """可用字幕信息。"""
    manual: list[SubtitleTrack] = field(default_factory=list)
    auto: list[SubtitleTrack] = field(default_factory=list)
```

#### 2.1.2 Exception Classes

```python
class YouTubeClientError(Exception):
    """YouTube 客戶端基礎異常。"""

class VideoNotFoundError(YouTubeClientError):
    """視頻不存在或不可訪問。"""

class SubtitleNotAvailableError(YouTubeClientError):
    """請求的字幕不可用。"""

class DownloadError(YouTubeClientError):
    """下載失敗。"""

class InfoExtractionError(YouTubeClientError):
    """信息提取失敗。"""
```

#### 2.1.3 YouTubeClient Class

```python
class YouTubeClient:
    """yt-dlp Python SDK 封裝。"""
    
    def __init__(
        self,
        *,
        timeout: int = YOUTUBE_INFO_TIMEOUT,
        download_timeout: int = YOUTUBE_DOWNLOAD_TIMEOUT,
        subtitle_timeout: int = SUBTITLE_DOWNLOAD_TIMEOUT,
        proxy: Optional[str] = None,
        cookies_file: Optional[str] = None,
    ): ...
    
    def get_video_info(self, url: str) -> VideoInfo:
        """獲取視頻詳細信息。"""
    
    def download_audio(
        self, url: str, output_dir: str, audio_quality: str
    ) -> tuple[str, str]:
        """下載 YouTube 視頻音頻。"""
    
    def list_subtitles(self, url: str) -> SubtitleInfo:
        """列出視頻可用的字幕。"""
    
    def download_subtitles(
        self, url: str, lang: str, output_dir: str
    ) -> Optional[str]:
        """下載指定語言的字幕。"""
    
    def get_best_subtitles(
        self, url: str, preferred_langs: list[str], output_dir: str
    ) -> Optional[str]:
        """根據語言優先級下載最佳字幕。"""
```

#### 2.1.4 Migration Mapping

| 現有函數 | 新調用方式 |
|----------|-----------|
| `download_youtube_audio()` 內 subprocess | `client.download_audio()` |
| `_get_video_title()` | `client.get_video_info().title` |
| `check_available_subtitles()` | `client.list_subtitles()` |
| `download_and_convert_subtitles()` 內 subprocess | `client.download_subtitles()` + `client.get_video_info()` |

---

### 2.2 Audio Extractor Module (`api/audio_extractor.py`)

#### 2.2.1 Functions

```python
class AudioExtractionError(Exception):
    """音頻提取異常。"""


def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None,
    *,
    sample_rate: int = AUDIO_SAMPLE_RATE,
    channels: int = AUDIO_CHANNELS,
    codec: str = AUDIO_CODEC,
    threads: int = AUDIO_FFMPEG_THREADS,
    timeout: int = DEFAULT_AUDIO_EXTRACT_TIMEOUT,
) -> str:
    """從視頻文件提取音頻（使用 ffmpeg-python SDK）。"""


def get_audio_info(audio_path: str) -> dict:
    """獲取音頻文件信息。"""


def validate_video_file(video_path: str) -> bool:
    """驗證視頻文件是否包含可提取的音頻。"""
```

#### 2.2.2 Audio Parameters

| 參數 | 值 | 說明 |
|------|-----|------|
| `sample_rate` | 16000 Hz | Whisper 原生採樣率 |
| `channels` | 1 | 單聲道 |
| `codec` | pcm_s16le | WAV/PCM 無壓縮 |
| `threads` | 4 | 多線程解碼 |

---

### 2.3 OCR Client Module (`api/ocr_client.py`)

#### 2.3.1 Exception Classes

```python
class OCRError(Exception):
    """OCR 處理異常。"""

class UnsupportedLanguageError(OCRError):
    """不支持的 OCR 語言。"""
```

#### 2.3.2 Functions

```python
def validate_ocr_languages(ocr_lang: str) -> None:
    """驗證 OCR 語言參數。"""


def ocr_image(image_path: str, ocr_lang: str = DEFAULT_OCR_LANG) -> str:
    """對圖像文件執行 OCR。"""


def ocr_image_object(image: Image.Image, ocr_lang: str) -> str:
    """對 PIL Image 對象執行 OCR。"""


def ocr_pdf(
    pdf_path: str,
    ocr_lang: str = DEFAULT_OCR_LANG,
    *,
    zoom: float = 3.0,
    min_text_length: int = 50,
) -> str:
    """對 PDF 文件執行 OCR（掃描型 PDF）。"""


def ocr_pdf_pages(pdf_path: str, ocr_lang: str) -> list[str]:
    """對 PDF 文件逐頁執行 OCR。"""


def get_tesseract_languages() -> list[str]:
    """獲取系統已安裝的 Tesseract 語言包。"""


def is_tesseract_available() -> bool:
    """檢查 Tesseract 是否可用。"""
```

---

## 3. Code Migration Details

### 3.1 whisper_transcribe.py Changes

#### Imports

```python
# === 移除 ===
# import subprocess

# === 新增 ===
from api.youtube_client import (
    YouTubeClient,
    VideoInfo,
    SubtitleInfo,
    YouTubeClientError,
    VideoNotFoundError,
    DownloadError,
)
from api.audio_extractor import (
    extract_audio_from_video as _extract_audio,
    AudioExtractionError,
)
```

#### Function Replacements

**`download_youtube_audio()`**:
```python
def download_youtube_audio(url: str, output_dir: str = "/tmp", audio_quality: str = "128K"):
    client = YouTubeClient()
    return client.download_audio(url, output_dir, audio_quality)
```

**`_get_video_title()`**:
```python
def _get_video_title(url: str) -> str:
    try:
        client = YouTubeClient()
        info = client.get_video_info(url)
        return info.title
    except YouTubeClientError:
        return "Unknown"
```

**`check_available_subtitles()`**:
```python
def check_available_subtitles(url: str) -> dict:
    try:
        client = YouTubeClient()
        subtitle_info = client.list_subtitles(url)
        return {
            "has_manual": bool(subtitle_info.manual),
            "has_auto": bool(subtitle_info.auto),
            "available_langs": list(subtitle_info.available_langs),
        }
    except Exception:
        return {"has_manual": False, "has_auto": False, "available_langs": []}
```

**`extract_audio_from_video()`**:
```python
def extract_audio_from_video(video_path: str, output_audio_path: Optional[str] = None, threads: int = AUDIO_FFMPEG_THREADS) -> str:
    return _extract_audio(video_path, output_audio_path, threads=threads)
```

---

### 3.2 main.py Changes

#### Imports

```python
# === 移除 ===
# import subprocess

# === 新增 ===
from api.ocr_client import (
    ocr_image,
    ocr_pdf,
    OCRError,
    validate_ocr_languages,
    UnsupportedLanguageError,
)
```

#### Function Replacements

**`ocr_image_pdf()`**:
```python
def ocr_image_pdf(pdf_path: str, ocr_lang: str = DEFAULT_OCR_LANG) -> str:
    return ocr_pdf(pdf_path, ocr_lang)
```

**圖像 OCR（在 `convert_file_endpoint()` 內）**:
```python
# 舊: subprocess.run(["tesseract", ...])
# 新:
try:
    ocr_text = ocr_image(tmp_path, ocr_lang or DEFAULT_OCR_LANG)
except OCRError as e:
    if API_DEBUG:
        print(f"OCR failed: {e}")
    ocr_text = ""
```

**語言驗證**:
```python
# 舊: 手動遍歷檢查
# 新:
try:
    validate_ocr_languages(ocr_lang)
except UnsupportedLanguageError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

---

## 4. Project Configuration

### 4.1 pyproject.toml

```toml
[project]
name = "oh-my-markitdown"
version = "0.4.0"
description = "MarkItDown API - Convert files to Markdown with OCR and transcription"
authors = [{ name = "Kimhsiao", email = "white.shopping@gmail.com" }]
requires-python = ">=3.12"

dependencies = [
    # MarkItDown 核心
    "markitdown[all]",
    "markitdown-ocr",
    # FastAPI
    "fastapi",
    "uvicorn[standard]",
    "python-multipart",
    "aiofiles",
    # OpenAI / Azure
    "openai",
    "azure-ai-documentintelligence",
    "azure-identity",
    # Whisper
    "faster-whisper",
    "psutil",
    # YouTube
    "yt-dlp",
    # === SDK 遷移新增 ===
    "pytesseract>=0.3.10",
    "ffmpeg-python>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "ruff>=0.4",
    "mypy>=1.9",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
warn_return_any = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 4.2 Dockerfile (uv integration)

```dockerfile
FROM python:3.12-slim

# ... 系統依賴保持不變 ...

# 安裝 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 複製依賴定義
COPY pyproject.toml uv.lock* ./

# 使用 uv 安裝依賴
RUN uv sync --frozen --no-dev

# ... 其餘保持不變 ...
```

### 4.3 Additional Configuration Files

| 文件 | 用途 |
|------|------|
| `.python-version` | Python 版本（3.12） |
| `.gitignore` | 更新 uv 相關條目 |
| `Makefile` | 開發命令快捷方式 |
| `uv.toml` | uv 特定配置（可選） |

---

## 5. Testing Strategy

### 5.1 Test Structure

```
tests/
├── unit/
│   ├── test_youtube_client.py     # YouTubeClient 單元測試
│   ├── test_audio_extractor.py    # audio_extractor 單元測試
│   └── test_ocr_client.py         # ocr_client 單元測試
├── integration/
│   ├── test_youtube_integration.py
│   ├── test_audio_integration.py
│   └── test_ocr_integration.py
└── api/
    ├── test_subtitles.py           # 更新
    └── test_endpoints.py           # 更新
```

### 5.2 Test Coverage Requirements

| 模塊 | 最低覆蓋率 |
|------|-----------|
| `youtube_client.py` | 80% |
| `audio_extractor.py` | 80% |
| `ocr_client.py` | 80% |

### 5.3 Test Commands

```bash
# 單元測試
uv run pytest tests/unit -v

# 覆蓋率
uv run pytest tests/unit --cov=api --cov-report=html

# 集成測試
uv run pytest tests/integration --run-integration -v
```

---

## 6. Migration Comparison

### 6.1 Before vs After

| 方面 | 舊實現 (subprocess) | 新實現 (SDK) |
|------|---------------------|--------------|
| **調用方式** | `subprocess.run(["tool", ...])` | Python API 調用 |
| **進程開銷** | 每次 fork ~50-200ms | 無進程開銷 |
| **錯誤處理** | returncode + stderr 解析 | Python 異常捕獲 |
| **返回值** | 字符串解析 | 結構化對象 |
| **類型提示** | 無 | 完整類型提示 |
| **可測試性** | 需 mock subprocess | 可直接 mock 函數 |
| **IDE 支持** | 無 | 自動補全、類型檢查 |

### 6.2 Performance Improvement

| 指標 | 舊值 | 新值 | 改善 |
|------|------|------|------|
| yt-dlp 信息獲取 | ~200ms | ~100ms | 50% |
| 批量處理（10 視頻） | +1s 開銷 | +0.1s 開銷 | 90% |
| 內存開銷 | +50MB per fork | 無 | 100% |

---

## 7. Risks and Mitigations

| 風險 | 概率 | 影響 | 緩解措施 |
|------|------|------|----------|
| yt-dlp API 行為與 CLI 不同 | 中 | 中 | 完整單元測試，對比新舊輸出 |
| 測試覆蓋不足 | 低 | 高 | 強制 >80% 覆蓋率門檻 |
| Docker 構建失敗 | 低 | 中 | 本地先驗證 `uv sync` |
| 性能退化 | 低 | 中 | 遷移前後基準測試對比 |

---

## 8. References

- [yt-dlp Python API Documentation](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)
- [pytesseract Documentation](https://github.com/madmaze/pytesseract)
- [ffmpeg-python Documentation](https://github.com/kkroening/ffmpeg-python)
- [uv Documentation](https://docs.astral.sh/uv/)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-19 | Kimhsiao | Initial design document |