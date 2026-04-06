#!/bin/bash

# MarkItDown Smart Launcher
# Auto-detects platform and launches with optimal device support:
#   - Linux + NVIDIA GPU → Docker with CUDA
#   - macOS Apple Silicon → Native (uv run) for MPS support
#   - Linux (no GPU) → Docker with CPU
#   - macOS Intel → Docker with CPU

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

API_PORT="${API_PORT:-51083}"

# ============================================================
# Detect platform
# ============================================================
detect_platform() {
    local os="$(uname -s)"
    local arch="$(uname -m)"

    if [ "$os" = "Darwin" ] && [ "$arch" = "arm64" ]; then
        echo "apple-silicon"
    elif [ "$os" = "Darwin" ] && [ "$arch" = "x86_64" ]; then
        echo "mac-intel"
    elif [ "$os" = "Linux" ]; then
        # Check for NVIDIA GPU
        if command -v nvidia-smi > /dev/null 2>&1 && nvidia-smi > /dev/null 2>&1; then
            echo "linux-gpu"
        else
            echo "linux-cpu"
        fi
    else
        echo "unknown"
    fi
}

# ============================================================
# Launch modes
# ============================================================
launch_docker_cpu() {
    echo "🐳 Launching with Docker (CPU mode)..."
    docker compose down --remove-orphans > /dev/null 2>&1 || true
    docker compose build markitdown-api markitdown-auto
    docker compose up -d markitdown-api markitdown-auto
}

launch_docker_gpu() {
    echo "🚀 Launching with Docker (GPU/CUDA mode)..."
    docker compose down --remove-orphans > /dev/null 2>&1 || true
    docker compose build markitdown-api-gpu
    docker compose --profile gpu up -d markitdown-api-gpu
}

launch_native_mps() {
    echo "🍎 Launching natively on Apple Silicon (MPS mode)..."
    echo "   (Docker on macOS cannot access Metal/MPS — running natively)"
    echo ""

    # Check for uv
    if ! command -v uv > /dev/null 2>&1; then
        echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Install dependencies with apple-silicon extras
    echo "📦 Installing dependencies (torch + MPS support)..."
    uv sync --extra apple-silicon

    # Install torch for macOS MPS
    echo "🔧 Installing torch for Apple Silicon..."
    uv pip install torch --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || \
    uv pip install torch 2>/dev/null || true

    # Start API
    echo ""
    echo "🔧 Starting API server..."
    echo "   PID: $$"
    uv run uvicorn api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload
}

# ============================================================
# Wait for service
# ============================================================
wait_for_service() {
    local port="$1"
    local max_retries=15
    local count=0

    echo ""
    echo "⏳ Waiting for service..."
    while [ $count -lt $max_retries ]; do
        if curl -s "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo ""
            echo "✅ Service ready!"
            echo ""
            echo "📡 API Endpoints:"
            echo "   - Health:    http://localhost:${port}/health"
            echo "   - Swagger:   http://localhost:${port}/docs"
            echo "   - Device:    http://localhost:${port}/api/v1/device-info"
            echo ""
            echo "📋 Commands:"
            echo "   - Logs:      docker compose logs -f"
            echo "   - Stop:      docker compose down"
            echo "   - Restart:   docker compose restart"
            echo ""
            return 0
        fi
        count=$((count + 1))
        sleep 2
    done

    echo "❌ Service startup timed out"
    echo "   Check logs: docker compose logs -f"
    return 1
}

# ============================================================
# Main
# ============================================================
platform="$(detect_platform)"
echo "🔍 Detected platform: $platform"
echo ""

case "$platform" in
    apple-silicon)
        # Check if user wants Docker anyway
        if [ "$1" = "--docker" ] || [ "$MARKITDOWN_FORCE_DOCKER" = "true" ]; then
            echo "⚠️  Forced Docker mode (MPS not available in Docker)"
            echo "   For best performance, run without --docker flag"
            echo ""
            launch_docker_cpu
            wait_for_service "$API_PORT"
        else
            launch_native_mps
        fi
        ;;
    linux-gpu)
        launch_docker_gpu
        wait_for_service "$API_PORT"
        ;;
    linux-cpu|mac-intel|unknown)
        launch_docker_cpu
        wait_for_service "$API_PORT"
        ;;
esac
