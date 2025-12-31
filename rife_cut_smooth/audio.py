"""Audio extraction and muxing."""

import os
from typing import Optional, Callable

from .config import Config
from .utils import run_command, print_section


def extract_audio(
    input_path: str,
    output_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Extract audio from video.

    Args:
        input_path: Path to input video
        output_path: Path for output audio file
        progress_callback: Optional callback for progress updates

    Returns:
        True if audio extracted, False if no audio stream
    """
    print_section("EXTRACTING AUDIO")

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    # Try to copy audio stream
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vn",  # No video
        "-c:a", "copy",  # Copy audio codec
        output_path,
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        "Extract audio stream (copy codec)",
        progress_callback=progress_callback,
    )

    # Check if audio exists
    if returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
        print("[INFO] No audio stream found or extraction failed")
        return False

    print(f"[SUCCESS] Audio extracted: {output_path}")
    return True


def mux_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    audio_mode: str = "keep-original",
    video_duration: Optional[float] = None,
    audio_duration: Optional[float] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Mux audio onto video.

    Args:
        video_path: Path to video file (no audio)
        audio_path: Path to audio file
        output_path: Path for output file
        audio_mode: "keep-original" or "stretch-audio"
        video_duration: Duration of video in seconds (for stretching)
        audio_duration: Duration of audio in seconds (for stretching)
        progress_callback: Optional callback for progress updates

    Returns:
        True if successful
    """
    print_section("MUXING AUDIO")

    print(f"Video: {video_path}")
    print(f"Audio: {audio_path}")
    print(f"Output: {output_path}")
    print(f"Mode: {audio_mode}")

    if audio_mode == "keep-original":
        # Simple mux, audio may drift slightly
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",  # Copy video
            "-c:a", "aac",   # Re-encode to AAC for compatibility
            "-b:a", "192k",  # Audio bitrate
            "-shortest",     # End at shortest stream
            output_path,
        ]

        returncode, stdout, stderr = run_command(
            cmd,
            "Mux audio (keep original timing)",
            progress_callback=progress_callback,
        )

    elif audio_mode == "stretch-audio":
        if video_duration is None or audio_duration is None:
            print("[ERROR] Duration information required for audio stretching")
            return False

        # Calculate stretch factor
        stretch_factor = video_duration / audio_duration
        print(f"[INFO] Stretching audio by factor: {stretch_factor:.4f}")
        print(f"[INFO] Original audio: {audio_duration:.3f}s → New: {video_duration:.3f}s")

        # Clamp stretch factor to reasonable range
        if stretch_factor < 0.5 or stretch_factor > 2.0:
            print(f"[WARNING] Stretch factor {stretch_factor:.4f} is extreme. Using keep-original instead.")
            return mux_audio(video_path, audio_path, output_path, "keep-original", progress_callback=progress_callback)

        # Use atempo filter (supports 0.5-2.0 range)
        # For larger changes, chain multiple atempo filters
        atempo_filters = []
        remaining_stretch = stretch_factor

        while remaining_stretch > 2.0:
            atempo_filters.append("atempo=2.0")
            remaining_stretch /= 2.0

        while remaining_stretch < 0.5:
            atempo_filters.append("atempo=0.5")
            remaining_stretch /= 0.5

        if remaining_stretch != 1.0:
            atempo_filters.append(f"atempo={remaining_stretch:.4f}")

        audio_filter = ",".join(atempo_filters) if atempo_filters else "anull"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-af", audio_filter,
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ]

        returncode, stdout, stderr = run_command(
            cmd,
            f"Mux audio with time-stretch (factor={stretch_factor:.4f})",
            progress_callback=progress_callback,
        )

    else:
        print(f"[ERROR] Unknown audio mode: {audio_mode}")
        return False

    if returncode != 0:
        print(f"[ERROR] Audio muxing failed: {stderr}")
        return False

    print(f"[SUCCESS] Audio muxed: {output_path}")
    return True
