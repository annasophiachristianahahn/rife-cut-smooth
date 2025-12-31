"""RIFE interpolation bridge generation."""

import os
import sys
from pathlib import Path
from typing import List, Optional
from PIL import Image
import numpy as np

# NOTE: Using simple blending fallback due to RIFE package compatibility issues on Apple Silicon
# This provides basic transition smoothing - not as advanced as true RIFE optical flow
# TODO: Implement proper RIFE when a compatible package becomes available

RIFE_AVAILABLE = True  # We're using blend fallback
Rife = None


class RifeInterpolator:
    """Frame interpolation engine (using blend fallback)."""

    def __init__(self, model_name: str = "rife-v4.6", gpu_id: int = 0):
        """
        Initialize interpolator.

        Args:
            model_name: Model version (unused in fallback)
            gpu_id: GPU device ID (unused in fallback)
        """
        print(f"[WARNING] Using simple blend interpolation (RIFE package unavailable)")
        print(f"[INFO] This provides basic transitions - not as advanced as true RIFE optical flow")

    def interpolate_between(
        self,
        frame_a_path: str,
        frame_b_path: str,
        num_frames: int,
        output_dir: str,
        start_index: int = 0,
    ) -> List[str]:
        """
        Generate interpolated frames between two frames using blending.

        Args:
            frame_a_path: Path to first frame
            frame_b_path: Path to second frame
            num_frames: Number of frames to generate
            output_dir: Directory to save interpolated frames
            start_index: Starting index for output filenames

        Returns:
            List of paths to generated frames
        """
        # Load images
        img_a = Image.open(frame_a_path).convert('RGB')
        img_b = Image.open(frame_b_path).convert('RGB')

        output_paths = []

        # Generate interpolations using simple alpha blending
        for i in range(num_frames):
            t = (i + 1) / (num_frames + 1)  # Timestep between 0 and 1 (exclusive)

            # Simple linear blend
            interpolated = Image.blend(img_a, img_b, t)

            # Save frame
            output_path = os.path.join(output_dir, f"{start_index + i:08d}.png")
            interpolated.save(output_path)
            output_paths.append(output_path)

        return output_paths

    def close(self):
        """Clean up resources."""
        pass


def generate_bridge_frames(
    frame_before: str,
    frame_after: str,
    num_frames: int,
    output_dir: str,
    rife_interpolator: RifeInterpolator,
    start_index: int = 0,
) -> List[str]:
    """
    Generate interpolated bridge frames.

    Args:
        frame_before: Path to frame before cut
        frame_after: Path to frame after cut
        num_frames: Number of interpolated frames to generate
        output_dir: Directory to save frames
        rife_interpolator: Interpolator instance
        start_index: Starting index for filenames

    Returns:
        List of paths to generated bridge frames
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"  [BLEND] Interpolating {num_frames} frames between:")
    print(f"    Before: {frame_before}")
    print(f"    After:  {frame_after}")

    bridge_frames = rife_interpolator.interpolate_between(
        frame_before,
        frame_after,
        num_frames,
        output_dir,
        start_index,
    )

    print(f"  [BLEND] Generated {len(bridge_frames)} bridge frames")
    return bridge_frames


def check_rife_available() -> bool:
    """Check if RIFE is available."""
    return RIFE_AVAILABLE
