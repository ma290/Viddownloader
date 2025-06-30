# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# Copy project files to /app inside the container
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose HTTP server port
EXPOSE 8000

# Run the bot
CMD ["python", "bot.py"]
