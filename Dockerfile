FROM python:3.11-slim

# Install ffmpeg (diperlukan untuk yt-dlp merge video+audio)
# Install gallery-dl dan dependensinya
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gallery-dl via pip juga (sudah di requirements.txt)
# tapi pastikan

COPY . .

CMD ["python", "bot.py"]