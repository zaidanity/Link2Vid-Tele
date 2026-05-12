# Link2Vid-Tele

A lightweight Telegram bot for downloading videos and photos from popular platforms directly to your chat.

**Supported Platforms:**
- ✅ YouTube (with resolution selection up to 4K)
- ✅ TikTok Videos (watermark-free)
- ✅ TikTok Photos/Slideshows (as album)

---

## 🚀 Quick Start

### 1. Create Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Give your bot a name (e.g., "Link2Vid Downloader")
4. Give your bot a username (e.g., "link2vid_tele_bot")
5. **Copy the bot token** - you'll need this

Example token: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

### 2. Deploy to Railway

**Option A: Direct Railway Deploy (Easiest)**

1. Click: [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
2. Connect your GitHub account (fork this repo first if needed)
3. Select this repository
4. Add environment variables in Railway dashboard:
   - `BOT_TOKEN`: Your token from BotFather

**Option B: Manual Setup**

```bash
# Clone repository
git clone https://github.com/zaidanity/Link2Vid-Tele.git
cd Link2Vid-Tele

# Create virtual environment
python -m venv venv

# Activate venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable and run
# On Windows (PowerShell):
$env:BOT_TOKEN = "your_token_here"
python bot.py

# On Linux/macOS:
export BOT_TOKEN="your_token_here"
python bot.py
```

### 3. Environment Variables Setup (Railway)

In Railway dashboard, go to **Variables** and add:

```
BOT_TOKEN=your_telegram_bot_token_here
```

Your bot will automatically start when deployed!

---

## 📱 How to Use

### YouTube Downloads

1. Send a YouTube link to the bot (e.g., `https://youtu.be/...` or `youtube.com/watch?v=...`)
2. Bot shows available resolutions and file sizes
3. Click your preferred resolution to download
4. Video sends automatically

**Features:**
- Select video quality: 144p → 4K (if available)
- Download only audio as MP3 file
- Respects Telegram's 50MB file limit

### TikTok Videos

1. Open TikTok, find the video you want
2. Tap **Share** → **Copy Link**
3. Send the link to the bot
4. Video downloads **without watermark** and sends automatically

### TikTok Photos/Slideshow

1. Open TikTok photo post or slideshow
2. Tap **Share** → **Copy Link**
3. Send the link to the bot
4. Bot downloads **all images** and sends as an album

---

## 🔧 Features & Limits

| Feature | Details |
|---------|---------|
| YouTube Resolutions | 144p, 240p, 360p, 480p, 720p, 1080p, 4K (varies by video) |
| Audio Download | YouTube to MP3 (192 kbps) |
| TikTok Video | Watermark-free download |
| TikTok Photos | Download all images in slideshow |
| File Size Limit | Max 50MB per file (Telegram limit) |
| Album Size Limit | Max 50MB total for photo albums |

---

## 📦 Dependencies

```
python-telegram-bot==20.7
yt-dlp==2024.7.1
gallery-dl==1.26.9
```

---

## ⚠️ Important Notes

- **Public Content Only**: Links must be publicly accessible
- **File Limits**: Telegram enforces a 50MB per file limit
- **TikTok Photos**: Total size of all images in slideshow limited to ~50MB
- **Private Videos**: Will fail if account is private or video is restricted
- **Download Time**: Large files (1GB+) may take several minutes

---

## 🛠️ Development

### Running Locally

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run
BOT_TOKEN="your_token" python bot.py
```

### Architecture

- `bot.py` - Main bot logic and handlers
- `requirements.txt` - Python dependencies
- Handlers: YouTube selection menu → TikTok auto-download → Photo albums

---

## 📄 License

Personal use and reference. Ensure you respect copyright of downloaded content.

---

## 🤝 Support

- **Issue with link?** Make sure it's public and try copying again
- **File too big?** Select lower resolution or check video duration
- **Still stuck?** Double-check your BOT_TOKEN in Railway variables

**Repository:** [github.com/zaidanity/Link2Vid-Tele](https://github.com/zaidanity/Link2Vid-Tele)
