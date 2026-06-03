# Use an official lightweight Python runtime
FROM python:3.11-slim

# Install system dependencies (FFmpeg and FFprobe are required for the rendering engine)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory inside the container
WORKDIR /app

# Copy requirements from the backend folder and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (frontend and backend) into the container
COPY . .

# Set environment variables for the temporary directories
# Hugging Face and other free tiers require writing to /tmp for permission consistency
ENV CACHE_DIR="/tmp/cache"
ENV OUTPUT_DIR="/tmp/static/outputs"
ENV VOICEOVER_DIR="/tmp/static/voiceovers"
ENV LOFI_TRACKS_DIR="/tmp/static/lofi"
ENV PYTHONPATH="/app/backend"

# Expose port (FastAPI default, overridden by deployment platforms)
EXPOSE 7860

# Run the FastAPI app. We run it by telling uvicorn to look inside the backend module
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
