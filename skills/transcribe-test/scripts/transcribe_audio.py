#!/usr/bin/env python3
"""
Transcribe audio from video using faster-whisper (local Whisper).

Usage:
    python transcribe_audio.py <video_path> --model base --output <dir>

Output:
    - transcription.json (segments with timestamps and text)
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Check for faster-whisper
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Error: faster-whisper not installed.", file=sys.stderr)
    print("Install with: pip install faster-whisper", file=sys.stderr)
    sys.exit(1)


def check_ffmpeg() -> bool:
    """Verify ffmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_audio(video_path: Path, audio_path: Path) -> bool:
    """
    Extract audio track from video using ffmpeg.
    Outputs 16kHz mono WAV for optimal Whisper performance.
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM format
        "-ar", "16000",  # 16kHz sample rate (Whisper optimal)
        "-ac", "1",  # Mono
        str(audio_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        return result.returncode == 0 and audio_path.exists()
    except subprocess.TimeoutExpired:
        print("Error: ffmpeg timed out during audio extraction", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error extracting audio: {e}", file=sys.stderr)
        return False


def transcribe_audio(
    audio_path: Path,
    model_size: str = "base",
    device: str = "auto",
    compute_type: str = "auto"
) -> dict:
    """
    Transcribe audio using faster-whisper.

    Model sizes: tiny, base, small, medium, large-v2, large-v3
    Smaller = faster but less accurate.

    Returns dict with segments and metadata.
    """
    print(f"Loading Whisper model: {model_size}")
    print("(First run will download the model, ~150MB for base)")

    # Initialize model
    # Note: compute_type="auto" will use int8 on CPU, float16 on GPU
    try:
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
    except Exception as e:
        # Try CPU fallback if GPU fails
        if device != "cpu":
            print(f"GPU init failed ({e}), falling back to CPU...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
        else:
            raise

    print("Transcribing audio...")

    # Transcribe with word-level timestamps
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        word_timestamps=True,  # Enable word-level timestamps
        vad_filter=True,  # Voice activity detection to skip silence
    )

    # Convert generator to list and format output
    result_segments = []
    for segment in segments:
        seg_data = {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        }

        # Include word-level timestamps if available
        if segment.words:
            seg_data["words"] = [
                {
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "confidence": round(w.probability, 3)
                }
                for w in segment.words
            ]

        result_segments.append(seg_data)

    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 3),
        "segments": result_segments
    }


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio from video using local Whisper"
    )
    parser.add_argument(
        "video_path",
        type=Path,
        help="Path to input video file"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output directory"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device: auto, cpu, cuda, mps (default: auto)"
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep extracted audio file in output directory"
    )

    args = parser.parse_args()

    # Validate ffmpeg
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    # Validate input
    if not args.video_path.exists():
        print(f"Error: Video not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {args.video_path}")

    # Determine audio output path
    if args.keep_audio:
        audio_path = args.output / "audio.wav"
    else:
        # Use temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_path = Path(temp_file.name)
        temp_file.close()

    # Extract audio
    print("Extracting audio track...")
    if not extract_audio(args.video_path, audio_path):
        print("Error: Failed to extract audio from video", file=sys.stderr)
        sys.exit(1)

    print(f"Audio extracted: {audio_path}")

    # Transcribe
    try:
        result = transcribe_audio(
            audio_path,
            model_size=args.model,
            device=args.device
        )
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        # Cleanup temp file
        if not args.keep_audio and audio_path.exists():
            audio_path.unlink()
        sys.exit(1)

    # Add metadata
    result["video_path"] = str(args.video_path.absolute())
    result["model"] = args.model
    result["transcription_time"] = datetime.now().isoformat()

    # Write output
    output_file = args.output / "transcription.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Cleanup temp audio if not keeping
    if not args.keep_audio and audio_path.exists():
        audio_path.unlink()

    # Summary
    segment_count = len(result["segments"])
    total_words = sum(
        len(seg.get("words", []))
        for seg in result["segments"]
    )

    print(f"\nTranscription complete!")
    print(f"  Language: {result['language']} ({result['language_probability']:.0%} confidence)")
    print(f"  Duration: {result['duration']:.1f}s")
    print(f"  Segments: {segment_count}")
    print(f"  Words: {total_words}")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
