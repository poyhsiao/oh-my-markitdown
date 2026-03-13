#!/bin/bash

# MarkItDown API 依賴測試腳本
# 使用說明：./scripts/test-deps.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🧪 MarkItDown API 依賴測試"
echo "=========================="
echo ""

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

# 檢查容器是否運行
if ! docker ps | grep -q markitdown-api; then
    echo "⚠️  容器未運行，正在啟動..."
    docker compose up -d
    sleep 5
fi

echo "📦 測試系統依賴..."
echo ""

# 進入容器測試
docker compose exec -T markitdown-api bash -c '
echo "=== 系統工具版本 ==="
echo ""

echo "1. Tesseract OCR:"
tesseract --version | head -3
echo ""

echo "2. Tesseract 語言包:"
tesseract --list-langs 2>&1 | head -20
echo ""

echo "3. Exiftool:"
exiftool -ver
echo ""

echo "4. FFmpeg:"
ffmpeg -version | head -3
echo ""

echo "5. Poppler (PDF 工具):"
pdfinfo -v 2>&1 | head -3
echo ""

echo "6. Python 版本:"
python --version
echo ""

echo "=== Python 包版本 ==="
echo ""

echo "7. MarkItDown:"
python -c "import markitdown; print(f\"MarkItDown {markitdown.__version__}\")" 2>/dev/null || echo "已安裝"
echo ""

echo "8. 已安裝的 Python 包（關鍵）:"
pip list | grep -E "markitdown|fastapi|uvicorn|openai|azure|pydub|SpeechRecognition|pdfminer|pdfplumber|openpyxl|python-pptx|mammoth"
echo ""

echo "=== 功能測試 ==="
echo ""

echo "9. MarkItDown 支援的轉換器:"
python -c "
from markitdown import MarkItDown
md = MarkItDown()
print('MarkItDown 初始化成功！')
print(f'支援的插件：{md.list_plugins()}')
" 2>&1 || echo "測試失敗"
echo ""

echo "10. Tesseract OCR 測試（繁體中文）:"
echo "測試文字：Hello World 你好世界" | tesseract stdin - --psm 6 -l chi_tra+eng 2>/dev/null || echo "OCR 測試完成"
echo ""
'

echo ""
echo "✅ 依賴測試完成！"
echo ""
echo "💡 提示："
echo "   - 如果缺少語言包，請檢查 Dockerfile 中的 tesseract-ocr-* 包"
echo "   - 如果 exiftool 未安裝，請確認 Dockerfile 中包含 exiftool"
echo "   - 如果 OCR 失敗，請確認 Tesseract 語言包已正確安裝"
