"""Utility functions for rife-cut-smooth."""

import subprocess
import shlex
import sys
from typing import List, Tuple, Optional, Callable


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_ffprobe() -> bool:
    """Check if ffprobe is available."""
    try:
        subprocess.run(
            ["ffprobe", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_command(
    cmd: List[str],
    description: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    verbose: bool = True,
) -> Tuple[int, str, str]:
    """
    Run a command and capture output.

    Args:
        cmd: Command as list of strings
        description: Description for logging
        progress_callback: Optional callback for progress updates
        verbose: Whether to print command before running

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    if verbose:
        # Print command with proper shell escaping for inspection
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        print(f"\n{'='*80}")
        print(f"[COMMAND] {description}")
        print(f"{'='*80}")
        print(cmd_str)
        print(f"{'='*80}\n")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )

    stdout_lines = []
    stderr_lines = []

    # Read stderr for progress (ffmpeg outputs to stderr)
    while True:
        line = process.stderr.readline()
        if not line and process.poll() is not None:
            break
        if line:
            stderr_lines.append(line)
            if progress_callback:
                progress_callback(line.strip())

    # Get any remaining output
    stdout_remainder, stderr_remainder = process.communicate()
    if stdout_remainder:
        stdout_lines.append(stdout_remainder)
    if stderr_remainder:
        stderr_lines.append(stderr_remainder)

    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)

    return process.returncode, stdout, stderr


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def parse_ffmpeg_duration(line: str) -> Optional[float]:
    """Parse duration from ffmpeg output line."""
    if "Duration:" in line:
        try:
            # Duration: 00:00:10.50, start: 0.000000, bitrate: 1000 kb/s
            duration_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = duration_str.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
        except (ValueError, IndexError):
            pass
    return None


def parse_ffmpeg_time(line: str) -> Optional[float]:
    """Parse current time from ffmpeg progress line."""
    if "time=" in line:
        try:
            # time=00:00:05.50
            time_str = line.split("time=")[1].split()[0].strip()
            h, m, s = time_str.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
        except (ValueError, IndexError):
            pass
    return None


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'#'*80}")
    print(f"# {title}")
    print(f"{'#'*80}\n")
