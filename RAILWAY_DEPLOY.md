# Railway Deployment Guide

## Quick Deploy to Railway

### Option 1: Deploy via GitHub (Recommended)

1. **Push code to GitHub:**
   ```bash
   cd /Users/jaredmadere/code/rife-cut-smooth
   git init
   git add .
   git commit -m "Initial commit - RIFE Cut Smooth"
   # Create a new repo on GitHub, then:
   git remote add origin https://github.com/YOUR_USERNAME/rife-cut-smooth.git
   git push -u origin main
   ```

2. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `rife-cut-smooth` repository
   - Railway will automatically detect the Dockerfile and deploy

3. **Wait for deployment** (~5-10 minutes for first build)

4. **Access your app:**
   - Railway will provide a URL like: `https://rife-cut-smooth-production.up.railway.app`
   - Click it to open the web interface

### Option 2: Deploy via Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login:**
   ```bash
   railway login
   ```

3. **Initialize and deploy:**
   ```bash
   cd /Users/jaredmadere/code/rife-cut-smooth
   railway init
   railway up
   ```

4. **Open deployed app:**
   ```bash
   railway open
   ```

## What Gets Deployed

- **Web Interface:** Upload videos, configure settings, download processed results
- **RIFE Engine:** Full RIFE v4.6 optical flow interpolation
- **FFmpeg:** Video processing pipeline
- **Automatic Scaling:** Railway handles resources automatically

## Usage After Deployment

1. **Open the Railway URL** in your browser
2. **Upload your video** (supports MP4, MOV, AVI, MKV, etc.)
3. **Configure settings:**
   - Target FPS (default: 30)
   - Scene threshold (default: 0.30)
   - Bridge duration (default: 0.5s)
   - Audio mode (keep-original recommended)
4. **Click "Process Video"**
5. **Wait for processing** (progress shown in real-time)
6. **Download the result** when complete

## Configuration

Railway environment variables (optional):

- `PORT` - Auto-set by Railway (default: 8000)
- `MAX_CONTENT_LENGTH` - Max upload size in bytes (default: 2GB)

## Costs

Railway Pricing (as of 2025):

- **Free Tier:** $5 credit/month (good for testing)
- **Pro Plan:** $20/month with $20 included credits
- **Usage-based:** ~$0.000231/GB-hour + compute time

**Estimated costs:**
- Processing a 5-minute 1080p video: ~$0.10-0.50
- 10 videos/month: ~$1-5

## Troubleshooting

### Build fails

**Check logs:**
```bash
railway logs
```

**Common issues:**
- Dockerfile syntax error → Check Dockerfile
- Dependency installation failed → Check requirements.txt
- Out of memory → Upgrade Railway plan

### App doesn't respond

**Check status:**
```bash
railway status
```

**Restart:**
```bash
railway restart
```

### Upload fails

- Check file size < 2GB
- Check Railway storage limits
- Try smaller test video first

## Local Testing (Before Deploy)

Test the Docker image locally:

```bash
# Build
docker build -t rife-cut-smooth .

# Run
docker run -p 8000:8000 rife-cut-smooth

# Access at http://localhost:8000
```

## Advanced: Custom Domain

1. Go to Railway dashboard
2. Select your project
3. Click "Settings" → "Domains"
4. Add custom domain
5. Update DNS records as instructed

## Monitoring

Railway provides:
- **Logs:** Real-time application logs
- **Metrics:** CPU, memory, network usage
- **Alerts:** Set up via Railway dashboard

Access via:
```bash
railway logs --follow
```

## Updating Deployment

After making code changes:

**Via GitHub:**
```bash
git add .
git commit -m "Update"
git push
# Railway auto-deploys
```

**Via CLI:**
```bash
railway up
```

## Cleanup

To delete the deployment:

**Via Dashboard:**
- Go to project settings
- Click "Danger" → "Delete Project"

**Via CLI:**
```bash
railway down
```

---

**Need help?** Check [Railway docs](https://docs.railway.app) or their Discord support.
