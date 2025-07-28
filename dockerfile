# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CASS_DRIVER_NO_EXTENSIONS=1
ENV TRANSFORMERS_CACHE=/app/hf_cache
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libev-dev \
    gcc \
    git \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install tiktoken

# Pre-download Hugging Face model and tokenizer
RUN python -c "\
from transformers import AutoModel, AutoTokenizer; \
AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2'); \
AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')"

# Copy the rest of the app
COPY . /app/

# Expose port (optional)
EXPOSE 8000

# Run the app
CMD ["python", "main.py"]
