# MarkItDown API Docker

> **Based on:** [microsoft/markitdown](https://github.com/microsoft/markitdown)  
> **Original Project:** Microsoft MarkItDown - Python tool for converting various files to Markdown

Convert various file formats to Markdown via HTTP API with multi-language OCR support and **YouTube video transcription using Faster-Whisper**!

**[繁體中文版](README_ZH_TW.md)** | **[English](README.md)** | **[CHANGELOG](CHANGELOG.md)**

---

## Table of Contents

- [Features](#features)
- [Supported Formats](#supported-formats)
- [OCR Multi-Language Support](#ocr-multi-language-support)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Usage](#api-usage)
- [Auto-Convert Feature](#auto-convert-feature)
- [CLI Tool](#cli-tool)
- [Documentation](#documentation)

---

## Features

- **7 Asian Language OCR**: Traditional Chinese, Simplified Chinese, English, Japanese, Korean, Thai, Vietnamese
- **YouTube Video Transcription**: Download audio and transcribe using **Faster-Whisper** (local, no API limits!) with **subtitle priority for 10-100x speedup**
- **Audio File Transcription**: Upload MP3/WAV/M4A and convert to text
- **Instant Conversion**: Upload files and get Markdown immediately
- **Dual Format Output**: Support `markdown` or `json` format
- **Environment Variables**: Configurable ports, paths, OCR languages
- **Batch Processing**: Support directory batch conversion
- **Auto-Monitoring**: Automatically convert files in `input/` to `output/`
- **CLI Tool**: Flexible command-line tool for files/URLs/batch processing
- **Swagger UI**: Complete interactive API documentation
- **Health Checks**: Built-in health check endpoints
- **Resource Limits**: Adjustable memory and CPU limits

---

## Supported Formats

| Type | Formats |
|------|---------|
| **Documents** | PDF, Word (DOCX/DOC), PowerPoint (PPTX/PPT), Excel (XLSX/XLS), Outlook (MSG) |
| **Web** | HTML, URLs (including YouTube subtitles) |
| **Images** | JPG, PNG, GIF, WEBP, BMP, TIFF (with EXIF + Multi-language OCR) |
| **Audio** | MP3, WAV, M4A, FLAC, OGG (with speech transcription) |
| **Data** | CSV, JSON, XML |
| **Other** | ZIP (iterate contents), EPub |

### Installed System Dependencies

| Tool/Library | Purpose |
|--------------|---------|
| `poppler-utils` | PDF processing (pdfminer.six, pdfplumber) |
| `exiftool` | Image/Audio EXIF metadata extraction |
| `tesseract-ocr` + language packs | Multi-language OCR (7 Asian languages) |
| `ffmpeg` | Audio processing (pydub, SpeechRecognition) |
| `fonts-liberation` / `fonts-noto-cjk` | Font support (CJK characters) |
| `libxml2-dev` / `libxslt1-dev` | Office file processing (mammoth, lxml) |
| `build-essential` | Python dependency build tools |

### SDK Migration (v0.4.0)

This project now uses **native Python SDK APIs** instead of subprocess CLI calls for better performance and error handling:

| Component | Before | After |
|-----------|--------|-------|
| **YouTube Download** | `yt-dlp` CLI | `yt-dlp` Python SDK |
| **Audio Extraction** | `ffmpeg` CLI | `ffmpeg-python` SDK |
| **OCR Processing** | `tesseract` CLI | `pytesseract` SDK |

**Benefits:**
- Reduced process fork overhead (~50-200ms per call)
- Structured Python exceptions for better error handling
- Easier debugging and testing
- Type-safe API interactions

**New SDK Modules:**
- `api/youtube_client.py` - YouTube video/audio download
- `api/audio_extractor.py` - Audio extraction and processing
- `api/ocr_client.py` - OCR with multi-language support

For implementation details, see the respective module files.

---

## OCR Multi-Language Support

| Language Code | Language | Writing System | Use Case |
|---------------|----------|----------------|----------|
| `chi_tra` | Traditional Chinese | Traditional Han | Taiwan, Hong Kong, Macau |
| `chi_sim` | Simplified Chinese | Simplified Han | Mainland China |
| `eng` | English | Latin | English documents |
| `jpn` | Japanese | Kanji + Kana | Japanese documents |
| `kor` | Korean | Hangul | Korean documents |
| `tha` | Thai | Thai Script | Thai documents |
| `vie` | Vietnamese | Quoc Ngu | Vietnamese documents |

### Language Combinations

Use `+` to combine multiple languages:

| Combination | Description |
|-------------|-------------|
| `chi_tra+eng` | Traditional Chinese + English (**Default**) |
| `chi_sim+eng` | Simplified Chinese + English |
| `chi_tra+jpn+kor+eng` | Northeast Asian multi-language |
| `tha+eng` | Thai + English |
| `vie+eng` | Vietnamese + English |
| `chi_tra+tha+vie+eng` | Southeast Asian multi-language |
| `chi_tra+chi_sim+eng+jpn+kor+tha+vie` | **Complete Asian (all 7 languages)** |

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/poyhsiao/oh-my-markitdown.git
cd oh-my-markitdown
```

### 2. Configure Environment Variables (Optional)

```bash
# Copy example configuration (first time only)
cp .env.example .env

# Edit configuration (adjust port, OCR language, etc.)
nano .env
```

### 3. Build and Start Services

```bash
# Build Docker image (first time takes ~8-15 minutes)
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

Services will start at **http://localhost:51083** (or your configured port)!

### 4. Test Services

```bash
# Health check
curl http://localhost:51083/health

# View supported formats
curl http://localhost:51083/api/v1/formats

# View OCR language support
curl http://localhost:51083/api/v1/ocr-languages

# View current configuration
curl http://localhost:51083/api/v1/config
```

---

## Environment Variables

### Quick Start

```bash
# 1. Copy example configuration
cp .env.example .env

# 2. Edit configuration
nano .env

# 3. Restart services
docker compose restart
```

### Complete Configuration List

| Variable | Default | Description |
|----------|---------|-------------|
| **API Ports** |
| `API_PORT` | `51083` | External exposed port (browser access) |
| `API_PORT_INTERNAL` | `8000` | Internal container port |
| `API_HOST` | `0.0.0.0` | API listen address |
| `API_DEBUG` | `false` | Debug mode (true/false) |
| `API_WORKERS` | `1` | Worker count (recommend: CPU cores) |
| **Directory Config** |
| `DATA_DIR` | `./data` | Data persistence directory |
| `INPUT_DIR` | `./input` | Input file directory (batch processing) |
| `OUTPUT_DIR` | `./output` | Output file directory (batch processing) |
| **OCR Config** |
| `DEFAULT_OCR_LANG` | `chi_tra+eng` | Default OCR language |
| `ENABLE_PLUGINS_BY_DEFAULT` | `false` | Enable plugins by default |
| **Upload Limits** |
| `MAX_UPLOAD_SIZE` | `52428800` | Max upload size (bytes, default 50MB) |
| **Resource Limits** |
| `MEMORY_LIMIT` | `2G` | Memory limit |
| `CPU_LIMIT` | `2.0` | CPU limit (cores) |
| **OpenAI (Optional)** |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API endpoint |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| **Azure (Optional)** |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | - | Azure Document Intelligence endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | - | Azure Document Intelligence Key |

For detailed configuration examples, see [CONFIG_GUIDE.md](CONFIG_GUIDE.md).

---

## API Usage

### API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API Homepage (version info) |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/formats` | View supported file formats |
| `GET` | `/api/v1/ocr-languages` | View OCR language support |
| `GET` | `/api/v1/config` | View current configuration |
| `GET` | `/api/v1/device-info` | Get compute device info (CPU/GPU) |
| `POST` | `/api/v1/convert` | Upload file and convert |
| `POST` | `/api/v1/convert/youtube` | YouTube video transcription (Faster-Whisper) |
| `POST` | `/api/v1/convert/audio` | Audio file transcription (Faster-Whisper) |
| `POST` | `/api/v1/convert/video` | Video file transcription (Faster-Whisper) |
| `GET` | `/api/v1/convert/languages` | Supported transcription languages |
| `GET` | `/docs` | Swagger UI interactive docs |
| `GET` | `/redoc` | ReDoc documentation |

### Quick Examples

**Basic conversion:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

**OCR with Traditional Chinese:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md
```

**YouTube transcription:**
```bash
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=https://www.youtube.com/watch?v=VIDEO_ID&language=zh" \
  -o transcript.md
```

**GPU-accelerated transcription (new in v0.3.0):**
```bash
# Check available devices
curl http://localhost:51083/api/v1/device-info

# Use CUDA for faster transcription
curl -X POST "http://localhost:51083/api/v1/convert/audio?device=cuda" \
  -F "file=@audio.mp3" \
  -o transcript.md
```

For complete API documentation, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Auto-Convert Feature

Place files in `input/` directory, they will be automatically converted to Markdown in `output/`!

```bash
# 1. Confirm .env configuration
AUTO_ENABLED=true
AUTO_POLL_INTERVAL=5

# 2. Start services
docker compose up -d

# 3. Place files
cp document.pdf input/

# 4. Wait a few seconds, check output
ls output/
# Output: document.md
```

**For detailed instructions see:** [AUTO_CONVERT.md](AUTO_CONVERT.md)

---

## CLI Tool

### Quick Usage

```bash
# Convert single file
./markitdown document.pdf output.md

# Convert from URL
./markitdown --url https://example.com output.md

# Batch convert
./markitdown *.pdf -o ./output/

# View help
./markitdown --help
```

**For detailed instructions see:** [CLI_USAGE.md](CLI_USAGE.md)

---

## Documentation

### API & Configuration

- **[API Reference](docs/API_REFERENCE.md)** - Complete API endpoint documentation
- **[Code Examples](docs/CODE_EXAMPLES.md)** - Python, cURL, and Node.js examples
- **[Advanced Configuration](docs/ADVANCED_CONFIG.md)** - OpenAI, Azure, and Docker configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Feature Guides

- **[AUTO_CONVERT.md](AUTO_CONVERT.md)** - Auto-convert feature guide
- **[CLI_USAGE.md](CLI_USAGE.md)** - CLI tool usage guide
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Configuration guide
- **[System Management](docs/SYSTEM_MANAGEMENT.md)** - Storage, cleanup, and monitoring

---

## System Management

For monitoring and cleanup operations, see [System Management Guide](docs/SYSTEM_MANAGEMENT.md).

**Quick commands:**

```bash
# Check storage usage
python scripts/storage.py

# Clean temporary files (preview)
python scripts/cleanup.py --dry-run

# Clean temporary files (execute)
python scripts/cleanup.py --force
```

**API endpoints:**

```bash
# Query storage
curl http://localhost:51083/api/v1/admin/storage

# Cleanup all temporary files
curl -X POST http://localhost:51083/api/v1/admin/cleanup \
  -H "Content-Type: application/json" \
  -d '{"targets": ["all"]}'

# Manage model cache
curl http://localhost:51083/api/v1/admin/models
curl -X DELETE http://localhost:51083/api/v1/admin/models
```

---

## Stop and Cleanup

```bash
# Stop services
docker compose down

# Stop and remove images
docker compose down --rmi all

# View logs
docker compose logs -f

# Restart
docker compose restart

# Rebuild
docker compose build --no-cache
docker compose up -d

# Test dependencies
./scripts/test-deps.sh
```

---

## API Interactive Documentation

After starting services, visit:

- **Swagger UI**: http://localhost:51083/docs
- **ReDoc**: http://localhost:51083/redoc

---

## License

MarkItDown is open-sourced by Microsoft under the MIT License.

**Original Project:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

---

## Support

For issues, please check:

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR Documentation](https://tesseract-ocr.github.io/)

---

## Related Documentation

- **[繁體中文說明](README_ZH_TW.md)** - Traditional Chinese documentation
- **[AUTO_CONVERT.md](AUTO_CONVERT.md)** - Auto-convert feature guide
- **[CLI_USAGE.md](CLI_USAGE.md)** - CLI tool usage guide
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Configuration guide

---

**Created by:** Kimhsiao  
**Last Updated:** 2026-03-19  
**Version:** 0.4.0  
**API Port:** 51083 (adjustable via `API_PORT` environment variable)  
**Supported Languages:** Traditional Chinese, Simplified Chinese, English, Japanese, Korean, Thai, Vietnamese  
**New Features:** YouTube transcription, Audio transcription (Faster-Whisper), GPU Acceleration (CUDA/MPS), System Management API, SDK Migration (native Python APIs)