# RIFE Cut Smooth - Railway Deployment v7 (RIFE models baked into image)
FROM python:3.11-slim

# Install system dependencies (ffmpeg for video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install RIFE from GitHub (PyTorch-based implementation)
RUN pip install --no-cache-dir git+https://github.com/xhluca/rife

# Download RIFE HDv2 pretrained models during Docker build
# This ensures models are baked into the image
RUN mkdir -p /app/train_log && \
    cd /tmp && \
    wget --no-check-certificate -O rife_hdv2.zip "https://drive.usercontent.google.com/download?id=1wsQIhHZ3Eg4_AfCXItFKqqyDMB4NS0Yd&export=download&confirm=t" && \
    unzip -q rife_hdv2.zip -d /app/train_log && \
    rm rife_hdv2.zip

# Copy application code
COPY rife_cut_smooth/ ./rife_cut_smooth/
COPY setup.py .
COPY README.md .

# Create directories for file uploads/outputs
RUN mkdir -p /app/uploads /app/outputs

# Expose port for web interface
EXPOSE 8000

# Run the web server
CMD ["python", "-m", "rife_cut_smooth.web"]
