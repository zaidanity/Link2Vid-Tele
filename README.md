# Link2Vid-Tele

A lightweight Telegram bot for downloading TikTok videos and photos directly to your chat — fast, clean, watermark-free.

**Features:**
- ✅ TikTok Videos (watermark-free)
- ✅ TikTok Photos/Slideshows (as album)
- ✅ Short links support (vt.tiktok.com, vm.tiktok.com)
- ✅ Auto URL resolution

---

## 🚀 Quick Start

### 1. Create Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Give your bot a name (e.g., "Link2Vid")
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

### Download TikTok Video

1. Open TikTok, find the video you want
2. Tap **Share** → **Copy Link**
3. Send the link to the bot
4. Video downloads **without watermark** and sends automatically

**Supports:**
- Full TikTok links: `tiktok.com/@username/video/xxx`
- Short links: `vt.tiktok.com/xxxxx` or `vm.tiktok.com/xxxxx`

### Download TikTok Photos/Slideshow

1. Open TikTok photo post or slideshow
2. Tap **Share** → **Copy Link**
3. Send the link to the bot
4. Bot downloads **all images** and sends as an album
   - Up to 10 images per batch
   - Multiple batches sent if needed

---

## 🔧 Features & Limits

| Feature | Details |
|---------|---------|
| TikTok Video | Watermark-free, best quality (720p max) |
| TikTok Photos | Download all images from slideshow |
| Short Links | Auto-resolve vt.tiktok.com, vm.tiktok.com |
| File Size Limit | Max 50MB per file (Telegram limit) |
| Album Limit | Max 50MB total for photo albums |

---

## 📦 Dependencies

```
python-telegram-bot==20.7
yt-dlp==2024.7.1
gallery-dl==1.26.9
requests
```

---

## ⚠️ Important Notes

- **Public Content Only**: Links must be publicly accessible
- **File Limits**: Telegram enforces a 50MB per file limit
- **TikTok Photos**: Total size of all images limited to ~50MB
- **Private Videos**: Will fail if account is private or video is restricted
- **Download Time**: Large videos may take 10-30 seconds

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

### How It Works

1. Bot detects if link is TikTok video or photo
2. For videos: Downloads with yt-dlp, sends as video
3. For photos: Uses gallery-dl, sends as media album
4. Auto-resolves short URLs before processing
5. Cleans up temp files after sending

---

## 📄 License

Personal use and reference. Ensure you respect copyright of downloaded content.

---

## 🤝 Support

- **Link not working?** Make sure it's public and try copying again
- **File too big?** Check video duration (longer = larger file)
- **Bot not responding?** Double-check your BOT_TOKEN in Railway variables

**Repository:** [github.com/zaidanity/Link2Vid-Tele](https://github.com/zaidanity/Link2Vid-Tele)
