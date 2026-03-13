#!/bin/bash

# MarkItDown API 快速啟動腳本
# 使用說明：./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 MarkItDown API 快速啟動"
echo "=========================="
echo ""

# 檢查 .env 是否存在
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在從 .env.example 複製..."
    cp .env.example .env
    echo "✓ 已創建 .env 文件"
    echo "💡 提示：編輯 .env 文件以自訂配置"
    echo ""
fi

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

# 檢查映像是否已建置
if ! docker images | grep -q markitdown-api; then
    echo "📦 首次啟動，正在建置 Docker 映像（可能需要 5-10 分鐘）..."
    docker compose build
else
    echo "✓ Docker 映像已存在"
fi

# 啟動服務
echo ""
echo "🔧 啟動服務..."
docker compose up -d

# 等待服務就緒
echo ""
echo "⏳ 等待服務就緒..."
sleep 5

# 健康檢查
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:${API_PORT:-51083}/health > /dev/null 2>&1; then
        echo ""
        echo "✅ 服務啟動成功！"
        echo ""
        echo "📡 API 端點："
        echo "   - 首頁：http://localhost:${API_PORT:-51083}"
        echo "   - 健康檢查：http://localhost:${API_PORT:-51083}/health"
        echo "   - Swagger UI: http://localhost:${API_PORT:-51083}/docs"
        echo "   - ReDoc: http://localhost:${API_PORT:-51083}/redoc"
        echo ""
        echo "🔧 CLI 工具："
        echo "   - 轉換文件：./markitdown document.pdf output.md"
        echo "   - 從 URL 轉換：./markitdown --url https://example.com output.md"
        echo "   - 批量轉換：./markitdown *.pdf -o ./output/"
        echo "   - 查看幫助：./markitdown --help"
        echo ""
        echo "📋 常用命令："
        echo "   - 查看日誌：docker compose logs -f"
        echo "   - 停止服務：docker compose down"
        echo "   - 重啟服務：docker compose restart"
        echo ""
        exit 0
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  等待中... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo ""
echo "❌ 服務啟動超時，請查看日誌："
echo "   docker compose logs -f"
exit 1
