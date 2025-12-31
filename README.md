# RIFE Cut Smooth

**Smooth hard cuts in videos using RIFE optical flow interpolation**

A macOS-friendly tool that detects hard cuts in videos and replaces them with smooth RIFE-interpolated transitions while preserving the original video length.

## Features

- ✨ **Automatic cut detection** using ffmpeg scene analysis
- 🎯 **Length-preserving** - output has same duration as input
- 🔄 **True optical flow** interpolation using RIFE (not crossfades)
- 🎵 **Flexible audio handling** - keep original, stretch, or remove
- 🖥️ **Simple GUI** with Finder integration
- 💻 **Powerful CLI** for automation and scripting
- 📹 **Handles VFR, H.265, long GOP** - normalizes everything to CFR
- 🍎 **macOS optimized** (Apple Silicon + Intel)

## Installation

### Prerequisites

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install ffmpeg**:
   ```bash
   brew install ffmpeg
   ```

3. **Install Python 3.8+** (usually pre-installed on macOS):
   ```bash
   python3 --version
   ```

### Install RIFE Cut Smooth

1. **Clone or download this repository**:
   ```bash
   cd ~/code
   git clone <repository-url> rife-cut-smooth
   cd rife-cut-smooth
   ```

2. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

   This will install:
   - `rife-ncnn-vulkan-python` - RIFE interpolation engine
   - `Pillow` - Image processing
   - `tqdm` - Progress bars

### Verify Installation

```bash
python3 -m rife_cut_smooth --help
```

You should see the help message with available options.

## Usage

### GUI Mode (Recommended)

Launch the GUI with no arguments:

```bash
python3 -m rife_cut_smooth
```

Or explicitly:

```bash
python3 -m rife_cut_smooth --gui
```

**Steps:**
1. Click "Choose Video..." to select your video file
2. Adjust settings (FPS, threshold, bridge duration, etc.)
3. Click "▶ Run Processing"
4. Monitor progress in the log window
5. Output will be saved as `<input>__rife_smooth.mp4`

### CLI Mode

Process a video file directly:

```bash
python3 -m rife_cut_smooth input.mp4
```

**Custom settings:**

```bash
python3 -m rife_cut_smooth input.mp4 \
  --fps 60 \
  --threshold 0.4 \
  --bridge 0.75 \
  --crf 20 \
  --audio stretch-audio
```

**All CLI options:**

```
python3 -m rife_cut_smooth [input.mp4] [options]

Options:
  -o, --output PATH        Output path (default: <input>__rife_smooth.mp4)
  --fps FLOAT             Target FPS (default: 30)
  --threshold FLOAT       Scene detection threshold, 0.0-1.0 (default: 0.30)
  --bridge FLOAT          Bridge duration in seconds (default: 0.5)
  --crf INT               Output quality, 0-51, lower=better (default: 18)
  --preset PRESET         Encoding preset (default: medium)
  --audio MODE            Audio mode: keep-original, stretch-audio, no-audio
  --temp-dir PATH         Temp directory (default: auto)
  --gui                   Launch GUI
```

## Configuration Guide

### Scene Threshold (`--threshold`)

Controls cut detection sensitivity:

- **0.20** - Very sensitive, detects subtle changes (may detect dissolves)
- **0.30** - Default, good for most videos
- **0.40** - Less sensitive, only detects hard cuts
- **0.50+** - Very conservative, may miss some cuts

**Tip:** If you get too many cuts detected, increase the threshold. If cuts are missed, decrease it.

### Bridge Duration (`--bridge`)

Duration of the smooth transition in seconds:

- **0.3s** - Quick, subtle transition
- **0.5s** - Default, smooth and natural (15 frames @ 30fps)
- **1.0s** - Longer, more pronounced transition

**Note:** Longer bridges require more space around cuts. Cuts too close to video edges or each other will be skipped.

### Audio Modes

1. **keep-original** (default, recommended)
   - Keeps original audio untouched
   - Length-preserving means almost perfect sync
   - May have tiny desync (~1ms per cut) - usually imperceptible

2. **stretch-audio**
   - Time-stretches audio to match video length exactly
   - Perfect sync guaranteed
   - May introduce slight pitch/quality artifacts if many cuts

3. **no-audio**
   - Outputs video without audio
   - Useful for reference clips or re-scoring

### Quality Settings

**CRF (Constant Rate Factor):**
- **0-17**: Visually lossless (large files)
- **18**: High quality (default, recommended)
- **23**: Good quality (smaller files)
- **28+**: Lower quality (small files)

**Preset:**
- **ultrafast**: Fastest encode, largest file
- **medium**: Default, balanced
- **slower/veryslow**: Slowest encode, smallest file

## How It Works

### Pipeline Overview

1. **Normalization**: Converts input to CFR H.264 (all-intra for frame accuracy)
2. **Cut Detection**: Uses ffmpeg scene filter to detect hard cuts
3. **Frame Extraction**: Extracts all frames as PNG
4. **Bridge Generation**: For each cut:
   - Takes frames before and after the cut
   - Generates RIFE-interpolated bridge frames
   - Replaces the cut region (length-preserving)
5. **Reassembly**: Combines frames into output video
6. **Audio Handling**: Extracts and re-muxes audio based on mode
7. **Validation**: Verifies output is CFR H.264 at target FPS

### Length-Preserving Algorithm

Instead of inserting frames, we **replace** frames around each cut:

**Example** (30fps, 0.5s bridge = 15 frames):
```
Original:
  ... frame_92 frame_93 ... frame_99 [CUT] frame_100 ... frame_107 frame_108 ...

Output:
  ... frame_92 [RIFE_1 RIFE_2 ... RIFE_15] frame_108 ...
```

The bridge replaces:
- 7 frames before cut
- 1 cut frame
- 7 frames after cut

Total: Same number of frames = Same duration ✓

## Troubleshooting

### "rife-ncnn-vulkan-python is not installed"

**Solution:**
```bash
pip3 install rife-ncnn-vulkan-python
```

If this fails on Apple Silicon, try:
```bash
pip3 install --upgrade pip
pip3 install rife-ncnn-vulkan-python --no-cache-dir
```

### "ffmpeg not found"

**Solution:**
```bash
brew install ffmpeg
```

### "No cuts detected"

**Possible causes:**
1. Video has no hard cuts (only dissolves or smooth edits)
2. Threshold is too high

**Solution:**
- Lower `--threshold` (try 0.25 or 0.20)
- Visually inspect video to confirm hard cuts exist

### "All detected cuts were filtered out"

**Cause:** Cuts are too close to video edges or each other for the bridge size.

**Solution:**
- Reduce `--bridge` duration (try 0.3 or 0.25)
- Use longer source video with more space around cuts

### Processing is slow

**Expected:** RIFE interpolation is computationally intensive.

**Tips:**
- Use faster preset: `--preset fast` or `ultrafast`
- Reduce FPS: `--fps 24` instead of 60
- Process shorter clips for testing
- Longer bridges = more interpolation = slower

**Typical speeds:**
- 1080p, 30fps, 10 cuts: ~5-10 minutes
- 4K, 60fps, 20 cuts: ~20-40 minutes

### GPU acceleration

The `rife-ncnn-vulkan` backend uses Vulkan for GPU acceleration on macOS (via MoltenVK). It should automatically detect and use your GPU.

**To verify:**
- Check console output during processing
- Look for "RIFE" initialization messages

### Memory issues

For very long videos or high resolutions:

**Solution:**
- Process in shorter segments
- Close other applications
- Ensure sufficient disk space for temp files

## Advanced Usage

### Batch Processing

Process multiple files:

```bash
for video in *.mp4; do
  python3 -m rife_cut_smooth "$video" --threshold 0.35
done
```

### Custom Temp Directory

Keep temp files for debugging:

```bash
python3 -m rife_cut_smooth input.mp4 --temp-dir ./temp_processing
```

### High Quality 4K Output

```bash
python3 -m rife_cut_smooth input.mp4 \
  --fps 60 \
  --crf 15 \
  --preset slower
```

## Technical Details

### Video I/O Specifications

**Input:**
- Codecs: H.264, H.265, ProRes, etc.
- Frame rates: VFR or CFR
- GOP structure: Any (long GOP, short GOP, all-intra)

**Normalization (intermediate):**
- Codec: H.264 (libx264)
- Frame rate: CFR at target FPS
- GOP: All-intra (`keyint=1`, `bframes=0`, `scenecut=0`)
- Pixel format: yuv420p

**Output:**
- Codec: H.264 (libx264)
- Frame rate: CFR at target FPS
- GOP: Normal (`keyint=30`, `bframes=0`, `scenecut=0`)
- Pixel format: yuv420p
- Audio: AAC (if present)

### RIFE Implementation

Uses `rife-ncnn-vulkan-python`, a Python wrapper for the optimized RIFE implementation:
- Model: RIFE v4.6 (default)
- Backend: ncnn + Vulkan
- Platform: macOS (MoltenVK)

**Sources:**
- [RIFE Paper (ECCV 2022)](https://github.com/hzwer/ECCV2022-RIFE)
- [rife-ncnn-vulkan](https://github.com/nihui/rife-ncnn-vulkan)
- [Python wrapper](https://pypi.org/project/rife-ncnn-vulkan-python/)

## Examples

### Example 1: Quick Edit Cleanup

**Scenario:** You have a 1080p video with 15 hard cuts from a rough edit.

```bash
python3 -m rife_cut_smooth rough_edit.mp4
```

**Result:** `rough_edit__rife_smooth.mp4` with smooth transitions instead of hard cuts.

### Example 2: High Frame Rate Smooth

**Scenario:** Create buttery-smooth 60fps output with long transitions.

```bash
python3 -m rife_cut_smooth input.mp4 \
  --fps 60 \
  --bridge 1.0 \
  --audio stretch-audio
```

### Example 3: Conservative Detection

**Scenario:** Only smooth the most obvious cuts.

```bash
python3 -m rife_cut_smooth input.mp4 --threshold 0.45
```

## Limitations

1. **RIFE interpolation quality:** Works best with:
   - Similar lighting before/after cut
   - Similar composition
   - Minimal motion blur

2. **Processing time:** Significant for long videos or many cuts

3. **Boundary constraints:** Cuts very close to start/end or each other may be skipped

4. **Dissolves:** Not designed for dissolve transitions (use lower threshold to detect them, but may produce artifacts)

## Contributing

Found a bug? Have a feature request? Please open an issue!

## License

MIT License - see LICENSE file

## Acknowledgments

- [RIFE](https://github.com/hzwer/ECCV2022-RIFE) - Real-Time Intermediate Flow Estimation
- [rife-ncnn-vulkan](https://github.com/nihui/rife-ncnn-vulkan) - Optimized implementation
- [FFmpeg](https://ffmpeg.org/) - Video processing backbone

---

Built with ❤️ for smooth video editing
