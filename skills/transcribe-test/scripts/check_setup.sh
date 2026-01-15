#!/bin/bash
# Check if all dependencies are installed for the transcribe-test skill

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SKILL_DIR/.venv"

echo "Checking transcribe-test skill dependencies..."
echo "Skill directory: $SKILL_DIR"
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

# Check Python 3.11+
echo -n "Python 3.11+: "
if command -v python3.13 &> /dev/null; then
    echo "OK ($(python3.13 --version 2>&1))"
elif command -v python3.12 &> /dev/null; then
    echo "OK ($(python3.12 --version 2>&1))"
elif command -v python3.11 &> /dev/null; then
    echo "OK ($(python3.11 --version 2>&1))"
else
    echo "MISSING - Install with: brew install python@3.13"
    ERRORS=$((ERRORS + 1))
fi

# Check for venv in skill directory
echo -n "Virtual environment: "
if [ -d "$VENV_DIR" ]; then
    echo "OK ($VENV_DIR)"
else
    echo "MISSING - Run: $SCRIPT_DIR/setup.sh"
    ERRORS=$((ERRORS + 1))
fi

# Check faster-whisper in venv
echo -n "faster-whisper: "
if [ -d "$VENV_DIR" ]; then
    if "$VENV_DIR/bin/python" -c "import faster_whisper" 2>/dev/null; then
        echo "OK"
    else
        echo "MISSING - Run: $SCRIPT_DIR/setup.sh"
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
    echo "$ERRORS dependency issue(s) found."
    echo "Run: $SCRIPT_DIR/setup.sh"
    exit 1
fi
