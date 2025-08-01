FROM python:3.11

# Set working directory
WORKDIR /app

# Set environment variables


# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libev-dev \
    gcc \
    git \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (excluding torch)
COPY requirements.txt /app/

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt 
 # Uninstall torch if it got installed by accident (optional, safer to remove torch from requirements.txt)
RUN pip uninstall -y torch || true

# Copy rest of the app
COPY . /app/

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "main.py"]
