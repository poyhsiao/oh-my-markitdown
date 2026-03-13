# MarkItDown Docker 🐳

使用 Docker 容器輕鬆將各種文件格式轉換為 Markdown！

## 📦 支援的文件格式

- **文件**：PDF、Word (DOCX)、PowerPoint (PPTX)、Excel (XLSX/XLS)
- **網頁**：HTML、YouTube URL（字幕）
- **多媒體**：圖片（EXIF + OCR）、音頻（語音轉錄）
- **資料格式**：CSV、JSON、XML
- **其他**：ZIP、EPub、Outlook 郵件

## 🚀 快速開始

### 1. 建立目錄結構

```bash
mkdir -p input output
```

### 2. 建置 Docker 映像

```bash
docker compose build
```

### 3. 使用方式

#### 方法 A：一次性轉換（推薦）

```bash
# 將文件放入 input/ 目錄
cp your-file.pdf input/

# 執行轉換
docker compose run --rm markitdown markitdown /app/input/your-file.pdf -o /app/output/your-file.md

# 查看結果
cat output/your-file.md
```

#### 方法 B：管道輸入

```bash
cat input/file.pdf | docker compose run --rm markitdown markitdown > output/file.md
```

#### 方法 C：進入交互式容器

```bash
docker compose up -d
docker compose exec markitdown bash

# 在容器內執行
markitdown /app/input/file.pdf -o /app/output/file.md
```

## 📝 常用命令

### 轉換單一文件
```bash
docker compose run --rm markitdown markitdown /app/input/document.pdf -o /app/output/document.md
```

### 批量轉換（所有 PDF）
```bash
docker compose run --rm markitdown bash -c "for f in /app/input/*.pdf; do markitdown \"\$f\" -o \"/app/output/\${f%.pdf}.md\"; done"
```

### 使用 LLM 描述圖片（需要 OpenAI API）
```bash
docker compose run --rm -e OPENAI_API_KEY=your_key markitdown python -c "
from markitdown import MarkItDown
from openai import OpenAI
md = MarkItDown(llm_client=OpenAI(), llm_model='gpt-4o')
result = md.convert('/app/input/image.jpg')
print(result.text_content)
" > output/image.md
```

### 啟用插件（如 OCR）
```bash
docker compose run --rm markitdown markitdown --use-plugins /app/input/document.pdf -o /app/output/document.md
```

### 查看已安裝插件
```bash
docker compose run --rm markitdown markitdown --list-plugins
```

### 查看幫助
```bash
docker compose run --rm markitdown markitdown --help
```

## 🔧 自定義配置

### 添加環境變數

在 `docker-compose.yml` 中添加：

```yaml
environment:
  - OPENAI_API_KEY=your_key_here
  - AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your_endpoint
```

### 調整資源限制

編輯 `docker-compose.yml` 中的 `deploy.resources` 部分。

## 📊 依賴說明

本容器已預裝所有 MarkItDown 可選依賴：

| 依賴組 | 包含 |
|--------|------|
| `[all]` | 所有依賴 |
| 系統工具 | poppler-utils (PDF)、ffmpeg (音頻)、tesseract-ocr (OCR) |
| Python 插件 | markitdown-ocr |

## 🗑️ 清理

```bash
# 停止容器
docker compose down

# 刪除映像
docker compose down --rmi all

# 清理輸入/輸出目錄
rm -rf input/* output/*
```

## 📄 授權

MarkItDown 由 Microsoft 開源，遵循 MIT 授權。

---

**建立者：** kimhsiao  
**日期：** 2026-03-13
