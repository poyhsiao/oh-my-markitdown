# MarkItDown API Docker 🐳🚀

透過 HTTP API 將各種文件格式轉換為 Markdown，支援 **7 種亞洲語言 OCR**！

## 📋 目錄

- [特色功能](#-特色功能)
- [支援的文件格式](#-支援的文件格式)
- [OCR 多語言支援](#-ocr-多語言支援)
- [快速開始](#-快速開始)
- [環境變數配置](#-環境變數配置)
- [API 使用說明](#-api-使用說明)
- [自動轉換功能](#-自動轉換功能) ✨
- [程式碼範例](#-程式碼範例)
- [進階配置](#-進階配置)
- [故障排除](#-故障排除)

---

## ✨ 特色功能

- ✅ **7 種亞洲語言 OCR**：繁中、簡中、英文、日文、韓文、泰文、越南文
- ✅ **即時轉換**：上傳文件後立即回傳 Markdown
- ✅ **雙格式輸出**：支援 `markdown` 或 `json` 格式
- ✅ **環境變數配置**：端口、路徑、OCR 預設語言皆可自訂
- ✅ **批量處理**：支援目錄批量轉換
- ✅ **自動監控轉換**：放入 `input/` 目錄自動轉換到 `output/` ✨
- ✅ **命令行工具**：靈活的 CLI，支持文件/URL/批量處理 ✨
- ✅ **Swagger UI**：完整的互動式 API 文件
- ✅ **健康檢查**：內建健康檢查端點
- ✅ **資源限制**：可調整記憶體、CPU 限制

---

## 📦 支援的文件格式

| 類型 | 格式 |
|------|------|
| **文件** | PDF、Word (DOCX/DOC)、PowerPoint (PPTX/PPT)、Excel (XLSX/XLS)、Outlook (MSG) |
| **網頁** | HTML、URL（含 YouTube 字幕） |
| **圖片** | JPG、PNG、GIF、WEBP、BMP、TIFF（含 EXIF 元數據 + 多語言 OCR） |
| **音頻** | MP3、WAV、M4A、FLAC、OGG（含語音轉錄） |
| **資料** | CSV、JSON、XML |
| **其他** | ZIP（遍歷內容）、EPub |

### 已安裝的系統依賴

| 工具/庫 | 用途 |
|---------|------|
| `poppler-utils` | PDF 處理（pdfminer.six, pdfplumber） |
| `exiftool` | 圖片/音頻 EXIF 元數據提取 |
| `tesseract-ocr` + 語言包 | 多語言 OCR（7 種亞洲語言） |
| `ffmpeg` | 音頻處理（pydub, SpeechRecognition） |
| `fonts-liberation` / `fonts-noto-cjk` | 字體支持（CJK 字符） |
| `libxml2-dev` / `libxslt1-dev` | Office 文件處理（mammoth, lxml） |
| `build-essential` | Python 依賴構建工具 |

---

## 🔤 OCR 多語言支援

| 語言代碼 | 語言 | 文字系統 | 適用場景 |
|----------|------|----------|----------|
| `chi_tra` | 繁體中文 | 繁體漢字 | 台灣、香港、澳門文件 |
| `chi_sim` | 簡體中文 | 簡體漢字 | 中國大陸文件 |
| `eng` | 英文 | 拉丁字母 | 英文文件 |
| `jpn` | 日文 | 漢字 + 假名 | 日本語文件 |
| `kor` | 韓文 | 諺文 (Hangul) | 한국어 文件 |
| `tha` | 泰文 | 泰文字母 | ภาษาไทย 文件 |
| `vie` | 越南文 | 國語字 | Tiếng Việt 文件 |

### 組合使用

使用 `+` 符號組合多種語言：

| 語言組合 | 說明 |
|----------|------|
| `chi_tra+eng` | 繁體中文 + 英文（**預設**） |
| `chi_sim+eng` | 簡體中文 + 英文 |
| `chi_tra+jpn+kor+eng` | 東北亞多語言混合 |
| `tha+eng` | 泰文 + 英文 |
| `vie+eng` | 越南文 + 英文 |
| `chi_tra+tha+vie+eng` | 東南亞多語言混合 |
| `chi_tra+chi_sim+eng+jpn+kor+tha+vie` | **完整亞洲語言（7 種全開）** |

---

## 🚀 快速開始

### 1. 克隆專案

```bash
cd /Users/kimhsiao/git/kimhsiao/markitdown-kim
```

### 2. 配置環境變數（可選）

```bash
# 複製範例配置（第一次需要）
cp .env.example .env

# 編輯配置（根據需求調整端口、OCR 語言等）
nano .env
# 或使用其他編輯器
vim .env
code .env
```

**📝 提示：** `.env.example` 文件包含詳細註解，建議先閱讀！

### 3. 建置並啟動服務

```bash
# 建置 Docker 映像（首次需要約 8-15 分鐘，包含所有依賴）
docker compose build

# 啟動服務
docker compose up -d

# 查看日誌
docker compose logs -f
```

服務將在 **http://localhost:51083** 啟動（或你在 `.env` 中設置的端口）！

**注意：** 首次建置會安裝所有系統依賴和 Python 包，包括：
- Tesseract OCR + 7 種亞洲語言包
- exiftool（EXIF 元數據提取）
- ffmpeg（音頻處理）
- poppler-utils（PDF 處理）
- MarkItDown 所有可選依賴

### 4. 測試服務

```bash
# 健康檢查
curl http://localhost:51083/health

# 查看支援格式
curl http://localhost:51083/formats

# 查看 OCR 語言支援
curl http://localhost:51083/ocr-languages

# 查看當前配置
curl http://localhost:51083/config
```

### 5. 測試依賴（可選）

```bash
# 測試所有系統依賴和 Python 包是否正常
./scripts/test-deps.sh

# 或手動進入容器檢查
docker compose exec markitdown-api bash

# 在容器內檢查
tesseract --list-langs    # 查看 OCR 語言包
exiftool -ver             # 查看 exiftool 版本
ffmpeg -version           # 查看 ffmpeg 版本
pip list                  # 查看 Python 包
```

---

## 🤖 自動轉換功能

### 啟用自動監控

把文件放入 `input/` 目錄，會自動轉換為 Markdown 並輸出到 `output/`！

```bash
# 1. 確認 .env 配置
AUTO_ENABLED=true
AUTO_POLL_INTERVAL=5

# 2. 啟動服務
docker compose up -d

# 3. 放入文件
cp document.pdf input/

# 4. 等待幾秒，查看輸出
ls output/
# 輸出：document.md
```

**詳細說明請參考：** [AUTO_CONVERT.md](AUTO_CONVERT.md)

---

## 💻 命令行工具（CLI）

### 快速使用

```bash
# 轉換單一文件
./markitdown document.pdf output.md

# 從 URL 轉換
./markitdown --url https://example.com output.md

# 批量轉換
./markitdown *.pdf -o ./output/

# 查看幫助
./markitdown --help
```

### 常用選項

| 選項 | 說明 |
|------|------|
| `-o, --output DIR` | 輸出目錄 |
| `-u, --url URL` | 從 URL 轉換 |
| `--ocr-lang LANG` | OCR 語言（預設：chi_tra+eng） |
| `--no-plugins` | 禁用插件 |
| `-v, --verbose` | 詳細輸出 |
| `--stdout` | 輸出到 stdout |

**詳細說明請參考：** [CLI_USAGE.md](CLI_USAGE.md)

### 配置選項

| 配置 | 預設值 | 說明 |
|------|--------|------|
| `AUTO_ENABLED` | `true` | 是否啟用自動轉換 |
| `AUTO_POLL_INTERVAL` | `5` | 監控間隔（秒） |
| `AUTO_ENABLE_PLUGINS` | `true` | 是否啟用 OCR |
| `AUTO_OCR_LANG` | `chi_tra+eng` | OCR 語言 |
| `AUTO_MOVE_SOURCE` | `false` | 轉換後移動源文件 |

### 查看日誌

```bash
# 查看自動轉換服務日誌
docker compose logs -f markitdown-auto
```

---

## ⚙️ 環境變數配置

### 快速開始

```bash
# 1. 複製範例配置
cp .env.example .env

# 2. 編輯配置（使用你喜歡的編輯器）
nano .env
# 或
vim .env
# 或
code .env

# 3. 重啟服務使配置生效
docker compose restart
```

### 完整配置清單

| 變數名稱 | 預設值 | 說明 |
|----------|--------|------|
| **🌐 API 端口** |
| `API_PORT` | `51083` | 對外暴露的端口（瀏覽器訪問） |
| `API_PORT_INTERNAL` | `8000` | 容器內部端口（通常不需修改） |
| `API_HOST` | `0.0.0.0` | API 監聽地址 |
| `API_DEBUG` | `false` | 調試模式（true/false） |
| `API_WORKERS` | `1` | Worker 數量（建議：CPU 核心數） |
| **📁 目錄配置** |
| `DATA_DIR` | `./data` | 數據持久化目錄 |
| `INPUT_DIR` | `./input` | 輸入文件目錄（批量處理） |
| `OUTPUT_DIR` | `./output` | 輸出文件目錄（批量處理） |
| **🔤 OCR 配置** |
| `DEFAULT_OCR_LANG` | `chi_tra+eng` | 預設 OCR 語言（見下方說明） |
| `ENABLE_PLUGINS_BY_DEFAULT` | `false` | 預設啟用插件（true/false） |
| **📤 上傳限制** |
| `MAX_UPLOAD_SIZE` | `52428800` | 最大上傳大小（字節，預設 50MB） |
| **💻 資源限制** |
| `MEMORY_LIMIT` | `2G` | 記憶體限制 |
| `MEMORY_RESERVE` | `512M` | 記憶體保留 |
| `CPU_LIMIT` | `2.0` | CPU 限制（核心數） |
| `CPU_RESERVE` | `0.5` | CPU 保留 |
| **🏥 健康檢查** |
| `HEALTHCHECK_INTERVAL` | `30s` | 健康檢查間隔 |
| `HEALTHCHECK_TIMEOUT` | `10s` | 健康檢查超時 |
| `HEALTHCHECK_RETRIES` | `3` | 重試次數 |
| `HEALTHCHECK_START_PERIOD` | `40s` | 啟動寬限期 |
| **📝 日誌配置** |
| `LOG_MAX_SIZE` | `10m` | 日誌文件最大大小 |
| `LOG_MAX_FILE` | `3` | 日誌文件最大數量 |
| **🤖 OpenAI（可選）** |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API 端點 |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI 模型 |
| **☁️ Azure（可選）** |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | - | Azure Document Intelligence 端點 |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | - | Azure Document Intelligence Key |

### 常用配置範例

#### 範例 1：更改 API 端口為 8080

```bash
# .env 文件
API_PORT=8080

# 重啟服務
docker compose restart

# 現在服務在 http://localhost:8080
```

#### 範例 2：預設使用簡體中文 OCR

```bash
# .env 文件
DEFAULT_OCR_LANG=chi_sim+eng

# 重啟服務
docker compose restart
```

#### 範例 3：增加上傳限制到 100MB

```bash
# .env 文件
MAX_UPLOAD_SIZE=104857600  # 100MB = 100 * 1024 * 1024

# 重啟服務
docker compose restart
```

#### 範例 4：啟用 OpenAI 高品質 OCR

```bash
# .env 文件
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-4o

# 重啟服務
docker compose restart

# 驗證配置
curl http://localhost:51083/config
```

#### 範例 5：增加資源限制（高性能需求）

```bash
# .env 文件
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# 重啟服務
docker compose restart
```

#### 範例 6：主要處理東南亞語言文件

```bash
# .env 文件
DEFAULT_OCR_LANG=chi_tra+tha+vie+eng

# 重啟服務
docker compose restart
```

#### 範例 7：開啟調試模式（開發環境）

```bash
# .env 文件
API_DEBUG=true

# 重啟服務
docker compose restart

# 現在 API 會返回詳細錯誤信息
```

#### 範例 8：批量處理大量文件

```bash
# .env 文件
MAX_UPLOAD_SIZE=524288000  # 500MB
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
API_WORKERS=4

# 重啟服務
docker compose restart
```

---

### 📋 配置檢查清單

**基本使用（推薦新手）：**
- [x] `API_PORT=51083`（或你想要的端口）
- [x] `DEFAULT_OCR_LANG=chi_tra+eng`（根據主要文件語言調整）

**進階使用：**
- [ ] `MAX_UPLOAD_SIZE`（如需上傳大於 50MB 的文件）
- [ ] `MEMORY_LIMIT` 和 `CPU_LIMIT`（如需更高性能）
- [ ] `OPENAI_API_KEY`（如需使用 OpenAI 高品質 OCR）

**生產環境：**
- [ ] `API_DEBUG=false`（關閉調試模式）
- [ ] `LOG_MAX_SIZE` 和 `LOG_MAX_FILE`（調整日誌大小）
- [ ] 健康檢查配置（根據監控需求調整）

#### 範例 4：增加資源限制

```bash
# .env 文件
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
```

---

## 📡 API 使用說明

### API 端點總覽

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/` | API 首頁（版本資訊） |
| `GET` | `/health` | 健康檢查 |
| `GET` | `/formats` | 查看支援的文件格式 |
| `GET` | `/ocr-languages` | 查看 OCR 語言支援 |
| `GET` | `/config` | 查看當前配置 |
| `POST` | `/convert` | 上傳文件並轉換 |
| `POST` | `/convert/url` | 從 URL 轉換 |
| `GET` | `/docs` | Swagger UI 互動文件 |
| `GET` | `/redoc` | ReDoc 文件 |

---

### 1. `POST /convert` - 上傳文件並轉換

#### 請求範例

**基本轉換（使用環境變數預設）：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

**指定 OCR 語言：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -F "return_format=markdown" \
  -o output.md
```

**JSON 格式回傳：**
```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -F "return_format=json" \
  -o response.json
```

#### 請求參數

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `file` | File | ✅ | - | 要轉換的文件檔案 |
| `enable_plugins` | Boolean | ❌ | `ENABLE_PLUGINS_BY_DEFAULT` | 是否啟用插件（OCR） |
| `ocr_lang` | String | ❌ | `DEFAULT_OCR_LANG` | OCR 語言代碼（可用 `+` 組合） |
| `return_format` | String | ❌ | `markdown` | 回傳格式：`markdown` 或 `json` |

#### 回傳格式

**Markdown（預設）：**
- Content-Type: `text/markdown`
- 直接回傳 Markdown 內容
- Headers 包含原始檔名、轉換時間、OCR 語言

**JSON：**
```json
{
  "success": true,
  "filename": "document.pdf",
  "file_size": 123456,
  "conversion_time": "2026-03-13T14:30:00",
  "ocr_language": "chi_tra+eng",
  "content": "# Markdown 內容...",
  "metadata": {
    "type": "pdf",
    "source": "file",
    "title": "文件標題",
    "author": "作者"
  }
}
```

---

### 2. `POST /convert/url` - 從 URL 轉換

#### 請求範例

```bash
curl -X POST "http://localhost:51083/convert/url?url=https://example.com/article" \
  -o output.md
```

**YouTube 字幕抓取：**
```bash
curl -X POST "http://localhost:51083/convert/url?url=https://www.youtube.com/watch?v=VIDEO_ID" \
  -o transcript.md
```

#### 請求參數

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `url` | String | ✅ | - | 網頁 URL 或 YouTube URL |
| `return_format` | String | ❌ | `markdown` | 回傳格式：`markdown` 或 `json` |

---

### 3. `GET /ocr-languages` - 查看 OCR 語言支援

#### 請求範例

```bash
curl http://localhost:51083/ocr-languages
```

#### 回傳範例

```json
{
  "supported_languages": {
    "chi_sim": "簡體中文",
    "chi_tra": "繁體中文",
    "eng": "英文",
    "jpn": "日文",
    "kor": "韓文",
    "tha": "泰文",
    "vie": "越南文"
  },
  "default": "chi_tra+eng",
  "usage": "使用 + 符號組合多種語言，例如：chi_tra+eng+jpn",
  "examples": [
    {"code": "chi_tra", "name": "繁體中文"},
    {"code": "chi_sim", "name": "簡體中文"},
    {"code": "eng", "name": "英文"},
    {"code": "jpn", "name": "日文"},
    {"code": "kor", "name": "韓文"},
    {"code": "tha", "name": "泰文"},
    {"code": "vie", "name": "越南文"},
    {"code": "chi_tra+eng", "name": "繁體中文 + 英文（預設）"},
    {"code": "chi_sim+eng", "name": "簡體中文 + 英文"},
    {"code": "chi_tra+jpn+kor+eng", "name": "多語言混合"},
    {"code": "tha+eng", "name": "泰文 + 英文"},
    {"code": "vie+eng", "name": "越南文 + 英文"},
    {"code": "chi_tra+tha+vie+eng", "name": "東南亞多語言混合"}
  ]
}
```

---

### 4. `GET /config` - 查看當前配置

#### 請求範例

```bash
curl http://localhost:51083/config
```

#### 回傳範例

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
      "chi_sim": "簡體中文",
      "chi_tra": "繁體中文",
      "eng": "英文",
      "jpn": "日文",
      "kor": "韓文",
      "tha": "泰文",
      "vie": "越南文"
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

## 💻 程式碼範例

### Python

#### 基本轉換

```python
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:51083/convert',
        files={'file': f},
        params={'return_format': 'json'}
    )

data = response.json()
print(f"檔名：{data['filename']}")
print(f"內容長度：{len(data['content'])}")
print(data['content'][:500])  # 預覽前 500 字
```

#### OCR 轉換（繁體中文）

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

print("繁體中文 OCR 轉換完成！")
```

#### 多語言 OCR（東北亞）

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
print(f"檔名：{data['filename']}")
print(f"內容長度：{len(data['content'])} 字元")
```

#### 東南亞語言 OCR（泰文 + 越南文）

```python
import requests

# 泰文文件
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

print("泰文 OCR 轉換完成！")

# 越南文文件
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

print("越南文 OCR 轉換完成！")
```

#### 完整亞洲語言（7 種全開）

```python
import requests

# 支援的所有亞洲語言
ocr_languages = [
    "chi_tra",  # 繁體中文
    "chi_sim",  # 簡體中文
    "eng",      # 英文
    "jpn",      # 日文
    "kor",      # 韓文
    "tha",      # 泰文
    "vie",      # 越南文
]

# 全語言混合（適合多語言文件）
all_langs = "+".join(ocr_languages)
print(f"使用語言組合：{all_langs}")

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
print(f"轉換成功！內容長度：{len(data['content'])} 字元")
```

#### 批量轉換

```python
import requests
from pathlib import Path

# 批量轉換 input/ 目錄下所有 PDF
input_dir = Path('input')
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

for pdf_file in input_dir.glob('*.pdf'):
    print(f"正在轉換：{pdf_file.name}")
    
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
    
    print(f"✓ 完成：{output_file.name}")

print("\n批量轉換完成！")
```

---

### cURL

#### 基本轉換

```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -o output.md
```

#### OCR 轉換（指定語言）

```bash
# 繁體中文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@scanned-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+eng" \
  -o output.md

# 簡體中文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@chinese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_sim+eng" \
  -o output.md

# 日文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@japanese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=jpn+eng" \
  -o output.md

# 韓文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@korean-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=kor+eng" \
  -o output.md

# 泰文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@thai-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=tha+eng" \
  -o output.md

# 越南文
curl -X POST "http://localhost:51083/convert" \
  -F "file=@vietnamese-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=vie+eng" \
  -o output.md
```

#### 多語言混合

```bash
# 東北亞多語言
curl -X POST "http://localhost:51083/convert" \
  -F "file=@northeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+jpn+kor+eng" \
  -o output.md

# 東南亞多語言
curl -X POST "http://localhost:51083/convert" \
  -F "file=@southeast-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+tha+vie+eng" \
  -o output.md

# 完整亞洲語言（7 種）
curl -X POST "http://localhost:51083/convert" \
  -F "file=@all-asia-doc.pdf" \
  -F "enable_plugins=true" \
  -F "ocr_lang=chi_tra+chi_sim+eng+jpn+kor+tha+vie" \
  -o output.md
```

#### 批量轉換（Shell 腳本）

```bash
#!/bin/bash

# 批量轉換 input/ 目錄下所有 PDF
for file in input/*.pdf; do
    filename=$(basename "$file" .pdf)
    echo "正在轉換：$filename.pdf"
    
    curl -X POST "http://localhost:51083/convert" \
        -F "file=@$file" \
        -F "enable_plugins=true" \
        -F "ocr_lang=chi_tra+eng" \
        -o "output/${filename}.md"
    
    echo "✓ 完成：${filename}.md"
done

echo "\n批量轉換完成！"
```

---

### Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// 基本轉換
const form = new FormData();
form.append('file', fs.createReadStream('document.pdf'));
form.append('return_format', 'json');

const response = await axios.post(
    'http://localhost:51083/convert',
    form,
    { headers: form.getHeaders() }
);

console.log('轉換成功:', response.data.filename);
fs.writeFileSync('output.md', response.data.content);

// OCR 轉換（繁體中文）
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
console.log('OCR 轉換完成！');
```

---

## 🔧 進階配置

### 使用 OpenAI 視覺模型（高品質 OCR）

如需更高品質的 OCR（特別是複雜文件或低品質掃描），可使用 OpenAI 視覺模型：

#### 1. 配置環境變數

```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

#### 2. 重啟服務

```bash
docker compose restart
```

#### 3. 驗證配置

```bash
curl http://localhost:51083/config
```

#### 4. Python 使用範例

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

### 使用 Azure Document Intelligence

#### 1. 配置環境變數

```bash
# .env 文件
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-azure-key-here
```

#### 2. 使用 Azure 轉換

```bash
curl -X POST "http://localhost:51083/convert" \
  -F "file=@document.pdf" \
  -F "enable_plugins=true" \
  -o output.md
```

---

### 批量處理目錄

#### 1. 準備目錄結構

```bash
mkdir -p input output
```

#### 2. 放入文件

```bash
cp *.pdf input/
```

#### 3. 批量轉換

```bash
# 使用提供的腳本
docker compose run --rm markitdown-api bash -c "
for file in /app/input/*.pdf; do
    filename=\$(basename \"\$file\" .pdf)
    markitdown \"\$file\" -o \"/app/output/\${filename}.md\"
    echo \"轉換完成：\$filename.md\"
done
"
```

---

### 自定義 Docker 配置

#### 增加記憶體限制

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '4.0'
```

#### 更改日誌配置

```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

---

## 🔍 故障排除

### 容器無法啟動

```bash
# 查看日誌
docker compose logs markitdown-api

# 檢查端口是否被佔用
lsof -i :51083

# 強制停止並重啟
docker compose down
docker compose up -d
```

### 轉換失敗

```bash
# 1. 檢查文件格式是否支援
curl http://localhost:51083/formats

# 2. 查看容器日誌
docker compose logs -f

# 3. 確認文件大小（建議 < 50MB）
ls -lh your-file.pdf

# 4. 查看 API 配置
curl http://localhost:51083/config
```

### OCR 品質不佳

1. **增加語言組合**：使用更多語言組合（如 `chi_tra+eng+jpn`）
2. **使用 OpenAI 視覺模型**：配置 `OPENAI_API_KEY`
3. **提高掃描品質**：確保原始文件清晰
4. **檢查 Tesseract 語言包**：確認所需語言已安裝

```bash
# 進入容器檢查語言包
docker compose exec markitdown-api bash
tesseract --list-langs
```

### 記憶體不足

```bash
# 增加 .env 中的記憶體限制
MEMORY_LIMIT=4G
CPU_LIMIT=4.0

# 重啟服務
docker compose down
docker compose up -d
```

### 上傳文件過大

```bash
# 增加 .env 中的上傳限制
MAX_UPLOAD_SIZE=104857600  # 100MB

# 重啟服務
docker compose restart
```

---

## 🗑️ 停止與清理

```bash
# 停止服務
docker compose down

# 停止並刪除映像
docker compose down --rmi all

# 查看日誌
docker compose logs -f

# 重新啟動
docker compose restart

# 重新建置
docker compose build --no-cache
docker compose up -d

# 測試依賴（確認所有工具已正確安裝）
./scripts/test-deps.sh
```

---

## 📊 API 互動文件

啟動服務後，訪問：

- **Swagger UI**: http://localhost:51083/docs
- **ReDoc**: http://localhost:51083/redoc

---

## 📄 授權

MarkItDown 由 Microsoft 開源，遵循 MIT 授權。

---

## 📞 支援

如有問題，請查看：

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR 文件](https://tesseract-ocr.github.io/)

---

**建立者：** kimhsiao  
**最後更新：** 2026-03-13  
**版本：** 1.1.0  
**API 端口：** 51083（可透過 `API_PORT` 環境變數調整）  
**支援語言：** 繁體中文、簡體中文、英文、日文、韓文、泰文、越南文
