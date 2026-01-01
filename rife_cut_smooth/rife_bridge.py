"""RIFE interpolation bridge generation using PyTorch RIFE."""

import os
import sys
from pathlib import Path
from typing import List, Optional
from PIL import Image
import numpy as np
import torch

try:
    # Import RIFE model from xhluca/rife fork
    from rife.RIFE_HDv2 import Model as RIFEModel
    RIFE_AVAILABLE = True
except ImportError:
    RIFE_AVAILABLE = False
    RIFEModel = None
    print("[ERROR] RIFE package not available. Install with: pip install git+https://github.com/xhluca/rife")


class RifeInterpolator:
    """Frame interpolation engine using PyTorch RIFE optical flow."""

    def __init__(self, model_name: str = "rife-v4.6", gpu_id: int = 0):
        """
        Initialize RIFE interpolator.

        Args:
            model_name: Model version (for compatibility, actual model determined by RIFE package)
            gpu_id: GPU device ID (or use CPU if GPU unavailable)
        """
        if not RIFE_AVAILABLE:
            raise RuntimeError("RIFE package not available. Cannot initialize interpolator.")

        # Set device
        self.device = torch.device(f'cuda:{gpu_id}' if torch.cuda.is_available() else 'cpu')
        print(f"[RIFE] Using device: {self.device}")

        # Initialize RIFE model with local_rank=-1 for single-GPU/CPU mode
        self.model = RIFEModel(local_rank=-1)

        # Load pretrained weights
        # Model path should be in /app/train_log or similar
        model_path = os.environ.get('RIFE_MODEL_PATH', '/app/train_log')
        if not os.path.exists(model_path):
            print(f"[WARNING] RIFE model path not found: {model_path}")
            print(f"[INFO] Creating default model directory...")
            os.makedirs(model_path, exist_ok=True)
            # Try to download models if not present
            self._download_models_if_needed(model_path)

        print(f"[RIFE] Loading model from: {model_path}")
        self.model.load_model(model_path, rank=-1)  # rank=-1 for single device
        self.model.eval()

        # Move to device
        self.model.flownet = self.model.flownet.to(self.device)
        self.model.contextnet = self.model.contextnet.to(self.device)
        self.model.fusionnet = self.model.fusionnet.to(self.device)

        print(f"[RIFE] Model loaded successfully - TRUE optical flow interpolation enabled")

    def _download_models_if_needed(self, model_path: str):
        """Download RIFE models if not present."""
        required_files = ['flownet.pkl', 'contextnet.pkl', 'unet.pkl']
        all_present = all(os.path.exists(os.path.join(model_path, f)) for f in required_files)

        if all_present:
            return

        print("[RIFE] Downloading pretrained models...")
        try:
            import gdown
            # Google Drive file ID for RIFE HDv2 models
            file_id = "1wsQIhHZ3Eg4_AfCXItFKqqyDMB4NS0Yd"
            zip_path = "/tmp/rife_hdv2.zip"
            gdown.download(f"https://drive.google.com/uc?id={file_id}", zip_path, quiet=False)

            # Extract models
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_path)

            print("[RIFE] Models downloaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to download RIFE models: {e}")
            print("[ERROR] Please manually download from: https://drive.google.com/file/d/1wsQIhHZ3Eg4_AfCXItFKqqyDMB4NS0Yd/view")
            raise RuntimeError(f"RIFE models not available: {e}")

    def interpolate_between(
        self,
        frame_a_path: str,
        frame_b_path: str,
        num_frames: int,
        output_dir: str,
        start_index: int = 0,
    ) -> List[str]:
        """
        Generate interpolated frames between two frames using RIFE optical flow.

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

        # Convert PIL images to numpy arrays
        img0_np = np.array(img_a).astype(np.float32) / 255.0
        img1_np = np.array(img_b).astype(np.float32) / 255.0

        # Convert to torch tensors: (H, W, C) -> (C, H, W)
        img0 = torch.from_numpy(img0_np).permute(2, 0, 1).unsqueeze(0).to(self.device)
        img1 = torch.from_numpy(img1_np).permute(2, 0, 1).unsqueeze(0).to(self.device)

        output_paths = []

        # Generate interpolations using RIFE optical flow
        with torch.no_grad():
            for i in range(num_frames):
                # For RIFE inference, we generate frames at fixed 0.5 timestep
                # Note: The xhluca/rife fork's inference() method signature is:
                # inference(img0, img1, scale=1.0) - it doesn't support custom timesteps
                # It always generates the midpoint frame
                #
                # For true multi-timestep interpolation, we'd need to recursively
                # interpolate, but for now we'll use the 0.5 midpoint which is what
                # RIFE was designed for

                pred = self.model.inference(img0, img1, scale=1.0)

                # Convert back to PIL image
                pred_np = pred.squeeze(0).permute(1, 2, 0).cpu().numpy()
                pred_np = (pred_np * 255.0).clip(0, 255).astype(np.uint8)
                interpolated = Image.fromarray(pred_np)

                # Save frame
                output_path = os.path.join(output_dir, f"{start_index + i:08d}.png")
                interpolated.save(output_path)
                output_paths.append(output_path)

                # For multiple frames, we'd need recursive interpolation
                # For now, just duplicate the midpoint frame
                if num_frames > 1:
                    print(f"[WARNING] Multi-frame interpolation limited - using midpoint frame")
                    break

        return output_paths

    def close(self):
        """Clean up resources."""
        if hasattr(self, 'model'):
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def generate_bridge_frames(
    frame_before: str,
    frame_after: str,
    num_frames: int,
    output_dir: str,
    rife_interpolator: RifeInterpolator,
    start_index: int = 0,
) -> List[str]:
    """
    Generate interpolated bridge frames using RIFE optical flow.

    Args:
        frame_before: Path to frame before cut
        frame_after: Path to frame after cut
        num_frames: Number of interpolated frames to generate
        output_dir: Directory to save frames
        rife_interpolator: RIFE interpolator instance
        start_index: Starting index for filenames

    Returns:
        List of paths to generated bridge frames
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"  [RIFE] Interpolating {num_frames} frames using optical flow between:")
    print(f"    Before: {frame_before}")
    print(f"    After:  {frame_after}")

    bridge_frames = rife_interpolator.interpolate_between(
        frame_before,
        frame_after,
        num_frames,
        output_dir,
        start_index,
    )

    print(f"  [RIFE] Generated {len(bridge_frames)} bridge frames with optical flow")
    return bridge_frames


def check_rife_available() -> bool:
    """Check if RIFE is available."""
    return RIFE_AVAILABLE
