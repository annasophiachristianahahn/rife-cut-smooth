"""Configuration and constants for rife-cut-smooth."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration for video processing."""

    # Video settings
    fps: float = 30.0
    scene_threshold: float = 0.30
    bridge_duration: float = 0.5  # seconds

    # Encoding settings
    output_crf: int = 18
    preset: str = "medium"

    # Audio settings
    audio_mode: str = "keep-original"  # "no-audio", "stretch-audio", "keep-original"

    # RIFE settings
    rife_model: str = "rife-v4.6"  # Model version

    # Advanced encoding flags
    normalize_keyint: int = 1  # All-intra for normalization
    normalize_bframes: int = 0
    output_keyint: int = 30  # Normal GOP for output
    output_bframes: int = 0

    # Processing settings
    max_cuts_warning: int = 200
    temp_dir: Optional[str] = None  # None = auto temp directory

    def get_bridge_frames(self) -> int:
        """Calculate number of frames in bridge."""
        return round(self.fps * self.bridge_duration)

    def get_bridge_half_frames(self) -> int:
        """Calculate half-bridge frames (frames to replace on each side of cut)."""
        total = self.get_bridge_frames()
        return total // 2

    def to_dict(self) -> dict:
        """Convert config to dictionary for display."""
        return {
            "fps": self.fps,
            "scene_threshold": self.scene_threshold,
            "bridge_duration": self.bridge_duration,
            "bridge_frames": self.get_bridge_frames(),
            "output_crf": self.output_crf,
            "preset": self.preset,
            "audio_mode": self.audio_mode,
            "rife_model": self.rife_model,
        }
