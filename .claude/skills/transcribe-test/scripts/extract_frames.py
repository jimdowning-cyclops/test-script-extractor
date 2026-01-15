#!/usr/bin/env python3
"""
Extract key frames from video using ffmpeg scene change detection.

Usage:
    python extract_frames.py <video_path> --threshold 0.3 --output <dir>

Output:
    - frames/frame_NNNN_SS.SSS.png  (frame files with timestamp in filename)
    - frames.json                    (mapping of frame_file -> timestamp)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


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


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting video duration: {e}", file=sys.stderr)
        return 0.0


def detect_scene_changes(video_path: Path, threshold: float) -> list[float]:
    """
    Detect scene change timestamps using ffmpeg.

    Uses the select filter with scene detection and showinfo to get timestamps.
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null",
        "-"
    ]

    try:
        # ffmpeg outputs to stderr
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Parse showinfo output for pts_time values
        # Format: [Parsed_showinfo_0 @ ...] ... pts_time:12.345678 ...
        timestamps = []
        pts_pattern = re.compile(r'pts_time:(\d+\.?\d*)')

        for line in result.stderr.split('\n'):
            if 'showinfo' in line.lower():
                match = pts_pattern.search(line)
                if match:
                    timestamps.append(float(match.group(1)))

        return sorted(set(timestamps))

    except subprocess.TimeoutExpired:
        print("Error: ffmpeg timed out during scene detection", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error detecting scene changes: {e}", file=sys.stderr)
        return []


def ensure_minimum_coverage(
    timestamps: list[float],
    duration: float,
    min_interval: float = 5.0
) -> list[float]:
    """
    Ensure frames are extracted at minimum intervals.
    Adds timestamps if gaps exceed min_interval.
    Always includes timestamp 0 (first frame).
    """
    if not timestamps:
        timestamps = []

    # Always start at 0
    result = [0.0]

    # Add detected timestamps
    for ts in timestamps:
        if ts > 0:
            result.append(ts)

    # Fill gaps
    filled = [0.0]
    for i in range(1, len(result)):
        prev = filled[-1]
        curr = result[i]

        # If gap is too large, add intermediate frames
        while curr - prev > min_interval:
            prev += min_interval
            filled.append(prev)

        filled.append(curr)

    # Ensure we cover until near the end
    if duration > 0:
        last = filled[-1]
        while duration - last > min_interval:
            last += min_interval
            filled.append(last)

    return sorted(set(filled))


def extract_frame_at_timestamp(
    video_path: Path,
    timestamp: float,
    output_path: Path
) -> bool:
    """
    Extract a single frame at the given timestamp.
    Uses -ss before -i for fast seeking.
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",  # High quality
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0 and output_path.exists()
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error extracting frame at {timestamp}s: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Extract key frames from video using scene detection"
    )
    parser.add_argument(
        "video_path",
        type=Path,
        help="Path to input video file"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.3,
        help="Scene change threshold (0.0-1.0, lower=more sensitive, default: 0.3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output directory"
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=5.0,
        help="Minimum interval between frames in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=100,
        help="Maximum number of frames to extract (default: 100)"
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

    # Create output directories
    frames_dir = args.output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {args.video_path}")

    # Get video duration
    duration = get_video_duration(args.video_path)
    print(f"Video duration: {duration:.2f}s")

    # Detect scene changes
    print(f"Detecting scene changes (threshold: {args.threshold})...")
    scene_timestamps = detect_scene_changes(args.video_path, args.threshold)
    print(f"Found {len(scene_timestamps)} scene changes")

    # Ensure minimum coverage
    timestamps = ensure_minimum_coverage(
        scene_timestamps,
        duration,
        args.min_interval
    )

    # Cap at max frames
    if len(timestamps) > args.max_frames:
        print(f"Limiting to {args.max_frames} frames")
        # Keep evenly distributed frames
        step = len(timestamps) / args.max_frames
        timestamps = [timestamps[int(i * step)] for i in range(args.max_frames)]

    print(f"Extracting {len(timestamps)} frames...")

    # Extract frames
    frames_data = []
    for i, ts in enumerate(timestamps, 1):
        # Format: frame_0001_12.345.png
        filename = f"frame_{i:04d}_{ts:.3f}.png"
        output_path = frames_dir / filename

        if extract_frame_at_timestamp(args.video_path, ts, output_path):
            frames_data.append({
                "file": filename,
                "timestamp": round(ts, 3),
                "index": i
            })
            print(f"  [{i}/{len(timestamps)}] {filename}")
        else:
            print(f"  [{i}/{len(timestamps)}] FAILED: {filename}", file=sys.stderr)

    # Build output JSON
    output_json = {
        "video_path": str(args.video_path.absolute()),
        "video_duration": round(duration, 3),
        "threshold": args.threshold,
        "min_interval": args.min_interval,
        "extraction_time": datetime.now().isoformat(),
        "frame_count": len(frames_data),
        "frames": frames_data
    }

    # Write frames.json
    output_file = args.output / "frames.json"
    with open(output_file, "w") as f:
        json.dump(output_json, f, indent=2)

    print(f"\nExtraction complete!")
    print(f"  Frames: {len(frames_data)}")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
