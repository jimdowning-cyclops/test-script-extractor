#!/bin/bash
# Check if all dependencies are installed for the transcribe-test skill

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "Checking transcribe-test skill dependencies..."
echo ""

# Track errors
ERRORS=0

# Check ffmpeg
echo -n "ffmpeg: "
if command -v ffmpeg &> /dev/null; then
    echo "OK ($(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3))"
else
    echo "MISSING - Install with: brew install ffmpeg"
    ERRORS=$((ERRORS + 1))
fi

# Check ffprobe
echo -n "ffprobe: "
if command -v ffprobe &> /dev/null; then
    echo "OK"
else
    echo "MISSING - Install with: brew install ffmpeg"
    ERRORS=$((ERRORS + 1))
fi

# Check Python 3.13
echo -n "Python 3.13: "
if command -v python3.13 &> /dev/null; then
    echo "OK ($(python3.13 --version 2>&1))"
else
    echo "MISSING - Install with: brew install python@3.13"
    ERRORS=$((ERRORS + 1))
fi

# Check for venv
echo -n "Virtual environment: "
if [ -d ".venv" ]; then
    echo "OK (.venv exists)"
else
    echo "MISSING - Create with: python3.13 -m venv .venv"
    ERRORS=$((ERRORS + 1))
fi

# Check faster-whisper in venv
echo -n "faster-whisper: "
if [ -d ".venv" ]; then
    if .venv/bin/python -c "import faster_whisper" 2>/dev/null; then
        echo "OK"
    else
        echo "MISSING - Install with: source .venv/bin/activate && pip install -r scripts/requirements.txt"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "SKIPPED (no venv)"
fi

echo ""

if [ $ERRORS -eq 0 ]; then
    echo "All dependencies are installed. Ready to transcribe!"
    exit 0
else
    echo "$ERRORS dependency issue(s) found. Please install missing dependencies."
    exit 1
fi
