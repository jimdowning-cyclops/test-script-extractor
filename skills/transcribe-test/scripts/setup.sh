#!/bin/bash
# Setup script for transcribe-test skill
# Run this after installing the skill globally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Transcribe Test Skill Setup ==="
echo "Skill directory: $SKILL_DIR"
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

# Check for Python 3.11+
echo ""
echo "Checking Python..."
PYTHON_CMD=""

if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo "Python 3.13 found"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo "Python 3.12 found"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "Python 3.11 found"
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

# Create virtual environment in skill directory
echo ""
echo "Setting up virtual environment..."
VENV_DIR="$SKILL_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Created $VENV_DIR"
else
    echo "$VENV_DIR already exists"
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

# Verify installation
echo ""
echo "Verifying installation..."
"$VENV_DIR/bin/python" -c "from faster_whisper import WhisperModel; print('faster-whisper: OK')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The skill is ready to use. Ask Claude:"
echo '  "Transcribe the video at path/to/video.mp4 into a test script"'
echo ""
