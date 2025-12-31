# Quick Start Guide

## Install in 3 Steps

### 1. Install ffmpeg
```bash
brew install ffmpeg
```

### 2. Install Python dependencies
```bash
cd /path/to/rife-cut-smooth
pip3 install -r requirements.txt
```

### 3. Run it!

**GUI mode:**
```bash
python3 -m rife_cut_smooth
```

**CLI mode:**
```bash
python3 -m rife_cut_smooth your_video.mp4
```

## Test It

Create a simple test video with hard cuts:

```bash
# Download a sample video or use your own
# Then run:
python3 -m rife_cut_smooth test_video.mp4 --threshold 0.30

# Output will be: test_video__rife_smooth.mp4
```

## What It Does

1. **Detects** hard cuts in your video
2. **Replaces** each cut with a smooth RIFE-interpolated transition
3. **Preserves** the original video length (no duration change!)
4. **Keeps** audio in sync (or stretches it for perfect sync)

## Settings to Try

**Detect more cuts:**
```bash
python3 -m rife_cut_smooth video.mp4 --threshold 0.20
```

**Longer, smoother transitions:**
```bash
python3 -m rife_cut_smooth video.mp4 --bridge 1.0
```

**60fps output:**
```bash
python3 -m rife_cut_smooth video.mp4 --fps 60
```

**Perfect audio sync (stretch audio):**
```bash
python3 -m rife_cut_smooth video.mp4 --audio stretch-audio
```

## Troubleshooting

**"rife-ncnn-vulkan-python is not installed"**
```bash
pip3 install rife-ncnn-vulkan-python
```

**"ffmpeg not found"**
```bash
brew install ffmpeg
```

**Processing is slow?**
- This is normal! RIFE interpolation is intensive
- For a 1080p video with 10 cuts: expect 5-10 minutes
- Use `--preset fast` for faster encoding (larger file)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Try different threshold values to tune cut detection
- Experiment with bridge durations for different transition styles
- Process your own video edits!

---

**Need help?** Check the README or open an issue on GitHub.
