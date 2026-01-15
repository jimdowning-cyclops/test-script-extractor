#!/bin/bash
# Setup script for transcribe-test skill
# Run this once after cloning the repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Transcribe Test Skill Setup ==="
echo ""

# Check for Homebrew (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install from https://brew.sh"
        exit 1
    fi
fi

# Install ffmpeg if needed
echo "Checking ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing ffmpeg..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    else
        echo "Please install ffmpeg manually for your OS"
        exit 1
    fi
else
    echo "ffmpeg already installed"
fi

# Check for Python 3.13
echo ""
echo "Checking Python 3.13..."
PYTHON_CMD=""

if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo "Python 3.13 found"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo "Python 3.12 found (3.13 preferred but 3.12 works)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "Python 3.11 found (3.13 preferred but 3.11 works)"
else
    echo "Python 3.11+ not found. Installing Python 3.13..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install python@3.13
        PYTHON_CMD="python3.13"
    else
        echo "Please install Python 3.11+ manually"
        exit 1
    fi
fi

# Create virtual environment
echo ""
echo "Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo "Created .venv"
else
    echo ".venv already exists"
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Verify installation
echo ""
echo "Verifying installation..."
python -c "from faster_whisper import WhisperModel; print('faster-whisper: OK')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use the skill, ask Claude:"
echo '  "Transcribe the video at path/to/video.mp4 into a test script"'
echo ""
echo "Or run manually:"
echo "  source .venv/bin/activate"
echo "  python scripts/extract_frames.py video.mp4 --output output/test/"
echo "  python scripts/transcribe_audio.py video.mp4 --output output/test/"
