# Use Python 3.11 slim (fully compatible with ptb v13.15)
FROM python:3.11-slim

# Set environment variables to prevent .pyc files and enable instant log output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# Copy your bot files into the container
COPY . /app

# Install system dependencies (FFmpeg is required for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "bot.py"]
