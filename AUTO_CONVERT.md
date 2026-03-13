# 自動轉換功能說明 🤖

> **基於：** [microsoft/markitdown](https://github.com/microsoft/markitdown)  
> **Original Project:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

MarkItDown API 支援**自動監控目錄**功能，當你把文件放入 `input/` 目錄後，會自動轉換為 Markdown 並輸出到 `output/` 目錄！

**[🇹🇼 繁體中文版](AUTO_CONVERT_ZH_TW.md)** | **[🇺🇸 English](AUTO_CONVERT_EN.md)** *(Coming Soon)*

---

## 🚀 快速開始

### 1. 啟用自動轉換服務

在 `.env` 文件中確認配置：

```bash
# .env 文件
AUTO_ENABLED=true
AUTO_ENABLE_PLUGINS=true
AUTO_OCR_LANG=chi_tra+eng
AUTO_MOVE_SOURCE=false
AUTO_POLL_INTERVAL=5
```

### 2. 啟動服務

```bash
# 啟動 API + 自動轉換服務
docker compose up -d

# 查看自動轉換服務日誌
docker compose logs -f markitdown-auto
```

### 3. 使用方式

```bash
# 把文件放入 input/ 目錄
cp document.pdf input/

# 等待幾秒（預設 5 秒監控間隔）
# 轉換完成的文件會出現在 output/ 目錄
ls output/
# 輸出：document.md
```

---

## 📋 配置說明

### 環境變數

| 變數名稱 | 預設值 | 說明 |
|----------|--------|------|
| `AUTO_ENABLED` | `true` | 是否啟用自動轉換服務 |
| `AUTO_ENABLE_PLUGINS` | `true` | 是否啟用 OCR 插件 |
| `AUTO_OCR_LANG` | `chi_tra+eng` | OCR 語言（可用 `+` 組合） |
| `AUTO_MOVE_SOURCE` | `false` | 轉換後是否移動源文件 |
| `AUTO_POLL_INTERVAL` | `5` | 監控間隔（秒） |
| `AUTO_MAX_RETRIES` | `3` | 轉換失敗最大重試次數 |
| `AUTO_MEMORY_LIMIT` | `1G` | 自動轉換服務記憶體限制 |
| `AUTO_CPU_LIMIT` | `1.0` | 自動轉換服務 CPU 限制 |

---

## 📁 目錄結構

```
markitdown-kim/
├── input/              # 放入待轉換的文件
│   └── .processed/     # 已處理的文件（如果 AUTO_MOVE_SOURCE=true）
├── output/             # 轉換完成的 Markdown 文件
│   ├── document1.md
│   └── document2.md
└── ...
```

---

## 🔧 使用場景

### 場景 1：基本使用（保留源文件）

```bash
# .env 配置
AUTO_MOVE_SOURCE=false

# 使用方式
cp file.pdf input/
# 等待 5 秒
# output/file.md 自動生成
# input/file.pdf 仍然保留
```

### 場景 2：轉換後移動源文件

```bash
# .env 配置
AUTO_MOVE_SOURCE=true

# 使用方式
cp file.pdf input/
# 等待 5 秒
# output/file.md 自動生成
# input/file.pdf 移動到 input/.processed/file.pdf
```

### 場景 3：批量處理

```bash
# 一次性放入多個文件
cp *.pdf input/

# 查看轉換進度
docker compose logs -f markitdown-auto

# 等待所有文件轉換完成
ls output/
```

### 場景 4：調整監控間隔

如果不需要即時轉換，可以延長監控間隔以節省資源：

```bash
# .env 配置
AUTO_POLL_INTERVAL=30  # 30 秒檢查一次

# 重啟服務
docker compose restart markitdown-auto
```

---

## 📊 日誌範例

```
[2026-03-13T15:10:00] 初始化 MarkItDown...
[2026-03-13T15:10:01] 監控服務啟動
  - 輸入目錄：/app/input
  - 輸出目錄：/app/output
  - 啟用插件：true
  - OCR 語言：chi_tra+eng
  - 移動源文件：false
  - 監控間隔：5 秒
--------------------------------------------------
[2026-03-13T15:10:01] 掃描現有文件...
  沒有現有文件
--------------------------------------------------
[2026-03-13T15:10:01] 開始監控（按 Ctrl+C 停止）...

[2026-03-13T15:10:15] 發現 1 個新文件
[2026-03-13T15:10:15] 開始轉換：document.pdf
[2026-03-13T15:10:18] ✓ 轉換成功：document.md
```

---

## ⚠️ 注意事項

### 1. 支援的文件格式

自動轉換支援以下格式：
- PDF, DOCX, DOC, PPTX, PPT
- XLSX, XLS
- HTML, HTM, CSV, JSON, XML
- ZIP, EPUB, MSG
- JPG, JPEG, PNG, GIF, WEBP
- MP3, WAV, M4A, FLAC

### 2. 文件命名規則

- 輸出文件名稱 = 輸入文件名稱（不含擴展名）+ `.md`
- 例如：`document.pdf` → `document.md`

### 3. 重複文件處理

- 如果 `output/` 目錄已有同名文件，會**覆蓋**
- 已處理的文件會被記錄，不會重複轉換（除非重新啟動服務）

### 4. 錯誤處理

- 轉換失敗的文件會保留在 `input/` 目錄
- 服務會持續重試（最多 `AUTO_MAX_RETRIES` 次）
- 查看日誌了解失敗原因

---

## 🛑 停止自動轉換服務

### 暫時停止

```bash
# 停止自動轉換服務（保留 API 服務）
docker compose stop markitdown-auto
```

### 完全禁用

```bash
# .env 文件
AUTO_ENABLED=false

# 重啟
docker compose down
docker compose up -d
```

### 查看日誌

```bash
# 查看即時日誌
docker compose logs -f markitdown-auto

# 查看最近 100 行
docker compose logs --tail=100 markitdown-auto
```

---

## 💡 進階技巧

### 技巧 1：僅使用 API（不使用自動轉換）

如果只想透過 API 上傳文件，不使用自動監控：

```bash
# .env 文件
AUTO_ENABLED=false

# 或只啟動 API 服務
docker compose up -d markitdown-api
```

### 技巧 2：僅使用自動轉換（不啟動 API）

如果只想使用自動監控功能：

```bash
# 只啟動自動轉換服務
docker compose up -d markitdown-auto
```

### 技巧 3：處理大量文件

如果需要批量處理大量文件，建議增加資源：

```bash
# .env 文件
AUTO_MEMORY_LIMIT=2G
AUTO_CPU_LIMIT=2.0
AUTO_POLL_INTERVAL=2  # 縮短監控間隔
```

### 技巧 4：歸檔已處理文件

啟用 `AUTO_MOVE_SOURCE` 自動歸檔：

```bash
# .env 文件
AUTO_MOVE_SOURCE=true

# 已處理的文件會移動到 input/.processed/
ls input/.processed/
```

---

## 🔗 相關文件

- `api/auto_convert.py` - 自動轉換服務代碼
- `docker-compose.yml` - Docker Compose 配置（包含 `markitdown-auto` 服務）
- `.env.example` - 環境變數範例（含自動轉換配置）

---

**最後更新：** 2026-03-13  
**版本：** 1.1.0
