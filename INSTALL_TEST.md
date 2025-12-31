# Installation & Testing Checklist

## Prerequisites Installation

### 1. Install Homebrew (if needed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install ffmpeg
```bash
brew install ffmpeg
```

**Verify:**
```bash
ffmpeg -version
ffprobe -version
```

### 3. Install Python Dependencies
```bash
cd /Users/jaredmadere/code/rife-cut-smooth
pip3 install -r requirements.txt
```

**What gets installed:**
- `rife-ncnn-vulkan-python` - RIFE interpolation engine
- `Pillow` - Image processing
- `tqdm` - Progress bars

**Verify installation:**
```bash
python3 -c "import rife_ncnn_vulkan; print('RIFE OK')"
python3 -c "from PIL import Image; print('Pillow OK')"
python3 -c "import tqdm; print('tqdm OK')"
```

## Verify Installation

### Test 1: CLI Help
```bash
python3 -m rife_cut_smooth --help
```

**Expected:** Should show help text with all options

### Test 2: Dependency Check
```bash
python3 -c "from rife_cut_smooth.utils import check_ffmpeg, check_ffprobe; print('ffmpeg:', check_ffmpeg()); print('ffprobe:', check_ffprobe())"
```

**Expected:**
```
ffmpeg: True
ffprobe: True
```

### Test 3: RIFE Check
```bash
python3 -c "from rife_cut_smooth.rife_bridge import check_rife_available; print('RIFE available:', check_rife_available())"
```

**Expected:** `RIFE available: True`

## Testing with Video

### Option 1: Test with your own video

```bash
# GUI mode (easiest)
python3 -m rife_cut_smooth

# Then choose your video file and click Run
```

### Option 2: CLI test

```bash
# Replace with path to your video
python3 -m rife_cut_smooth /path/to/your/video.mp4 --threshold 0.30
```

**What to expect:**
1. Console output showing each step
2. All ffmpeg commands printed for inspection
3. Progress updates during processing
4. Output file created: `<input>__rife_smooth.mp4`

### Verify Output

```bash
# Check output file exists
ls -lh /path/to/video__rife_smooth.mp4

# Verify it's CFR H.264
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,pix_fmt,avg_frame_rate \
  -of default=nw=1:nk=1 \
  /path/to/video__rife_smooth.mp4
```

**Expected output:**
```
h264
yuv420p
30/1  (or your chosen FPS)
```

## Test Scenarios

### Scenario 1: Quick Test (30 fps, default settings)
```bash
python3 -m rife_cut_smooth test.mp4
```

### Scenario 2: High Quality 60fps
```bash
python3 -m rife_cut_smooth test.mp4 --fps 60 --crf 15 --preset slower
```

### Scenario 3: Sensitive Cut Detection
```bash
python3 -m rife_cut_smooth test.mp4 --threshold 0.20
```

### Scenario 4: Long Transitions
```bash
python3 -m rife_cut_smooth test.mp4 --bridge 1.0
```

### Scenario 5: Audio Time-Stretch
```bash
python3 -m rife_cut_smooth test.mp4 --audio stretch-audio
```

## Troubleshooting

### Issue: "rife-ncnn-vulkan-python is not installed"

**Solution:**
```bash
pip3 install --upgrade pip
pip3 install rife-ncnn-vulkan-python --no-cache-dir
```

If still failing:
```bash
# Check Python version (need 3.8+)
python3 --version

# Try with specific version
pip3 install "rife-ncnn-vulkan-python>=1.0.0"
```

### Issue: "ffmpeg not found"

**Solution:**
```bash
# Install via Homebrew
brew install ffmpeg

# Verify PATH
which ffmpeg
echo $PATH

# If installed but not in PATH, add to ~/.zshrc or ~/.bash_profile:
export PATH="/opt/homebrew/bin:$PATH"  # Apple Silicon
# OR
export PATH="/usr/local/bin:$PATH"     # Intel
```

### Issue: Import errors

**Solution:**
```bash
# Ensure you're in the project directory
cd /Users/jaredmadere/code/rife-cut-smooth

# Try running as module (not script)
python3 -m rife_cut_smooth --help

# Check PYTHONPATH if needed
export PYTHONPATH=/Users/jaredmadere/code/rife-cut-smooth:$PYTHONPATH
```

### Issue: GUI doesn't launch

**Solution:**
```bash
# Test tkinter
python3 -c "import tkinter; print('tkinter OK')"

# If fails, tkinter might not be installed (rare on macOS)
# macOS usually includes tkinter with Python
python3 -m tkinter  # Should open a test window
```

### Issue: Processing fails mid-way

**Check:**
1. Disk space (temp files can be large)
2. Permissions (write access to output directory)
3. Memory (close other apps for large videos)

**Debug:**
```bash
# Use temp dir to keep files for inspection
python3 -m rife_cut_smooth test.mp4 --temp-dir ./debug_temp
```

## Performance Benchmarks

**Expected processing times (approximate):**

| Video | Resolution | FPS | Cuts | Time |
|-------|------------|-----|------|------|
| 1080p | 1920x1080  | 30  | 5    | 3-5 min |
| 1080p | 1920x1080  | 30  | 20   | 10-15 min |
| 4K    | 3840x2160  | 30  | 10   | 20-30 min |
| 1080p | 1920x1080  | 60  | 10   | 15-20 min |

*Times vary based on CPU/GPU, video codec, and preset*

## Success Criteria

✅ CLI help shows correctly
✅ All dependencies pass verification
✅ Can process a test video without errors
✅ Output video exists and plays correctly
✅ Output is CFR H.264 at target FPS
✅ Hard cuts are smoothed (visual inspection)
✅ Audio is in sync (if kept)
✅ Video duration matches input (length-preserving)

## Next Steps

Once all tests pass:
1. Process your actual video files
2. Experiment with different thresholds and bridge durations
3. Compare audio modes (keep-original vs stretch-audio)
4. Try the GUI for easier workflow

## Support

If you encounter issues not covered here:
1. Check the main [README.md](README.md)
2. Review console output for error messages
3. Check temp directory (if preserved) for intermediate files
4. Open an issue on GitHub with:
   - Error message
   - Console output
   - System info (macOS version, Python version)
   - Video properties (codec, resolution, duration)
