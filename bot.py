import os
import re
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Konfigurasi
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Akan diisi di Railway environment
DOWNLOAD_DIR = "downloads"

# Buat folder download jika belum ada
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Regex untuk mendeteksi link
URL_PATTERNS = {
    'youtube': r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/',
    'tiktok': r'(https?://)?(www\.)?(tiktok\.com|vt\.tiktok\.com)/',
    'instagram': r'(https?://)?(www\.)?instagram\.com/',
}

def detect_platform(url: str) -> str:
    """Deteksi platform dari URL"""
    for platform, pattern in URL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None

async def download_video(url: str) -> tuple:
    """
    Download video menggunakan yt-dlp
    Return: (file_path, title, error_message)
    """
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best[height<=720]/best',  # Maksimal 720p untuk ukuran lebih kecil
        'merge_output_format': 'mp4',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # yt-dlp kadang menambahkan .mp4 sendiri jika perlu
            if not os.path.exists(file_path):
                file_path = file_path.replace('.webm', '.mp4').replace('.mkv', '.mp4')
            
            title = info.get('title', 'video')
            return file_path, title, None
            
    except Exception as e:
        return None, None, str(e)

def get_file_size_mb(file_path: str) -> float:
    """Dapatkan ukuran file dalam MB"""
    return os.path.getsize(file_path) / (1024 * 1024)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /start"""
    await update.message.reply_text(
        "🎬 *Bot Downloader Video*\n\n"
        "Kirimkan link video dari:\n"
        "✓ YouTube\n"
        "✓ TikTok (tanpa watermark)\n"
        "✓ Instagram\n\n"
        "Bot akan mengirimkan video langsung ke chat ini!\n\n"
        "⚠️ *Batasan:* Video maksimal 50MB karena kebijakan Telegram.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pesan berisi link"""
    url = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    # Deteksi platform
    platform = detect_platform(url)
    
    if not platform:
        await update.message.reply_text(
            "❌ *Maaf, link tidak dikenali*\n\n"
            "Pastikan link dari:\n"
            "• YouTube\n"
            "• TikTok\n"
            "• Instagram",
            parse_mode="Markdown"
        )
        return
    
    # Kirim pesan proses
    status_msg = await update.message.reply_text(
        f"📥 *Sedang memproses* {'TikTok' if platform == 'tiktok' else platform.title()} video...\n"
        f"⏳ Mohon tunggu, ini bisa memakan waktu 10-30 detik.",
        parse_mode="Markdown"
    )
    
    # Download video
    file_path, title, error = await download_video(url)
    
    if error:
        await status_msg.edit_text(
            f"❌ *Gagal mendownload video*\n\n"
            f"Error: `{error[:200]}`\n\n"
            f"💡 *Tips:* Pastikan link bisa diakses publik atau coba link lain.",
            parse_mode="Markdown"
        )
        return
    
    # Cek ukuran file
    file_size = get_file_size_mb(file_path)
    
    if file_size > 50:
        # Ukuran melebihi batas Telegram
        await status_msg.edit_text(
            f"⚠️ *Ukuran video terlalu besar*\n\n"
            f"File: `{title}`\n"
            f"Ukuran: `{file_size:.1f} MB`\n\n"
            f"Telegram hanya mengizinkan file maksimal 50MB.\n\n"
            f"💡 *Solusi:* Kirim link video dengan resolusi lebih rendah.",
            parse_mode="Markdown"
        )
        os.remove(file_path)
        return
    
    # Kirim video
    try:
        await status_msg.edit_text(
            f"✅ *Download berhasil!*\n"
            f"🎬 *{title[:50]}*\n"
            f"📦 Ukuran: `{file_size:.1f} MB`\n\n"
            f"📤 *Sedang mengirim video...*",
            parse_mode="Markdown"
        )
        
        with open(file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=f"🎬 *{title[:60]}*\n\n"
                       f"[Download dari {platform.title()}]",
                parse_mode="Markdown",
                supports_streaming=True
            )
        
        # Hapus status message dan file setelah terkirim
        await status_msg.delete()
        os.remove(file_path)
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Gagal mengirim video*\n\n"
            f"Error: `{str(e)[:200]}`",
            parse_mode="Markdown"
        )
        if os.path.exists(file_path):
            os.remove(file_path)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /help"""
    await update.message.reply_text(
        "📖 *Cara Penggunaan*\n\n"
        "1. Copy link video dari:\n"
        "   • YouTube 🤍\n"
        "   • TikTok (tanpa watermark)\n"
        "   • Instagram\n\n"
        "2. Paste link di chat ini\n"
        "3. Tunggu bot memproses\n"
        "4. Video akan dikirim otomatis\n\n"
        "⚠️ *Catatan:*\n"
        "• Video maksimal 50MB\n"
        "• Proses bisa memakan waktu 10-30 detik\n"
        "• Untuk hasil terbaik, gunakan link publik\n\n"
        "📞 *Source Code:* [GitHub Repository]",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

def main():
    """Main function untuk menjalankan bot"""
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN tidak ditemukan!")
        print("   Set environment variable BOT_TOKEN di Railway.")
        return
    
    print("🚀 Bot sedang berjalan...")
    print(f"   Token: {BOT_TOKEN[:10]}...")
    
    # Buat application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Tambahkan handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()