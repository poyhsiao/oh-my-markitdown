#!/bin/bash
# Oh-My-MarkItDown: Apple Silicon Setup Script
# Phase 4: Whisper Performance Optimization
# This script sets up whisper-cpp for local GPU-accelerated transcription on Apple Silicon (M1/M2/M3/M4)

set -e

echo "=== Oh-My-MarkItDown: Apple Silicon Setup ==="

# Check if running on Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "ERROR: This script is for Apple Silicon (M1/M2/M3/M4) only."
    echo "Current architecture: $(uname -m)"
    exit 1
fi

echo "Detected Apple Silicon ($(uname -m))"

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew already installed"
fi

# Update Homebrew
echo "Updating Homebrew..."
brew update

# Install whisper-cpp (Apple Silicon optimized)
echo "Installing whisper-cpp..."
brew install whisper-cpp

# Install Python bindings
echo "Installing Python dependencies..."
pip install whispercpp>=2.0.0

# Verify installation
echo "Verifying installation..."
python -c "import whispercpp; print('whispercpp installed successfully')"

echo "=== Setup Complete ==="
echo ""
echo "To use Apple Silicon acceleration:"
echo "1. Set WHISPER_DEVICE=apple_silicon in your .env file"
echo "2. Or use: curl -X POST 'http://localhost:51083/api/v1/convert/audio?device=apple_silicon' -F 'file=@audio.mp3'"
echo ""
echo "For more information, see: docs/APPLE_SILICON.md"