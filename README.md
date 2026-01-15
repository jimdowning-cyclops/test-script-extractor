# Test Script Extractor

A Claude Code skill that extracts structured test scripts from narrated screen recordings of mobile app usage.

## Overview

This tool converts screen recordings with voice narration into GIVEN-WHEN-THEN test scripts using:
- **ffmpeg** for video frame extraction (scene change detection)
- **faster-whisper** for local audio transcription (no API costs)
- **Claude Code** for visual analysis and test script generation

All processing happens locally - no external API calls required after initial setup.

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/jimdowning-cyclops/test-script-extractor.git
cd test-script-extractor

# Run the setup script (installs ffmpeg, Python deps)
./.claude/skills/transcribe-test/scripts/setup.sh
```

### 2. Use with Claude Code

Open the project in Claude Code, then simply ask:

> "Transcribe the video at sample-files/RPReplay_Final1768422339.MP4 into a test script"

Claude will automatically use the `transcribe-test` skill to:
1. Extract key frames from the video
2. Transcribe the audio narration locally
3. Analyze each frame visually
4. Correlate audio with visual changes
5. Generate a structured test script

## Requirements

- macOS or Linux
- Python 3.11-3.13 (installed by setup script)
- ffmpeg (installed by setup script)
- Claude Code with Max subscription
- ~2GB disk space for Whisper models

## Project Structure

```
test-script-extractor/
├── .claude/
│   └── skills/
│       └── transcribe-test/
│           ├── SKILL.md           # Skill definition (orchestration guide)
│           └── scripts/
│               ├── extract_frames.py
│               ├── transcribe_audio.py
│               ├── requirements.txt
│               ├── setup.sh
│               └── check_setup.sh
├── sample-files/                   # Test videos
└── output/                         # Generated outputs
    └── <video_name>/
        ├── frames/                 # Extracted PNG frames
        ├── frames.json             # Frame timestamps
        ├── transcription.json      # Audio transcription
        ├── frame_descriptions.json # Visual analysis
        ├── correlated_events.json  # Audio/visual correlation
        └── test_script.md          # Final test script
```

## Manual Usage

If you prefer to run the pipeline manually:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Stage 1: Extract frames
python .claude/skills/transcribe-test/scripts/extract_frames.py \
  sample-files/recording.mp4 \
  --threshold 0.3 \
  --output output/my_test/

# Stage 2: Transcribe audio
python .claude/skills/transcribe-test/scripts/transcribe_audio.py \
  sample-files/recording.mp4 \
  --model base \
  --output output/my_test/

# Stages 3-5: Ask Claude to analyze and generate
# "Analyze the frames and transcription in output/my_test/ and generate a test script"
```

## Configuration

### Frame Extraction
| Option | Default | Description |
|--------|---------|-------------|
| `--threshold` | 0.3 | Scene change sensitivity (0.0-1.0, lower = more frames) |
| `--min-interval` | 5.0 | Minimum seconds between frames |
| `--max-frames` | 100 | Maximum frames to extract |

### Transcription
| Option | Default | Description |
|--------|---------|-------------|
| `--model` | base | Whisper model: tiny, base, small, medium, large-v3 |
| `--device` | auto | Processing device: auto, cpu, cuda, mps |

### Whisper Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| tiny | 75MB | Fastest | Low |
| base | 145MB | Fast | Good |
| small | 488MB | Medium | Better |
| medium | 1.5GB | Slow | High |
| large-v3 | 3GB | Slowest | Best |

## Output Format

The skill generates a structured test script like:

```markdown
## Test Case 1: Navigate to Settings

**Objective:** Verify user can access settings from home screen

### Step 1.1: Open Settings

**GIVEN** the user is on the home screen
**WHEN** the user taps the Settings icon (gear icon, top-right)
**THEN** the Settings menu should appear

> *Narration: "I click on the settings icon"*
> *Timestamp: 0:05 - 0:08*

**Screenshot:** `frames/frame_0002_5.000.png`
```

## Troubleshooting

### Check Dependencies

```bash
./.claude/skills/transcribe-test/scripts/check_setup.sh
```

### Common Issues

**"ffmpeg not found"**
```bash
brew install ffmpeg  # macOS
apt install ffmpeg   # Linux
```

**"faster-whisper not installed"**
```bash
source .venv/bin/activate
pip install -r .claude/skills/transcribe-test/scripts/requirements.txt
```

**Poor transcription quality**
→ Use a larger model: `--model small` or `--model medium`

**Too few/many frames**
→ Adjust threshold: `--threshold 0.2` (more) or `--threshold 0.4` (fewer)

## Offline Usage

After initial setup (which downloads the Whisper model), the tool works completely offline with no API calls or internet required.
