"""Video normalization to CFR."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Callable

from .config import Config
from .utils import run_command, print_section


def normalize_video(
    input_path: str,
    output_path: str,
    config: Config,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Normalize input video to CFR with deterministic encoding.

    Args:
        input_path: Path to input video
        output_path: Path to output normalized video
        config: Configuration object
        progress_callback: Optional callback for progress updates

    Returns:
        True if successful, False otherwise
    """
    print_section("NORMALIZING VIDEO TO CFR")

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Target FPS: {config.fps}")
    print(f"Pixel format: yuv420p")
    print(f"Codec: H.264 (all-intra, no B-frames, no scenecut)")

    # Build ffmpeg command with explicit flags
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", input_path,
        # Video filters
        "-vf", f"fps={config.fps}",
        # Sync mode
        "-vsync", "cfr",
        # Codec settings
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", config.preset,
        "-crf", str(config.output_crf),
        # X264 params: all-intra for frame-accurate processing
        "-x264-params",
        f"keyint={config.normalize_keyint}:min-keyint={config.normalize_keyint}:bframes={config.normalize_bframes}:scenecut=0",
        # No audio in normalized version
        "-an",
        output_path,
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        "Normalize video to CFR (VFR → CFR, all-intra encoding)",
        progress_callback=progress_callback,
    )

    if returncode != 0:
        print(f"\n[ERROR] Normalization failed with return code {returncode}")
        print(f"stderr: {stderr}")
        return False

    # Verify output exists
    if not os.path.exists(output_path):
        print(f"\n[ERROR] Output file not created: {output_path}")
        return False

    print(f"\n[SUCCESS] Normalized video created: {output_path}")
    return True


def get_video_info(video_path: str) -> dict:
    """
    Get video information using ffprobe.

    Returns dict with keys: duration, fps, width, height, codec, pix_fmt
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt,width,height,r_frame_rate,avg_frame_rate,duration",
        "-of", "default=nw=1:nk=1",
        video_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    # Debug logging
    print(f"[DEBUG] ffprobe output lines ({len(lines)} total):")
    for i, line in enumerate(lines):
        print(f"  [{i}] {repr(line)}")

    # Parse output
    info = {}
    if len(lines) >= 7:
        print(f"[DEBUG] Parsing: codec=lines[0], pix_fmt=lines[1], width=int(lines[2]), height=int(lines[3])", flush=True)
        info["codec"] = lines[0]
        info["pix_fmt"] = lines[1]
        try:
            info["width"] = int(lines[2])
        except ValueError as e:
            raise ValueError(f"Cannot convert width lines[2]={repr(lines[2])} to int. All lines: {lines}") from e
        try:
            info["height"] = int(lines[3])
        except ValueError as e:
            raise ValueError(f"Cannot convert height lines[3]={repr(lines[3])} to int. All lines: {lines}") from e
        info["r_frame_rate"] = lines[4]
        info["avg_frame_rate"] = lines[5]
        try:
            info["duration"] = float(lines[6])
        except (ValueError, IndexError):
            info["duration"] = None

    # Calculate FPS
    if info.get("avg_frame_rate"):
        try:
            num, den = info["avg_frame_rate"].split("/")
            info["fps"] = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            info["fps"] = None

    return info
