# MarkItDown CLI 使用指南 💻

完整的命令行工具使用說明，支持文件轉換、URL 抓取、批量處理等功能。

---

## 🚀 快速開始

### 安裝/設置

```bash
# 1. 進入專案目錄
cd /Users/kimhsiao/git/kimhsiao/markitdown-kim

# 2. 確保 Docker 映像已建置
docker compose build

# 3. 給 CLI 腳本執行權限
chmod +x markitdown
```

---

## 📋 使用方式

### 方法 1：使用包裝腳本（推薦）

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

### 方法 2：直接使用 Docker

```bash
# 轉換單一文件
docker run --rm \
  -v "${PWD}:/workspace" \
  -w /workspace \
  markitdown-api:latest \
  python cli.py document.pdf output.md

# 從 URL 轉換
docker run --rm \
  -v "${PWD}:/workspace" \
  -w /workspace \
  markitdown-api:latest \
  python cli.py --url https://example.com output.md
```

### 方法 3：使用 Python 直接運行

```bash
# 需要安裝 MarkItDown
pip install 'markitdown[all]'

# 轉換文件
python cli.py document.pdf output.md
```

---

## 📖 命令選項

### 基本選項

| 選項 | 簡寫 | 說明 |
|------|------|------|
| `--output` | `-o` | 輸出目錄或文件路徑 |
| `--url` | `-u` | 從 URL 抓取並轉換 |
| `--stdout` | - | 輸出到標準輸出（不寫入文件） |
| `--verbose` | `-v` | 詳細輸出 |
| `--version` | - | 顯示版本 |
| `--help` | `-h` | 顯示幫助信息 |

### OCR 配置

| 選項 | 說明 | 預設值 |
|------|------|--------|
| `--ocr-lang` | OCR 語言 | `chi_tra+eng` |
| `--no-plugins` | 禁用插件（包括 OCR） | false |

---

## 💡 使用範例

### 1. 轉換單一文件

```bash
# 基本使用
./markitdown document.pdf output.md

# 詳細輸出
./markitdown document.pdf output.md --verbose

# 輸出到 stdout
./markitdown document.pdf --stdout

# 指定 OCR 語言（簡體中文 + 英文）
./markitdown scanned.pdf output.md --ocr-lang chi_sim+eng
```

### 2. 從 URL 轉換

```bash
# 基本使用
./markitdown --url https://example.com output.md

# 簡寫
./markitdown -u https://example.com output.md

# 自動生成文件名
./markitdown --url https://example.com/article
# 輸出：article.md

# 輸出到 stdout
./markitdown --url https://example.com --stdout
```

### 3. 批量轉換

```bash
# 轉換當前目錄所有 PDF
./markitdown *.pdf -o ./output/

# 轉換並指定 OCR 語言
./markitdown *.pdf -o ./output/ --ocr-lang chi_tra+eng

# 詳細輸出
./markitdown *.pdf -o ./output/ --verbose

# 禁用 OCR（純文本轉換）
./markitdown *.pdf -o ./output/ --no-plugins
```

### 4. 混合使用

```bash
# 轉換多個指定文件
./markitdown file1.pdf file2.docx file3.pptx -o ./output/

# 轉換並從 URL 抓取（需要多次執行）
./markitdown document.pdf output.md
./markitdown --url https://example.com url-output.md
```

---

## 📁 輸出路徑規則

### 情況 1：指定輸出文件

```bash
./markitdown input.pdf output.md
# 輸出：output.md
```

### 情況 2：指定輸出目錄

```bash
./markitdown input.pdf -o ./output/
# 輸出：output/input.md
```

### 情況 3：批量轉換（必須指定目錄）

```bash
./markitdown *.pdf -o ./output/
# 輸出：
#   output/file1.md
#   output/file2.md
#   output/file3.md
```

### 情況 4：未指定輸出（自動生成）

```bash
./markitdown document.pdf
# 輸出：document.md（與輸入同目錄）
```

### 情況 5：從 URL 轉換

```bash
./markitdown --url https://example.com/article
# 輸出：article.md（自動從 URL 提取）

./markitdown --url https://example.com/article output.md
# 輸出：output.md（指定文件名）
```

---

## 🔧 OCR 語言配置

### 支援的語言

| 代碼 | 語言 | 代碼 | 語言 |
|------|------|------|------|
| `chi_tra` | 繁體中文 | `tha` | 泰文 |
| `chi_sim` | 簡體中文 | `vie` | 越南文 |
| `eng` | 英文 | `jpn` | 日文 |
| `kor` | 韓文 | | |

### 組合使用

```bash
# 繁體中文 + 英文（預設）
./markitdown scanned.pdf output.md --ocr-lang chi_tra+eng

# 簡體中文 + 英文
./markitdown scanned.pdf output.md --ocr-lang chi_sim+eng

# 多語言混合
./markitdown multi-lang.pdf output.md --ocr-lang chi_tra+eng+jpn+kor

# 東南亞語言
./markitdown sea-doc.pdf output.md --ocr-lang chi_tra+tha+vie+eng

# 完整亞洲語言（7 種）
./markitdown all-asia.pdf output.md --ocr-lang chi_tra+chi_sim+eng+jpn+kor+tha+vie
```

---

## 🎯 實用場景

### 場景 1：轉換會議記錄

```bash
# 轉換所有 PDF 會議記錄
./markitdown meetings/*.pdf -o ./markdown-meetings/ --verbose

# 輸出：
# markdown-meetings/meeting-2026-03-01.md
# markdown-meetings/meeting-2026-03-08.md
# ...
```

### 場景 2：抓取網頁文章

```bash
# 抓取並轉換多篇網誌文章
./markitdown --url https://blog.example.com/post1 output1.md
./markitdown --url https://blog.example.com/post2 output2.md

# 或使用腳本批量處理
for url in urls.txt; do
    ./markitdown --url "$url" "output/$(basename $url).md"
done
```

### 場景 3：處理掃描文件（OCR）

```bash
# 繁體中文掃描文件
./markitdown scanned-tw.pdf output.md --ocr-lang chi_tra+eng

# 多語言掃描文件
./markitdown scanned-multi.pdf output.md --ocr-lang chi_tra+eng+jpn
```

### 場景 4：轉換簡報文件

```bash
# 轉換所有 PowerPoint 簡報
./markitdown presentations/*.pptx -o ./markdown-slides/

# 輸出會保留簡報結構（標題、列表等）
```

### 場景 5：轉換 Excel 表格

```bash
# 轉換 Excel 為 Markdown 表格
./markitdown data.xlsx output.md

# 批量轉換
./markitdown data/*.xlsx -o ./markdown-data/
```

---

## ⚠️ 注意事項

### 支援的文件格式

**文件：** PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, ODT  
**網頁：** HTML, URL（含 YouTube 字幕）  
**圖片：** JPG, PNG, GIF, WEBP, BMP, TIFF  
**音頻：** MP3, WAV, M4A, FLAC, OGG  
**資料：** CSV, JSON, XML  
**其他：** ZIP, EPUB

### 限制

1. **文件大小：** 建議 < 50MB（可透過環境變數調整）
2. **批量處理：** 輸出必須是目錄
3. **URL 轉換：** 需要網絡連接
4. **OCR：** 需要安裝 Tesseract 語言包

### 錯誤處理

```bash
# 文件不存在
./markitdown nonexistent.pdf output.md
# 錯誤：找不到文件 'nonexistent.pdf'

# 不支援的格式
./markitdown file.xyz output.md
# 警告：跳過不支援的文件類型 'file.xyz' (.xyz)

# 轉換失敗
./markitdown corrupted.pdf output.md
# 錯誤：轉換失敗：[錯誤信息]
```

---

## 🔗 整合腳本範例

### 範例 1：批量轉換腳本

```bash
#!/bin/bash
# batch-convert.sh

INPUT_DIR="${1:-./input}"
OUTPUT_DIR="${2:-./output}"
OCR_LANG="${3:-chi_tra+eng}"

echo "批量轉換開始"
echo "  輸入：$INPUT_DIR"
echo "  輸出：$OUTPUT_DIR"
echo "  OCR: $OCR_LANG"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.{pdf,docx,pptx,xlsx}; do
    if [[ -f "$file" ]]; then
        echo "處理：$(basename $file)"
        ./markitdown "$file" -o "$OUTPUT_DIR/" --ocr-lang "$OCR_LANG" --verbose
    fi
done

echo "批量轉換完成"
```

### 範例 2：YouTube 字幕抓取

```bash
#!/bin/bash
# youtube-transcript.sh

URL="$1"
OUTPUT="${2:-transcript.md}"

if [[ -z "$URL" ]]; then
    echo "使用方式：$0 <YouTube URL> [output.md]"
    exit 1
fi

echo "抓取 YouTube 字幕：$URL"
./markitdown --url "$URL" "$OUTPUT" --verbose

echo "字幕已保存到：$OUTPUT"
```

### 範例 3：網頁文章收集器

```bash
#!/bin/bash
# article-collector.sh

OUTPUT_DIR="./articles"
mkdir -p "$OUTPUT_DIR"

while IFS= read -r url; do
    if [[ -n "$url" && ! "$url" =~ ^# ]]; then
        echo "抓取：$url"
        ./markitdown --url "$url" "$OUTPUT_DIR/" --verbose
    fi
done < urls.txt

echo "文章收集完成"
```

---

## 📚 相關文件

- `cli.py` - CLI 工具主程序
- `markitdown` - Bash 包裝腳本
- `README.md` - 完整使用說明
- `AUTO_CONVERT.md` - 自動監控功能說明

---

**最後更新：** 2026-03-13  
**版本：** 1.1.0
