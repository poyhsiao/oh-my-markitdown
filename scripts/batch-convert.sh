#!/bin/bash

# MarkItDown API 批量轉換腳本
# 使用說明：./scripts/batch-convert.sh [input_dir] [ocr_lang]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 預設值
INPUT_DIR="${1:-./input}"
OCR_LANG="${2:-chi_tra+eng}"
OUTPUT_DIR="./output"
API_PORT="${API_PORT:-51083}"
API_URL="http://localhost:${API_PORT}/convert"

echo "📝 MarkItDown API 批量轉換"
echo "=========================="
echo ""
echo "📂 輸入目錄：$INPUT_DIR"
echo "📤 輸出目錄：$OUTPUT_DIR"
echo "🔤 OCR 語言：$OCR_LANG"
echo "🌐 API 端點：$API_URL"
echo ""

# 檢查輸入目錄
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ 輸入目錄不存在：$INPUT_DIR"
    exit 1
fi

# 創建輸出目錄
mkdir -p "$OUTPUT_DIR"

# 檢查 API 是否運行
if ! curl -s "$API_URL/../health" > /dev/null 2>&1; then
    echo "❌ API 服務未運行，請先啟動："
    echo "   ./scripts/start.sh"
    exit 1
fi

echo "✅ API 服務正常"
echo ""

# 計數器
TOTAL=0
SUCCESS=0
FAILED=0

# 遍歷所有支援的文件
for ext in pdf docx doc pptx ppt xlsx xls jpg jpeg png gif webp; do
    for file in "$INPUT_DIR"/*.$ext "$INPUT_DIR"/*.${ext^^}; do
        if [ -f "$file" ]; then
            TOTAL=$((TOTAL + 1))
            
            filename=$(basename "$file")
            basename_no_ext="${filename%.*}"
            output_file="$OUTPUT_DIR/${basename_no_ext}.md"
            
            echo "[$TOTAL] 正在轉換：$filename"
            
            # 發送請求
            if curl -s -X POST "$API_URL" \
                -F "file=@$file" \
                -F "enable_plugins=true" \
                -F "ocr_lang=$OCR_LANG" \
                -o "$output_file" \
                -w "%{http_code}" | grep -q "200"; then
                
                echo "  ✓ 完成：$output_file"
                SUCCESS=$((SUCCESS + 1))
            else
                echo "  ❌ 失敗：$filename"
                FAILED=$((FAILED + 1))
                rm -f "$output_file"
            fi
            
            echo ""
        fi
    done
done

# 總結
echo "=========================="
echo "📊 轉換完成統計："
echo "   總計：$TOTAL"
echo "   成功：$SUCCESS"
echo "   失敗：$FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "⚠️  部分文件轉換失敗，請查看日誌"
    exit 1
else
    echo "✅ 所有文件轉換成功！"
fi
