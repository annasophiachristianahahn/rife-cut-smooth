"""Cut detection using ffmpeg scene filter."""

import re
from typing import List, Optional, Callable

from .config import Config
from .utils import run_command, print_section


def detect_cuts(
    video_path: str,
    config: Config,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[int]:
    """
    Detect hard cuts in video using ffmpeg scene detection.

    Args:
        video_path: Path to normalized video
        config: Configuration object
        progress_callback: Optional callback for progress updates

    Returns:
        List of frame numbers where cuts occur
    """
    print_section("DETECTING HARD CUTS")

    print(f"Video: {video_path}")
    print(f"Scene threshold: {config.scene_threshold}")
    print(f"Target FPS: {config.fps}")

    # Use ffmpeg's scene detection filter
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"select='gt(scene,{config.scene_threshold})',showinfo",
        "-f", "null",
        "-",
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        f"Detect scene changes (threshold={config.scene_threshold})",
        progress_callback=progress_callback,
    )

    if returncode != 0 and returncode != 1:  # ffmpeg returns 1 sometimes even on success
        print(f"\n[WARNING] Cut detection returned code {returncode}")

    # Parse showinfo output from stderr
    # Looking for lines like: "n:123 pts:4123 ... pos:12345"
    cut_frames = []
    pattern = re.compile(r'n:\s*(\d+)\s+')

    for line in stderr.split('\n'):
        if 'Parsed_showinfo' in line:
            match = pattern.search(line)
            if match:
                frame_num = int(match.group(1))
                cut_frames.append(frame_num)

    # Sort and deduplicate
    cut_frames = sorted(set(cut_frames))

    print(f"\n[RESULT] Detected {len(cut_frames)} hard cuts")

    if len(cut_frames) > config.max_cuts_warning:
        print(f"[WARNING] Found {len(cut_frames)} cuts, which exceeds {config.max_cuts_warning}.")
        print(f"[WARNING] This may indicate the threshold is too low or the video has many quick edits.")

    if cut_frames:
        print(f"[INFO] Cut frames: {cut_frames[:10]}{'...' if len(cut_frames) > 10 else ''}")

    return cut_frames


def validate_cuts(cut_frames: List[int], total_frames: int, bridge_half: int) -> List[int]:
    """
    Validate and filter cut frames to ensure they're processable.

    Args:
        cut_frames: List of detected cut frame numbers
        total_frames: Total number of frames in video
        bridge_half: Number of frames in half-bridge

    Returns:
        Filtered list of valid cut frames
    """
    valid_cuts = []

    for cut_frame in cut_frames:
        # Ensure we have enough frames before and after the cut
        if cut_frame < bridge_half:
            print(f"[WARNING] Cut at frame {cut_frame} is too close to start (need {bridge_half} frames before). Skipping.")
            continue

        if cut_frame + bridge_half >= total_frames:
            print(f"[WARNING] Cut at frame {cut_frame} is too close to end (need {bridge_half} frames after). Skipping.")
            continue

        valid_cuts.append(cut_frame)

    # Check for cuts that are too close together
    filtered_cuts = []
    min_distance = bridge_half * 2 + 1  # Need at least one bridge width between cuts

    for i, cut in enumerate(valid_cuts):
        if i == 0:
            filtered_cuts.append(cut)
        else:
            if cut - filtered_cuts[-1] >= min_distance:
                filtered_cuts.append(cut)
            else:
                print(f"[WARNING] Cut at frame {cut} is too close to previous cut at {filtered_cuts[-1]}. Skipping.")

    if len(filtered_cuts) < len(cut_frames):
        print(f"[INFO] Filtered {len(cut_frames) - len(filtered_cuts)} cuts due to boundary/spacing constraints.")

    return filtered_cuts
