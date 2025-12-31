# RIFE Cut Smooth - Railway Deployment
FROM python:3.11-slim

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    vulkan-tools \
    libvulkan1 \
    build-essential \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install RIFE (Linux version works reliably)
RUN pip install --no-cache-dir rife-ncnn-vulkan-python

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
