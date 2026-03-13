#!/bin/bash

# MarkItDown API 停止腳本
# 使用說明：./scripts/stop.sh [--remove-data]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🛑 MarkItDown API 停止服務"
echo "=========================="
echo ""

# 檢查是否要刪除數據
if [ "$1" == "--remove-data" ] || [ "$1" == "-r" ]; then
    echo "⚠️  警告：此操作將刪除所有數據和映像！"
    read -p "確定要繼續嗎？(y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  停止並刪除所有數據..."
        docker compose down --rmi all --volumes
        echo "✓ 完成"
    else
        echo "❌ 已取消"
        exit 0
    fi
else
    echo "🔧 停止服務..."
    docker compose down
    echo "✓ 服務已停止"
    echo ""
    echo "💡 提示："
    echo "   - 重新啟動：docker compose up -d"
    echo "   - 查看日誌：docker compose logs -f"
    echo "   - 完全刪除（含數據）：./scripts/stop.sh --remove-data"
fi
