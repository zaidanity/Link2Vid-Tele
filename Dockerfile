FROM python:3.11-slim

# Install ffmpeg (untuk yt-dlp) dan gallery-dl
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]