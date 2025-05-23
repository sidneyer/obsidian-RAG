# Use Python 3.10 slim image with platform-specific base
FROM --platform=$BUILDPLATFORM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV LLAMA_METAL=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies with platform-specific optimizations
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ .

# Create necessary directories
RUN mkdir -p models data config

# Expose port
EXPOSE 8000

# Set default command with platform-specific optimizations
CMD ["python", "-c", \
     "import platform; \
      is_arm = platform.machine() == 'arm64'; \
      metal_env = 'LLAMA_METAL=1 ' if is_arm else ''; \
      cmd = f'{metal_env}uvicorn run:app --host 0.0.0.0 --port 8000'; \
      import os; \
      os.system(cmd)"] 