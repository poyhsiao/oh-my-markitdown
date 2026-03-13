# MarkItDown API Docker 🐳🚀

> **Based on:** [microsoft/markitdown](https://github.com/microsoft/markitdown)  
> **Original Project:** Microsoft MarkItDown - Python tool for converting various files to Markdown

Convert various file formats to Markdown via HTTP API with multi-language OCR support for 7 Asian languages!

**[🇹🇼 繁體中文版](README_ZH_TW.md)** | **[🇺🇸 English](README.md)**

---

## 📋 Table of Contents

- [Features](#-features)
- [Supported Formats](#-supported-formats)
- [OCR Multi-Language Support](#-ocr-multi-language-support)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Usage](#-api-usage)
- [Auto-Convert Feature](#-auto-convert-feature)
- [CLI Tool](#-cli-tool)
- [Code Examples](#-code-examples)
- [Advanced Configuration](#-advanced-configuration)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

- ✅ **7 Asian Language OCR**: Traditional Chinese, Simplified Chinese, English, Japanese, Korean, Thai, Vietnamese
- ✅ **Instant Conversion**: Upload files and get Markdown immediately
- ✅ **Dual Format Output**: Support `markdown` or `json` format
- ✅ **Environment Variables**: Configurable ports, paths, OCR languages
- ✅ **Batch Processing**: Support directory batch conversion
- ✅ **Auto-Monitoring**: Automatically convert files in `input/` to `output/` ✨
- ✅ **CLI Tool**: Flexible command-line tool for files/URLs/batch processing ✨
- ✅ **Swagger UI**: Complete interactive API documentation
- ✅ **Health Checks**: Built-in health check endpoints
- ✅ **Resource Limits**: Adjustable memory and CPU limits

---

## 📦 Supported Formats

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

---

## 🔤 OCR Multi-Language Support

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

## 🚀 Quick Start

### 1. Clone the Repository

```bash
cd /Users/kimhsiao/git/kimhsiao/markitdown-kim
```

### 2. Configure Environment Variables (Optional)

```bash
# Copy example configuration (first time only)
cp .env.example .env

# Edit configuration (adjust port, OCR language, etc.)
nano .env
# or
vim .env
# or
code .env
```

**📝 Tip:** `.env.example` contains detailed comments, recommended to read first!

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

**Note:** First build installs all system dependencies and Python packages including:
- Tesseract OCR + 7 Asian language packs
- exiftool (EXIF metadata extraction)
- ffmpeg (audio processing)
- poppler-utils (PDF processing)
- All MarkItDown optional dependencies

### 4. Test Services

```bash
# Health check
curl http://localhost:51083/health

# View supported formats
curl http://localhost:51083/formats

# View OCR language support
curl http://localhost:51083/ocr-languages

# View current configuration
curl http://localhost:51083/config
```

### 5. Test Dependencies (Optional)

```bash
# Test all system dependencies and Python packages
./scripts/test-deps.sh

# Or manually check inside container
docker compose exec markitdown-api bash

# Check inside container
tesseract --list-langs    # View OCR language packs
exiftool -ver             # View exiftool version
ffmpeg -version           # View ffmpeg version
pip list                  # View Python packages
```

---

## ⚙️ Environment Variables

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
| **🌐 API Ports** |
| `API_PORT` | `51083` | External exposed port (browser access) |
| `API_PORT_INTERNAL` | `8000` | Internal container port |
| `API_HOST` | `0.0.0.0` | API listen address |
| `API_DEBUG` | `false` | Debug mode (true/false) |
| `API_WORKERS` | `1` | Worker count (recommend: CPU cores) |
| **📁 Directory Config** |
| `DATA_DIR` | `./data` | Data persistence directory |
| `INPUT_DIR` | `./input` | Input file directory (batch processing) |
| `OUTPUT_DIR` | `./output` | Output file directory (batch processing) |
| **🔤 OCR Config** |
| `DEFAULT_OCR_LANG` | `chi_tra+eng` | Default OCR language |
| `ENABLE_PLUGINS_BY_DEFAULT` | `false` | Enable plugins by default |
| **📤 Upload Limits** |
| `MAX_UPLOAD_SIZE` | `52428800` | Max upload size (bytes, default 50MB) |
| **💻 Resource Limits** |
| `MEMORY_LIMIT` | `2G` | Memory limit |
| `MEMORY_RESERVE` | `512M` | Memory reservation |
| `CPU_LIMIT` | `2.0` | CPU limit (cores) |
| `CPU_RESERVE` | `0.5` | CPU reservation |
| **🏥 Health Checks** |
| `HEALTHCHECK_INTERVAL` | `30s` | Health check interval |
| `HEALTHCHECK_TIMEOUT` | `10s` | Health check timeout |
| `HEALTHCHECK_RETRIES` | `3` | Retry count |
| `HEALTHCHECK_START_PERIOD` | `40s` | Start period |
| **📝 Logging** |
| `LOG_MAX_SIZE` | `10m` | Log file max size |
| `LOG_MAX_FILE` | `3` | Log file max count |
| **🤖 OpenAI (Optional)** |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API endpoint |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| **☁️ Azure (Optional)** |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | - | Azure Document Intelligence endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | - | Azure Document Intelligence Key |

### Common Configuration Examples

#### Example 1: Change API Port to 8080

```bash
# .env file
API_PORT=8080

# Restart services
docker compose restart

# Now service is at http://localhost:8080
```

#### Example 2: Default Simplified Chinese OCR

```bash
# .env file
DEFAULT_OCR_LANG=chi_sim+eng

# Restart services
docker compose restart
```

#### Example 3: Increase Upload Limit to 100MB

```bash
# .env file
MAX_UPLOAD_SIZE=104857600  # 100MB = 100 * 1024 * 1024

# Restart services
docker compose restart
```

#### Example 4: Enable OpenAI High-Quality OCR

```bash
# .env file
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-4o

# Restart services
docker compose restart

# Verify configuration
curl http://localhost:51083/config
```

#### Example 5: Increase Resource Limits (High Performance)

```bash
# .env file
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# Restart services
docker compose restart
```

#### Example 6: Southeast Asian Language Documents

```bash
# .env file
DEFAULT_OCR_LANG=chi_tra+tha+vie+eng

# Restart services
docker compose restart
```

#### Example 7: Enable Debug Mode (Development)

```bash
# .env file
API_DEBUG=true

# Restart services
docker compose restart

# API now returns detailed error messages
```

#### Example 8: Batch Processing Large Files

```bash
# .env file
MAX_UPLOAD_SIZE=524288000  # 500MB
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
API_WORKERS=4

# Restart services
docker compose restart
```

---

### 📋 Configuration Checklist

**Basic Usage (Recommended for Beginners):**
- [x] `API_PORT=51083` (or your preferred port)
- [x] `DEFAULT_OCR_LANG=chi_tra+eng` (adjust based on document language)

**Advanced Usage:**
- [ ] `MAX_UPLOAD_SIZE` (if uploading files > 50MB)
- [ ] `MEMORY_LIMIT` and `CPU_LIMIT` (if higher performance needed)
- [ ] `OPENAI_API_KEY` (if using OpenAI high-quality OCR)

**Production Environment:**
- [ ] `API_DEBUG=false` (disable debug mode)
- [ ] `LOG_MAX_SIZE` and `LOG_MAX_FILE` (adjust log size)
- [ ] Health check configuration (adjust based on monitoring needs)

---

## 📡 API Usage

### API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API Homepage (version info) |
| `GET` | `/health` | Health check |
| `GET` | `/formats` | View supported file formats |
| `GET` | `/ocr-languages` | View OCR language support |
| `GET` | `/config` | View current configuration |
| `POST` | `/convert` | Upload file and convert |
| `POST` | `/convert/url` | Convert from URL |
| `GET` | `/docs` | Swagger UI interactive docs |
| `GET` | `/redoc` | ReDoc documentation |

---

### 1. `POST /convert` - Upload File and Convert

#### Request Example

**Basic conversion (using environment variable defaults):**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

**Specify OCR language:**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -F "return_format=markdown" \
  -o output.md
```

**JSON format response:**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -F "return_format=json" \
  -o response.json
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | ✅ | - | File to convert |
| `enable_plugins` | Boolean | ❌ | `ENABLE_PLUGINS_BY_DEFAULT` | Enable plugins (OCR) |
| `ocr_lang` | String | ❌ | `DEFAULT_OCR_LANG` | OCR language code (combine with `+`) |
| `return_format` | String | ❌ | `markdown` | Response format: `markdown` or `json` |

#### Response Format

**Markdown (Default):**
- Content-Type: `text/markdown`
- Direct Markdown content
- Headers include original filename, conversion time, OCR language

**JSON:**
```json
{
  "success": true,
  "filename": "document.pdf",
  "file_size": 123456,
  "conversion_time": "2026-03-13T14:30:00",
  "ocr_language": "chi_tra+eng",
  "content": "# Markdown Content...",
  "metadata": {
    "type": "pdf",
    "source": "file",
    "title": "Document Title",
    "author": "Author"
  }
}
```

---

### 2. `POST /convert/url` - Convert from URL

#### Request Example

```bash
curl -X POST "http://localhost:51083/convert/url?url=https://example.com/article" \
  -o output.md
```

**YouTube subtitle extraction:**
```bash
curl -X POST "http://localhost:51083/convert/url?url=https://www.youtube.com/watch?v=VIDEO_ID" \
  -o transcript.md
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | String | ✅ | - | Web URL or YouTube URL |
| `return_format` | String | ❌ | `markdown` | Response format: `markdown` or `json` |

---

### 3. `GET /ocr-languages` - View OCR Language Support

#### Request Example

```bash
curl http://localhost:51083/ocr-languages
```

#### Response Example

```json
{
  "supported_languages": {
    "chi_sim": "Simplified Chinese",
    "chi_tra": "Traditional Chinese",
    "eng": "English",
    "jpn": "Japanese",
    "kor": "Korean",
    "tha": "Thai",
    "vie": "Vietnamese"
  },
  "default": "chi_tra+eng",
  "usage": "Combine multiple languages with + symbol, e.g., chi_tra+eng+jpn",
  "examples": [
    {"code": "chi_tra", "name": "Traditional Chinese"},
    {"code": "chi_sim", "name": "Simplified Chinese"},
    {"code": "eng", "name": "English"},
    {"code": "jpn", "name": "Japanese"},
    {"code": "kor", "name": "Korean"},
    {"code": "tha", "name": "Thai"},
    {"code": "vie", "name": "Vietnamese"},
    {"code": "chi_tra+eng", "name": "Traditional Chinese + English (Default)"},
    {"code": "chi_sim+eng", "name": "Simplified Chinese + English"},
    {"code": "chi_tra+jpn+kor+eng", "name": "Multi-language Mix"}
  ]
}
```

---

### 4. `GET /config` - View Current Configuration

#### Request Example

```bash
curl http://localhost:51083/config
```

#### Response Example

```json
{
  "api": {
    "version": "1.1.0",
    "debug": false,
    "max_upload_size": 52428800,
    "max_upload_size_mb": 50
  },
  "ocr": {
    "default_language": "chi_tra+eng",
    "plugins_enabled_by_default": false,
    "supported_languages": {
      "chi_sim": "Simplified Chinese",
      "chi_tra": "Traditional Chinese",
      "eng": "English",
      "jpn": "Japanese",
      "kor": "Korean",
      "tha": "Thai",
      "vie": "Vietnamese"
    }
  },
  "openai": {
    "configured": true,
    "model": "gpt-4o",
    "base_url": "https://api.openai.com/v1"
  }
}
```

---

## 🤖 Auto-Convert Feature

### Enable Auto-Monitoring

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

### Configuration Options

| Config | Default | Description |
|--------|---------|-------------|
| `AUTO_ENABLED` | `true` | Enable auto-convert |
| `AUTO_POLL_INTERVAL` | `5` | Poll interval (seconds) |
| `AUTO_ENABLE_PLUGINS` | `true` | Enable OCR |
| `AUTO_OCR_LANG` | `chi_tra+eng` | OCR language |
| `AUTO_MOVE_SOURCE` | `false` | Move source files after conversion |

### View Logs

```bash
# View auto-convert service logs
docker compose logs -f markitdown-auto
```

---

## 💻 CLI Tool

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

### Common Options

| Option | Description |
|--------|-------------|
| `-o, --output DIR` | Output directory |
| `-u, --url URL` | Convert from URL |
| `--ocr-lang LANG` | OCR language (default: chi_tra+eng) |
| `--no-plugins` | Disable plugins |
| `-v, --verbose` | Verbose output |
| `--stdout` | Output to stdout |

**For detailed instructions see:** [CLI_USAGE.md](CLI_USAGE.md)

---

## 💻 Code Examples

### Python

#### Basic Conversion

```python
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        params={'return_format': 'json'}
    )

data = response.json()
print(f"Filename: {data['filename']}")
print(f"Content length: {len(data['content'])}")
print(data['content'][:500])  # Preview first 500 chars
```

#### OCR Conversion (Traditional Chinese)

```python
import requests

with open('scanned-doc.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'chi_tra+eng',
            'return_format': 'markdown'
        }
    )

with open('output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Traditional Chinese OCR conversion complete!")
```

#### Multi-Language OCR (Northeast Asia)

```python
import requests

with open('mixed-asian-doc.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'chi_tra+eng+jpn+kor',
            'return_format': 'json'
        }
    )

data = response.json()
print(f"Filename: {data['filename']}")
print(f"Content length: {len(data['content'])} chars")
```

#### Southeast Asian Language OCR (Thai + Vietnamese)

```python
import requests

# Thai document
with open('thai-document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'tha+eng',
            'return_format': 'markdown'
        }
    )

with open('thai-output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Thai OCR conversion complete!")

# Vietnamese document
with open('vietnamese-document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': 'vie+eng',
            'return_format': 'markdown'
        }
    )

with open('vietnamese-output.md', 'w', encoding='utf-8') as f:
    f.write(response.text)

print("Vietnamese OCR conversion complete!")
```

#### Complete Asian Language Support (All 7 Languages)

```python
import requests

# All supported Asian languages
ocr_languages = [
    "chi_tra",  # Traditional Chinese
    "chi_sim",  # Simplified Chinese
    "eng",      # English
    "jpn",      # Japanese
    "kor",      # Korean
    "tha",      # Thai
    "vie",      # Vietnamese
]

# All languages combined (suitable for multi-language documents)
all_langs = "+".join(ocr_languages)
print(f"Using language combination: {all_langs}")

with open('multi-lang-asia.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        data={
            'enable_plugins': 'true',
            'ocr_lang': all_langs,
            'return_format': 'json'
        }
    )

data = response.json()
print(f"Conversion successful! Content length: {len(data['content'])} chars")
```

#### Batch Conversion

```python
import requests
from pathlib import Path

# Batch convert all PDFs in input/ directory
input_dir = Path('input')
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

for pdf_file in input_dir.glob('*.pdf'):
    print(f"Converting: {pdf_file.name}")
    
    with open(pdf_file, 'rb') as f:
        response = requests.post(
            'http://localhost:51083/convert',
            files={'file': f},
            data={
                'enable_plugins': 'true',
                'ocr_lang': 'chi_tra+eng'
            }
        )
    
    output_file = output_dir / f"{pdf_file.stem}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"✓ Complete: {output_file.name}")

print("\nBatch conversion complete!")
```

---

### cURL

#### Basic Conversion

```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

#### OCR Conversion (Specify Language)

```bash
# Traditional Chinese
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md

# Simplified Chinese
curl -X POST "http://localhost:51083/convert" \
  -F "file=@chinese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_sim+eng" \
  -o output.md

# Japanese
curl -X POST "http://localhost:51083/convert" \
  -F "file=@japanese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=jpn+eng" \
  -o output.md

# Korean
curl -X POST "http://localhost:51083/convert" \
  -F "file=@korean-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=kor+eng" \
  -o output.md

# Thai
curl -X POST "http://localhost:51083/convert" \
  -F "file=@thai-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=tha+eng" \
  -o output.md

# Vietnamese
curl -X POST "http://localhost:51083/convert" \
  -F "file=@vietnamese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=vie+eng" \
  -o output.md
```

#### Multi-Language Mix

```bash
# Northeast Asian multi-language
curl -X POST "http://localhost:51083/convert" \
  -F "file=@northeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+jpn+kor+eng" \
  -o output.md

# Southeast Asian multi-language
curl -X POST "http://localhost:51083/convert" \
  -F "file=@southeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+tha+vie+eng" \
  -o output.md

# Complete Asian languages (all 7)
curl -X POST "http://localhost:51083/convert" \
  -F "file=@all-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+chi_sim+eng+jpn+kor+tha+vie" \
  -o output.md
```

#### Batch Conversion (Shell Script)

```bash
#!/bin/bash

# Batch convert all PDFs in input/ directory
for file in input/*.pdf; do
    filename=$(basename "$file" .pdf)
    echo "Converting: $filename.pdf"
    
    curl -X POST "http://localhost:51083/convert" \
        -F "file=@$file" \
        -F "enable_plugins=true" \
        -F "ocr_lang=chi_tra+eng" \
        -o "output/${filename}.md"
    
    echo "✓ Complete: ${filename}.md"
done

echo "\nBatch conversion complete!"
```

---

### Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// Basic conversion
const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));
form.append('return_format', 'json');

const response = await axios.post(
    'http://localhost:51083/convert',
    form,
    { headers: form.getHeaders() }
);

console.log('Conversion successful:', response.data.filename);
fs.writeFileSync('output.md', response.data.content);

// OCR conversion (Traditional Chinese)
const ocrForm = new FormData();
ocrForm.append('file', fs.createReadStream('scanned-doc.jpg'));
ocrForm.append('enable_plugins', 'true');
ocrForm.append('ocr_lang', 'chi_tra+eng');
ocrForm.append('return_format', 'markdown');

const ocrResponse = await axios.post(
    'http://localhost:51083/convert',
    ocrForm,
    { headers: ocrForm.getHeaders() }
);

fs.writeFileSync('output-ocr.md', ocrResponse.data);
console.log('OCR conversion complete!');
```

---

## 🔧 Advanced Configuration

### Using OpenAI Vision Model (High-Quality OCR)

For higher quality OCR (especially for complex documents or low-quality scans), use OpenAI vision model:

#### 1. Configure Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

#### 2. Restart Services

```bash
docker compose restart
```

#### 3. Verify Configuration

```bash
curl http://localhost:51083/config
```

#### 4. Python Usage Example

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-api-key-here",
    base_url="https://api.openai.com/v1"
)

md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="gpt-4o"
)

result = md.convert("scanned-document.pdf")
print(result.text_content)
```

---

### Using Azure Document Intelligence

#### 1. Configure Environment Variables

```bash
# .env file
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-azure-key-here
```

#### 2. Use Azure Conversion

```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -F "enable_plugins=true" \
  -o output.md
```

---

### Batch Processing Directory

#### 1. Prepare Directory Structure

```bash
mkdir -p input output
```

#### 2. Place Files

```bash
cp *.pdf input/
```

#### 3. Batch Convert

```bash
# Using provided script
docker compose run --rm markitdown-api bash -c "
for file in /app/input/*.pdf; do
    filename=\$(basename \"\$file\" .pdf)
    markitdown \"\$file\" -o \"/app/output/\${filename}.md\"
    echo \"Conversion complete: \$filename.md\"
done
"
```

---

### Custom Docker Configuration

#### Increase Memory Limit

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '4.0'
```

#### Change Logging Configuration

```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

---

## 🔍 Troubleshooting

### Container Won't Start

```bash
# View logs
docker compose logs markitdown-api

# Check if port is occupied
lsof -i :51083

# Force stop and restart
docker compose down
docker compose up -d
```

### Conversion Failed

```bash
# 1. Check if file format is supported
curl http://localhost:51083/formats

# 2. View container logs
docker compose logs -f

# 3. Confirm file size (recommended < 50MB)
ls -lh your-file.pdf

# 4. View API configuration
curl http://localhost:51083/config
```

### Poor OCR Quality

1. **Increase language combination**: Use more language combinations (e.g., `chi_tra+eng+jpn`)
2. **Use OpenAI vision model**: Configure `OPENAI_API_KEY`
3. **Improve scan quality**: Ensure original document is clear
4. **Check Tesseract language packs**: Confirm required languages are installed

```bash
# Enter container to check language packs
docker compose exec markitdown-api bash
tesseract --list-langs
```

### Insufficient Memory

```bash
# Increase memory limit in .env
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# Restart services
docker compose down
docker compose up -d
```

### Upload File Too Large

```bash
# Increase upload limit in .env
MAX_UPLOAD_SIZE=104857600  # 100MB

# Restart services
docker compose restart
```

---

## 🗑️ Stop and Cleanup

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

# Test dependencies (confirm all tools installed correctly)
./scripts/test-deps.sh
```

---

## 📊 API Interactive Documentation

After starting services, visit:

- **Swagger UI**: http://localhost:51083/docs
- **ReDoc**: http://localhost:51083/redoc

---

## 📄 License

MarkItDown is open-sourced by Microsoft under the MIT License.

**Original Project:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

---

## 📞 Support

For issues, please check:

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR Documentation](https://tesseract-ocr.github.io/)

---

## 🔗 Related Documentation

- **[🇹🇼 繁體中文說明](README_ZH_TW.md)** - Traditional Chinese documentation
- **[AUTO_CONVERT.md](AUTO_CONVERT.md)** - Auto-convert feature guide
- **[CLI_USAGE.md](CLI_USAGE.md)** - CLI tool usage guide
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - Configuration guide
- **[TEST_REPORT.md](output/TEST_REPORT.md)** - YouTube URL conversion test report

---

**Created by:** kimhsiao  
**Last Updated:** 2026-03-13  
**Version:** 1.1.0  
**API Port:** 51083 (adjustable via `API_PORT` environment variable)  
**Supported Languages:** Traditional Chinese, Simplified Chinese, English, Japanese, Korean, Thai, Vietnamese
