"""Command-line interface for rife-cut-smooth."""

import sys
import argparse
from pathlib import Path

from .config import Config
from .pipeline import Pipeline


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect and smooth hard cuts in videos using RIFE interpolation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with GUI
  python -m rife_cut_smooth

  # Process a specific file via CLI
  python -m rife_cut_smooth input.mp4

  # Custom settings
  python -m rife_cut_smooth input.mp4 --fps 60 --threshold 0.4 --bridge 0.75

  # Keep audio with time-stretching
  python -m rife_cut_smooth input.mp4 --audio stretch-audio

  # No audio output
  python -m rife_cut_smooth input.mp4 --audio no-audio
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Input video file (if not provided, GUI will launch)",
    )

    parser.add_argument(
        "-o", "--output",
        help="Output video path (default: <input>__rife_smooth.mp4)",
    )

    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Target frames per second (default: 30)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="Scene detection threshold, 0.0-1.0 (default: 0.30)",
    )

    parser.add_argument(
        "--bridge",
        type=float,
        default=0.5,
        help="Bridge duration in seconds (default: 0.5)",
    )

    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="Output video quality, 0-51, lower=better (default: 18)",
    )

    parser.add_argument(
        "--preset",
        default="medium",
        choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
        help="Encoding preset (default: medium)",
    )

    parser.add_argument(
        "--audio",
        default="keep-original",
        choices=["no-audio", "keep-original", "stretch-audio"],
        help="Audio handling mode (default: keep-original)",
    )

    parser.add_argument(
        "--temp-dir",
        help="Temporary directory for processing (default: auto)",
    )

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force GUI mode",
    )

    args = parser.parse_args()

    # If no input and no --gui, launch GUI
    if args.input is None and not args.gui:
        print("No input file provided. Launching GUI...")
        from .ui import launch_gui
        launch_gui()
        return

    # If --gui flag, launch GUI
    if args.gui:
        from .ui import launch_gui
        launch_gui()
        return

    # Validate input
    if not args.input:
        parser.error("Input file required for CLI mode")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Create config
    config = Config(
        fps=args.fps,
        scene_threshold=args.threshold,
        bridge_duration=args.bridge,
        output_crf=args.crf,
        preset=args.preset,
        audio_mode=args.audio,
        temp_dir=args.temp_dir,
    )

    # Run pipeline
    try:
        pipeline = Pipeline(config)
        output_path = pipeline.run(str(input_path), args.output)
        print(f"\n{'='*80}")
        print(f"SUCCESS! Output saved to:")
        print(f"  {output_path}")
        print(f"{'='*80}")

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
