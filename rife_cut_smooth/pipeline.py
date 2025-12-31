"""Main pipeline orchestrator."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Callable

from .config import Config
from .utils import print_section, check_ffmpeg, check_ffprobe
from .normalize import normalize_video, get_video_info
from .cut_detect import detect_cuts, validate_cuts
from .rife_bridge import RifeInterpolator, check_rife_available
from .frame_pipeline import extract_frames, build_output_frame_list, process_frames, assemble_video
from .audio import extract_audio, mux_audio


class Pipeline:
    """Main processing pipeline."""

    def __init__(self, config: Config, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize pipeline.

        Args:
            config: Configuration object
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.progress_callback = progress_callback
        self.temp_dir = None

    def run(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Run the full pipeline.

        Args:
            input_path: Path to input video
            output_path: Optional output path (default: auto-generate)

        Returns:
            Path to output video
        """
        # Validate dependencies
        self._check_dependencies()

        # Generate output path if not provided
        if output_path is None:
            input_stem = Path(input_path).stem
            input_dir = Path(input_path).parent
            output_path = str(input_dir / f"{input_stem}__rife_smooth.mp4")

        print_section("RIFE CUT SMOOTH - PIPELINE START")
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"\nConfiguration:")
        for key, value in self.config.to_dict().items():
            print(f"  {key}: {value}")

        # Create temp directory
        if self.config.temp_dir:
            self.temp_dir = self.config.temp_dir
            os.makedirs(self.temp_dir, exist_ok=True)
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="rife_cut_smooth_")

        print(f"\nTemp directory: {self.temp_dir}")

        try:
            # Step 1: Get input video info
            print_section("ANALYZING INPUT VIDEO")
            input_info = get_video_info(input_path)
            print(f"Input video info:")
            print(f"  Resolution: {input_info.get('width')}x{input_info.get('height')}")
            print(f"  Codec: {input_info.get('codec')}")
            print(f"  Pixel format: {input_info.get('pix_fmt')}")
            print(f"  FPS: {input_info.get('fps', 'unknown')}")
            print(f"  Duration: {input_info.get('duration', 'unknown')}s")

            # Step 2: Normalize video to CFR
            normalized_path = os.path.join(self.temp_dir, "normalized.mp4")
            success = normalize_video(
                input_path,
                normalized_path,
                self.config,
                self.progress_callback,
            )
            if not success:
                raise RuntimeError("Video normalization failed")

            # Step 3: Detect cuts
            cut_frames = detect_cuts(
                normalized_path,
                self.config,
                self.progress_callback,
            )

            # If no cuts, just output normalized video
            if len(cut_frames) == 0:
                print_section("NO CUTS DETECTED")
                print("[INFO] No hard cuts found. Outputting normalized video.")

                # Handle audio
                if self.config.audio_mode != "no-audio":
                    audio_path = os.path.join(self.temp_dir, "audio.m4a")
                    has_audio = extract_audio(input_path, audio_path, self.progress_callback)

                    if has_audio:
                        success = mux_audio(
                            normalized_path,
                            audio_path,
                            output_path,
                            "keep-original",
                            progress_callback=self.progress_callback,
                        )
                        if not success:
                            # Fallback: copy without audio
                            shutil.copy2(normalized_path, output_path)
                    else:
                        shutil.copy2(normalized_path, output_path)
                else:
                    shutil.copy2(normalized_path, output_path)

                return output_path

            # Step 4: Extract frames
            frames_dir = os.path.join(self.temp_dir, "frames")
            total_frames = extract_frames(
                normalized_path,
                frames_dir,
                self.progress_callback,
            )

            # Step 5: Validate cuts
            bridge_half = self.config.get_bridge_half_frames()
            valid_cuts = validate_cuts(cut_frames, total_frames, bridge_half)

            if len(valid_cuts) == 0:
                print_section("NO VALID CUTS")
                print("[WARNING] All detected cuts were filtered out (too close to edges/each other)")
                print("[INFO] Outputting normalized video without processing.")

                # Handle audio (same as no-cuts case)
                if self.config.audio_mode != "no-audio":
                    audio_path = os.path.join(self.temp_dir, "audio.m4a")
                    has_audio = extract_audio(input_path, audio_path, self.progress_callback)

                    if has_audio:
                        success = mux_audio(
                            normalized_path,
                            audio_path,
                            output_path,
                            "keep-original",
                            progress_callback=self.progress_callback,
                        )
                        if not success:
                            shutil.copy2(normalized_path, output_path)
                    else:
                        shutil.copy2(normalized_path, output_path)
                else:
                    shutil.copy2(normalized_path, output_path)

                return output_path

            print(f"\n[INFO] Processing {len(valid_cuts)} valid cuts")

            # Step 6: Build output frame list
            output_frame_list = build_output_frame_list(
                frames_dir,
                valid_cuts,
                bridge_half,
                total_frames,
            )

            # Step 7: Initialize RIFE
            print_section("INITIALIZING RIFE")
            rife_interpolator = RifeInterpolator(model_name=self.config.rife_model)

            # Step 8: Process frames (copy + RIFE bridges)
            output_frames_dir = os.path.join(self.temp_dir, "output_frames")
            process_frames(
                output_frame_list,
                output_frames_dir,
                rife_interpolator,
                self.progress_callback,
            )

            # Step 9: Assemble video
            video_only_path = os.path.join(self.temp_dir, "video_only.mp4")
            success = assemble_video(
                output_frames_dir,
                video_only_path,
                self.config,
                self.progress_callback,
            )
            if not success:
                raise RuntimeError("Video assembly failed")

            # Step 10: Handle audio
            if self.config.audio_mode == "no-audio":
                print_section("FINALIZING (NO AUDIO)")
                shutil.copy2(video_only_path, output_path)
            else:
                audio_path = os.path.join(self.temp_dir, "audio.m4a")
                has_audio = extract_audio(input_path, audio_path, self.progress_callback)

                if has_audio:
                    # Get durations for stretch mode
                    if self.config.audio_mode == "stretch-audio":
                        input_duration = input_info.get("duration")
                        output_info = get_video_info(video_only_path)
                        output_duration = output_info.get("duration")

                        success = mux_audio(
                            video_only_path,
                            audio_path,
                            output_path,
                            self.config.audio_mode,
                            video_duration=output_duration,
                            audio_duration=input_duration,
                            progress_callback=self.progress_callback,
                        )
                    else:
                        success = mux_audio(
                            video_only_path,
                            audio_path,
                            output_path,
                            self.config.audio_mode,
                            progress_callback=self.progress_callback,
                        )

                    if not success:
                        print("[WARNING] Audio muxing failed, saving video without audio")
                        shutil.copy2(video_only_path, output_path)
                else:
                    print("[INFO] No audio in input, saving video only")
                    shutil.copy2(video_only_path, output_path)

            # Verify output
            self._verify_output(output_path)

            print_section("PIPELINE COMPLETE")
            print(f"Output saved to: {output_path}")

            return output_path

        finally:
            # Clean up temp directory
            if self.temp_dir and not self.config.temp_dir:  # Only clean if auto-created
                print(f"\n[CLEANUP] Removing temp directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _check_dependencies(self):
        """Check required dependencies."""
        print_section("CHECKING DEPENDENCIES")

        # Check ffmpeg
        if not check_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found. Install with: brew install ffmpeg"
            )
        print("[OK] ffmpeg found")

        # Check ffprobe
        if not check_ffprobe():
            raise RuntimeError(
                "ffprobe not found. Install with: brew install ffmpeg"
            )
        print("[OK] ffprobe found")

        # Check RIFE
        if not check_rife_available():
            raise RuntimeError(
                "RIFE not available.\n"
                "Install with: pip install rife-ncnn-vulkan-python\n"
                "Or see README for alternative installation."
            )
        print("[OK] RIFE available")

    def _verify_output(self, output_path: str):
        """Verify output video."""
        print_section("VERIFYING OUTPUT")

        info = get_video_info(output_path)

        print(f"Output video info:")
        print(f"  Codec: {info.get('codec')}")
        print(f"  Pixel format: {info.get('pix_fmt')}")
        print(f"  Resolution: {info.get('width')}x{info.get('height')}")
        print(f"  FPS: {info.get('fps')}")
        print(f"  Frame rate: {info.get('avg_frame_rate')}")

        # Validate requirements
        errors = []
        if info.get("codec") != "h264":
            errors.append(f"Expected codec h264, got {info.get('codec')}")
        if info.get("pix_fmt") != "yuv420p":
            errors.append(f"Expected pix_fmt yuv420p, got {info.get('pix_fmt')}")

        expected_fps = self.config.fps
        actual_fps = info.get("fps")
        if actual_fps and abs(actual_fps - expected_fps) > 0.1:
            errors.append(f"Expected FPS {expected_fps}, got {actual_fps}")

        if errors:
            print("\n[WARNING] Output validation issues:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n[SUCCESS] Output validation passed")
