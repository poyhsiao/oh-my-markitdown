# MarkItDown API Docker

> **基於：** [microsoft/markitdown](https://github.com/microsoft/markitdown)  
> **原始專案：** Microsoft MarkItDown - 將各種檔案轉換為 Markdown 的 Python 工具

透過 HTTP API 將各種檔案格式轉換為 Markdown，支援多語言 OCR 以及 **使用 Faster-Whisper 進行 YouTube 影片轉錄**！

**[繁體中文版](README_ZH_TW.md)** | **[English](README.md)** | **[CHANGELOG](CHANGELOG.md)**

---

## 目錄

- [功能特色](#功能特色)
- [支援格式](#支援格式)
- [OCR 多語言支援](#ocr-多語言支援)
- [快速開始](#快速開始)
- [環境變數](#環境變數)
- [API 使用](#api-使用)
- [自動轉換功能](#自動轉換功能)
- [CLI 工具](#cli-工具)
- [文件](#文件)

---

## 功能特色

- **7 種亞洲語言 OCR**：繁體中文、簡體中文、英文、日文、韓文、泰文、越南文
- **YouTube 影片轉錄**：下載音訊並使用 **Faster-Whisper** 轉錄（本地處理，無 API 限制！）
- **音訊檔案轉錄**：上傳 MP3/WAV/M4A 並轉換為文字
- **即時轉換**：上傳檔案並立即取得 Markdown
- **雙格式輸出**：支援 `markdown` 或 `json` 格式
- **環境變數**：可設定連接埠、路徑、OCR 語言
- **批次處理**：支援目錄批次轉換
- **自動監控**：自動將 `input/` 中的檔案轉換到 `output/`
- **CLI 工具**：靈活的命令列工具，支援檔案/URL/批次處理
- **Swagger UI**：完整的互動式 API 文件
- **健康檢查**：內建健康檢查端點
- **資源限制**：可調整記憶體和 CPU 限制

---

## 支援格式

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

## OCR 多語言支援

| 語言代碼 | 語言 | 書寫系統 | 使用場景 |
|---------------|----------|----------------|----------|
| `chi_tra` | 繁體中文 | 繁體漢字 | 台灣、香港、澳門 |
| `chi_sim` | 簡體中文 | 簡體漢字 | 中國大陸 |
| `eng` | 英文 | 拉丁字母 | 英文文件 |
| `jpn` | 日文 | 漢字 + 假名 | 日文文件 |
| `kor` | 韓文 | 諺文 | 韓文文件 |
| `tha` | 泰文 | 泰文書寫系統 | 泰文文件 |
| `vie` | 越南文 | 國語字 | 越南文文件 |

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

## 快速開始

### 1. 複製儲存庫

```bash
git clone https://github.com/poyhsiao/oh-my-markitdown.git
cd oh-my-markitdown
```

### 2. 設定環境變數（選用）

```bash
# 複製範例設定（首次使用）
cp .env.example .env

# 編輯設定（調整連接埠、OCR 語言等）
nano .env
```

### 3. 建置並啟動服務

```bash
# 建置 Docker 映像（首次約需 8-15 分鐘）
docker compose build

# 啟動服務
docker compose up -d

# 查看日誌
docker compose logs -f
```

服務將在 **http://localhost:51083** 啟動（或您設定的連接埠）！

### 4. 測試服務

```bash
# 健康檢查
curl http://localhost:51083/health

# 查看支援格式
curl http://localhost:51083/api/v1/formats

# 查看 OCR 語言支援
curl http://localhost:51083/api/v1/ocr-languages

# 查看目前設定
curl http://localhost:51083/api/v1/config
```

---

## 環境變數

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

## CLI 工具

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

**詳細說明請參考：** [CLI_USAGE.md](CLI_USAGE.md)

---

## 文件

### API 與配置

- **[API 參考文件](docs/API_REFERENCE.md)** - 完整 API 端點說明
- **[程式碼範例](docs/CODE_EXAMPLES.md)** - Python、cURL、Node.js 範例
- **[進階配置](docs/ADVANCED_CONFIG.md)** - OpenAI、Azure、Docker 配置
- **[故障排除](docs/TROUBLESHOOTING.md)** - 常見問題與解決方案

### 功能指南

- **[AUTO_CONVERT.md](AUTO_CONVERT.md)** - 自動轉換功能指南
- **[CLI_USAGE.md](CLI_USAGE.md)** - CLI 工具使用說明
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - 配置指南
- **[系統管理](docs/SYSTEM_MANAGEMENT.md)** - 儲存、清理、監控

---

## 系統管理

監控與清理操作請參考 [系統管理指南](docs/SYSTEM_MANAGEMENT.md)。

**快速指令：**

```bash
# 查看儲存空間使用量
python scripts/storage.py

# 清理暫存檔案（預覽）
python scripts/cleanup.py --dry-run

# 清理暫存檔案（執行）
python scripts/cleanup.py --force
```

**API 端點：**

```bash
# 查詢儲存空間
curl http://localhost:51083/api/v1/admin/storage

# 清理所有暫存檔案
curl -X POST http://localhost:51083/api/v1/admin/cleanup \
  -H "Content-Type: application/json" \
  -d '{"targets": ["all"]}'

# 管理模型快取
curl http://localhost:51083/api/v1/admin/models
curl -X DELETE http://localhost:51083/api/v1/admin/models
```

---

## 停止與清理

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

# 測試依賴
./scripts/test-deps.sh
```

---

## API 互動文件

啟動服務後，訪問：

- **Swagger UI**: http://localhost:51083/docs
- **ReDoc**: http://localhost:51083/redoc

---

## 授權

MarkItDown 由 Microsoft 開源，遵循 MIT 授權。

**原始專案：** [microsoft/markitdown](https://github.com/microsoft/markitdown)

---

## 支援

如有問題，請查看：

- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Tesseract OCR 文件](https://tesseract-ocr.github.io/)

---

## 相關文件

- **[English](README.md)** - 英文說明
- **[AUTO_CONVERT.md](AUTO_CONVERT.md)** - 自動轉換功能指南
- **[CLI_USAGE.md](CLI_USAGE.md)** - CLI 工具使用說明
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - 配置指南

---

**建立者：** Kimhsiao  
**最後更新：** 2026-03-17  
**版本：** 0.2.0  
**API 端口：** 51083（可透過 `API_PORT` 環境變數調整）  
**支援語言：** 繁體中文、簡體中文、英文、日文、韓文、泰文、越南文  
**新功能：** YouTube 轉錄、音頻轉錄（Faster-Whisper）、系統管理 API