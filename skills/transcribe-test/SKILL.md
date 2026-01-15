---
name: transcribe-test
description: Extract structured test scripts from screen recordings with voice narration. Converts MP4/MOV videos into GIVEN-WHEN-THEN test cases with screenshots and assertions.
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Transcribe Test: Video Recording to Test Script

Convert screen recordings with voice narration into structured test scripts.

## What This Skill Does

Takes a video file (MP4, MOV) containing:
- Screen recording of mobile/web app usage
- Voice narration describing the actions

And produces:
- Structured test script with GIVEN-WHEN-THEN steps
- Screenshot references at key moments
- Identification of dynamic vs static content
- Suggested assertions for automation

## Prerequisites

Before using this skill, ensure dependencies are installed:

```bash
# Check if setup is complete
${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/scripts/check_setup.sh
```

If not set up, run:
```bash
${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/scripts/setup.sh
```

## How to Use

Simply ask:
> "Transcribe the video at path/to/recording.mp4 into a test script"

Or:
> "Generate test cases from sample-files/RPReplay_Final1768422339.MP4"

## Pipeline Overview

This skill orchestrates a 5-stage pipeline:

```
Video Input
    │
    ├─► Stage 1: Frame Extraction (Python + ffmpeg)
    │       └─► frames.json + frames/*.png
    │
    ├─► Stage 2: Audio Transcription (faster-whisper, local)
    │       └─► transcription.json
    │
    ├─► Stage 3: Frame Analysis (Claude reads each frame)
    │       └─► frame_descriptions.json
    │
    ├─► Stage 4: Correlation (Claude matches audio to visuals)
    │       └─► correlated_events.json
    │
    └─► Stage 5: Test Script Generation (Claude)
            └─► test_script.md
```

---

## Execution Instructions

When asked to transcribe a video, follow these stages in order:

### Stage 1: Frame Extraction

Run the frame extraction script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/scripts/extract_frames.py "<VIDEO_PATH>" --threshold 0.3 --output "output/<VIDEO_NAME>/"
```

Replace `<VIDEO_PATH>` with the actual video path and `<VIDEO_NAME>` with a sanitized name (no spaces, lowercase). Output is created in the current working directory.

**Verify output:**
- Check that `output/<VIDEO_NAME>/frames.json` exists
- Confirm frame images are in `output/<VIDEO_NAME>/frames/`

If too few frames (< 10), re-run with `--threshold 0.2`.
If too many frames (> 50), re-run with `--threshold 0.4`.

### Stage 2: Audio Transcription

Run the transcription script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/.venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/scripts/transcribe_audio.py "<VIDEO_PATH>" --model base --output "output/<VIDEO_NAME>/"
```

**Verify output:**
- Check that `output/<VIDEO_NAME>/transcription.json` exists
- Review segment count and text quality

If transcription quality is poor, re-run with `--model small`.

### Stage 3: Frame Analysis

Read the frames.json to get the list of frames:
```
Read: output/<VIDEO_NAME>/frames.json
```

For each frame in the list, read and analyze the image:
```
Read: output/<VIDEO_NAME>/frames/<FRAME_FILE>
```

Create a description for each frame with this structure:

```json
{
  "file": "frame_0001_0.000.png",
  "timestamp": 0.0,
  "screen_type": "login | home | settings | list | form | dialog | detail | error | loading",
  "app_context": "Brief app/screen identification",
  "visible_elements": [
    "Description of UI element with location",
    "e.g., 'Blue Submit button at bottom center'",
    "e.g., 'Text field labeled Email with keyboard visible'"
  ],
  "text_content": ["Important visible text (titles, labels, error messages)"],
  "user_interaction_indicators": ["Tap highlights, focus states, selections"],
  "change_from_previous": "What changed since the previous frame"
}
```

Write all frame descriptions to:
```
Write: output/<VIDEO_NAME>/frame_descriptions.json
```

Format:
```json
{
  "video_name": "<VIDEO_NAME>",
  "analysis_time": "<ISO_TIMESTAMP>",
  "frame_count": <N>,
  "descriptions": [
    { /* frame 1 */ },
    { /* frame 2 */ }
  ]
}
```

### Stage 4: Correlation

Read both data files:
```
Read: output/<VIDEO_NAME>/transcription.json
Read: output/<VIDEO_NAME>/frame_descriptions.json
```

For each transcription segment, find matching frames using a **±2 second window**:
- A frame at timestamp 5.0s matches audio segments from 3.0s to 7.0s

Identify action types from narration:
- "tap/click/press" → Button interaction
- "type/enter/input" → Text entry
- "scroll/swipe" → Navigation gesture
- "select/choose" → Selection from list
- "wait/see/verify" → Expected outcome

Create correlated events:

```json
{
  "video_name": "<VIDEO_NAME>",
  "correlation_time": "<ISO_TIMESTAMP>",
  "events": [
    {
      "event_id": 1,
      "time_range": {"start": 0.0, "end": 2.5},
      "narration": "Now I tap on the settings icon",
      "action": {
        "type": "tap",
        "target": "Settings icon",
        "location": "top-right"
      },
      "frames": [
        {"file": "frame_0001_0.000.png", "role": "before"},
        {"file": "frame_0002_2.100.png", "role": "after"}
      ],
      "state_transition": {
        "before": "Home screen",
        "after": "Settings menu visible"
      }
    }
  ]
}
```

Write to:
```
Write: output/<VIDEO_NAME>/correlated_events.json
```

### Stage 5: Test Script Generation

Read the correlated events:
```
Read: output/<VIDEO_NAME>/correlated_events.json
```

**CRITICAL: Distinguishing User Inputs from Calculated/Dynamic Values**

When writing GIVEN-WHEN-THEN steps, carefully distinguish between:

1. **User Inputs (CAN be conditions):** Values the user explicitly enters or selects
   - Example: "enters '250' in Ruling Span field" ✓
   - Example: "selects 'Pelican' conductor" ✓

2. **Calculated/Algorithm Outputs (must NOT be conditions):** Values computed by the system
   - Example: "displays calculated tension of 1116lb" ✗ (too specific)
   - Example: "displays a calculated target tension (e.g., 1116lb)" ✓ (as example only)
   - Example: "a non-zero tension value is displayed" ✓ (valid assertion)

3. **Dynamic/Sensor Values (must NOT be conditions):** Values from external sources
   - Example: "ambient temperature shows 41°F" ✗ (too specific)
   - Example: "ambient temperature is auto-populated" ✓ (valid assertion)

**In THEN clauses:**
- For calculated values: Describe WHAT should happen, not the specific value
- Include specific values as examples in parentheses: "(e.g., 1116lb)"
- Never assert exact calculated values as pass/fail conditions
- Focus on behavioral assertions: "value is displayed", "value changes", "value is within valid range"

Generate the final test script in markdown format:

```markdown
# Test Script: <Video Name>

**Source:** <video_path>
**Generated:** <timestamp>
**Duration:** <duration>s

---

## Overview

<Brief description of what the recording demonstrates>

## Preconditions

- <Required starting state>
- <User authentication status>
- <Any test data needed>

---

## Test Case 1: <Descriptive Title>

**Objective:** <What this test verifies>

### Step 1.1: <Action Name>

**GIVEN** <current state/precondition>
**WHEN** <user action with specific element>
**THEN** <expected outcome - use specific values only for user inputs; for calculated/dynamic values use "e.g." or describe behavior>

> *Narration: "<original text>"*
> *Timestamp: MM:SS - MM:SS*

**Screenshot:** `frames/frame_NNNN_SS.SSS.png`

---

## Dynamic Data Elements

**IMPORTANT:** Elements listed here must NEVER have their specific values used as test conditions.
The "Example" column shows values observed in the recording for reference only.

| Element | Location | Type | Example (for reference only) |
|---------|----------|------|------------------------------|
| Username | Header | User data | "John Doe" |
| Calculated values | Various | Algorithm output | (list all computed values) |
| Sensor readings | Various | Device/environment | (list temperature, location, etc.) |

## Suggested Assertions

Focus on behavioral and structural assertions, NOT specific calculated values:
- [ ] <UI state/navigation assertion>
- [ ] <Input validation assertion>
- [ ] <Data presence assertion - e.g., "tension value is displayed" not "tension is 1116lb">
- [ ] <Behavioral assertion - e.g., "value changes when toggle is switched">

## Notes

- <Edge cases noticed>
- <Automation challenges>
```

Write to:
```
Write: output/<VIDEO_NAME>/test_script.md
```

---

## Output Summary

After completion, provide a summary:

```
Test script generated successfully!

Output directory: output/<VIDEO_NAME>/
├── frames/                  (<N> frames extracted)
├── frames.json             (frame manifest)
├── transcription.json      (<N> segments, <N> words)
├── frame_descriptions.json (visual analysis)
├── correlated_events.json  (<N> events)
└── test_script.md          (final test script)

Test cases generated: <N>
Total steps: <N>
```

---

## Troubleshooting

**"ffmpeg not found"**
→ Install with `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)

**"faster-whisper not installed" or skill not working**
→ Run `${CLAUDE_PLUGIN_ROOT}/skills/transcribe-test/scripts/setup.sh` to install dependencies

**Poor transcription quality**
→ Re-run Stage 2 with `--model small` for better accuracy

**Too few/many frames**
→ Adjust `--threshold` in Stage 1 (lower = more frames)

**Video has no audio**
→ Skip Stage 2, generate visual-only test script from frame analysis
