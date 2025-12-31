"""Frame extraction, processing, and reassembly pipeline."""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Callable
from tqdm import tqdm

from .config import Config
from .utils import run_command, print_section
from .rife_bridge import RifeInterpolator, generate_bridge_frames


def extract_frames(
    video_path: str,
    output_dir: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> int:
    """
    Extract all frames from video as PNG.

    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        progress_callback: Optional callback for progress updates

    Returns:
        Number of frames extracted
    """
    print_section("EXTRACTING FRAMES")

    os.makedirs(output_dir, exist_ok=True)

    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vsync", "0",  # Passthrough frame timing
        "-frame_pts", "1",  # Use presentation timestamp as filename
        os.path.join(output_dir, "%08d.png"),
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        "Extract all frames to PNG",
        progress_callback=progress_callback,
    )

    if returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {stderr}")

    # Count extracted frames
    frame_files = sorted(Path(output_dir).glob("*.png"))
    num_frames = len(frame_files)

    print(f"\n[SUCCESS] Extracted {num_frames} frames to {output_dir}")
    return num_frames


def build_output_frame_list(
    input_frame_dir: str,
    cut_frames: List[int],
    bridge_half: int,
    total_frames: int,
) -> List[tuple]:
    """
    Build a list of output frames with bridge replacements.

    Args:
        input_frame_dir: Directory containing input frames
        cut_frames: List of cut frame numbers
        bridge_half: Number of frames in half-bridge
        total_frames: Total number of frames

    Returns:
        List of tuples: (output_index, source_type, frame_info)
        source_type: "copy" or "bridge"
        frame_info: frame_path for "copy", (before_frame, after_frame, position) for "bridge"
    """
    print_section("BUILDING OUTPUT FRAME LIST")

    output_frames = []
    current_frame = 1  # Frames start at 1
    output_index = 0

    for cut_frame in cut_frames:
        # Copy frames before the bridge region
        bridge_start = cut_frame - bridge_half
        while current_frame < bridge_start:
            frame_path = os.path.join(input_frame_dir, f"{current_frame:08d}.png")
            output_frames.append((output_index, "copy", frame_path))
            output_index += 1
            current_frame += 1

        # Add bridge frames (replace bridge_half before + 1 cut + bridge_half after)
        before_frame_idx = cut_frame - bridge_half - 1
        after_frame_idx = cut_frame + bridge_half + 1

        before_frame_path = os.path.join(input_frame_dir, f"{before_frame_idx:08d}.png")
        after_frame_path = os.path.join(input_frame_dir, f"{after_frame_idx:08d}.png")

        total_bridge_frames = bridge_half * 2 + 1

        for i in range(total_bridge_frames):
            output_frames.append((
                output_index,
                "bridge",
                (before_frame_path, after_frame_path, i, total_bridge_frames)
            ))
            output_index += 1

        # Skip past the replaced region
        current_frame = cut_frame + bridge_half + 2

    # Copy remaining frames after last cut
    while current_frame <= total_frames:
        frame_path = os.path.join(input_frame_dir, f"{current_frame:08d}.png")
        if os.path.exists(frame_path):
            output_frames.append((output_index, "copy", frame_path))
            output_index += 1
        current_frame += 1

    print(f"[INFO] Built output frame list: {len(output_frames)} total frames")
    print(f"[INFO] Input frames: {total_frames}")
    print(f"[INFO] Output frames: {len(output_frames)} (same length - length-preserving)")

    return output_frames


def process_frames(
    output_frame_list: List[tuple],
    output_dir: str,
    rife_interpolator: RifeInterpolator,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Process frames: copy originals and generate RIFE bridges.

    Args:
        output_frame_list: List of (output_index, source_type, frame_info)
        output_dir: Directory to save output frames
        rife_interpolator: RIFE interpolator instance
        progress_callback: Optional callback for progress updates

    Returns:
        Path to output frames directory
    """
    print_section("PROCESSING FRAMES")

    os.makedirs(output_dir, exist_ok=True)

    # Group frames by type for progress tracking
    copy_frames = [(idx, info) for idx, typ, info in output_frame_list if typ == "copy"]
    bridge_groups = {}

    for idx, typ, info in output_frame_list:
        if typ == "bridge":
            before, after, pos, total = info
            key = (before, after)
            if key not in bridge_groups:
                bridge_groups[key] = []
            bridge_groups[key].append((idx, pos, total))

    print(f"[INFO] Copying {len(copy_frames)} frames")
    print(f"[INFO] Generating {len(bridge_groups)} RIFE bridges")

    # Copy frames
    print("\n[STEP 1/2] Copying original frames...")
    for output_idx, frame_path in tqdm(copy_frames, desc="Copying frames"):
        output_path = os.path.join(output_dir, f"{output_idx:08d}.png")
        shutil.copy2(frame_path, output_path)

    # Generate RIFE bridges
    print("\n[STEP 2/2] Generating RIFE interpolation bridges...")
    bridge_num = 0
    for (before_path, after_path), frame_list in tqdm(bridge_groups.items(), desc="RIFE bridges"):
        bridge_num += 1
        total_bridge_frames = frame_list[0][2]

        # Create temp directory for this bridge
        temp_bridge_dir = os.path.join(output_dir, f"_temp_bridge_{bridge_num}")
        os.makedirs(temp_bridge_dir, exist_ok=True)

        try:
            # Generate interpolated frames
            bridge_frames = generate_bridge_frames(
                before_path,
                after_path,
                total_bridge_frames,
                temp_bridge_dir,
                rife_interpolator,
                start_index=0,
            )

            # Copy bridge frames to correct output positions
            for output_idx, pos, total in frame_list:
                source_bridge_frame = bridge_frames[pos]
                output_path = os.path.join(output_dir, f"{output_idx:08d}.png")
                shutil.copy2(source_bridge_frame, output_path)

        finally:
            # Clean up temp bridge directory
            if os.path.exists(temp_bridge_dir):
                shutil.rmtree(temp_bridge_dir)

        if progress_callback:
            progress_callback(f"Generated bridge {bridge_num}/{len(bridge_groups)}")

    print(f"\n[SUCCESS] Processed all frames to {output_dir}")
    return output_dir


def assemble_video(
    frames_dir: str,
    output_path: str,
    config: Config,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Assemble frames into output video.

    Args:
        frames_dir: Directory containing output frames
        output_path: Path for output video
        config: Configuration object
        progress_callback: Optional callback for progress updates

    Returns:
        True if successful
    """
    print_section("ASSEMBLING OUTPUT VIDEO")

    print(f"Frames: {frames_dir}")
    print(f"Output: {output_path}")
    print(f"FPS: {config.fps}")
    print(f"Codec: H.264, yuv420p")

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(config.fps),
        "-i", os.path.join(frames_dir, "%08d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", config.preset,
        "-crf", str(config.output_crf),
        "-x264-params",
        f"keyint={config.output_keyint}:min-keyint={config.output_keyint}:scenecut=0:bframes={config.output_bframes}",
        "-movflags", "+faststart",
        output_path,
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        "Assemble frames to H.264 video (CFR)",
        progress_callback=progress_callback,
    )

    if returncode != 0:
        print(f"\n[ERROR] Video assembly failed: {stderr}")
        return False

    print(f"\n[SUCCESS] Video assembled: {output_path}")
    return True
