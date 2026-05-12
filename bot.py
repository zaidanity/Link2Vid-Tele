import os
import re
import asyncio
import subprocess
import tempfile
import shutil
import requests
import logging
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Konfigurasi
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def is_tiktok_link(url: str) -> bool:
    """Cek apakah link dari TikTok"""
    patterns = [
        r'tiktok\.com',
        r'vt\.tiktok\.com',
        r'vm\.tiktok\.com',
        r'tik tok\.com',
    ]
    return any(re.search(p, url, re.IGNORECASE) for p in patterns)

async def resolve_tiktok_url(short_url: str) -> str:
    """Resolve URL pendek TikTok ke URL asli"""
    try:
        response = requests.get(short_url, allow_redirects=True, timeout=15)
        return response.url
    except Exception as e:
        logging.warning(f"Failed to resolve TikTok URL: {e}")
        return short_url

async def download_tiktok_video(url: str) -> tuple:
    """
    Download TikTok video tanpa watermark
    Return: (file_path, title, file_size_mb, error_message)
    """
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'format': 'best[height<=720]/best',  # 720p maksimal biar kecil
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Cek file exist
            if not os.path.exists(file_path):
                if os.path.exists(file_path + '.mp4'):
                    file_path = file_path + '.mp4'
                elif os.path.exists(file_path.replace('.webm', '.mp4')):
                    file_path = file_path.replace('.webm', '.mp4')
            
            title = info.get('title', 'TikTok Video')[:50]
            title = re.sub(r'[^\w\s\-]', '', title)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            return file_path, title, file_size_mb, None
            
    except Exception as e:
        error_msg = str(e)
        # Deteksi apakah ini photo post
        if 'photo' in error_msg.lower() or 'slideshow' in error_msg.lower():
            return None, None, None, 'PHOTO'
        return None, None, None, error_msg

async def download_tiktok_photo(url: str) -> tuple:
    """
    Download TikTok photo/slideshow
    Return: (list_image_paths, jumlah_gambar, total_size_mb, error_message)
    """
    try:
        temp_dir = tempfile.mkdtemp(dir=DOWNLOAD_DIR)
        
        # Jalankan gallery-dl
        cmd = [
            'gallery-dl',
            '--destination', temp_dir,
            '--filename', '{id}_{num}.{extension}',
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        # Cari semua gambar
        images = []
        total_size = 0
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    path = os.path.join(root, file)
                    images.append(path)
                    total_size += os.path.getsize(path)
        
        if not images:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, 0, 0, "No images found"
        
        total_mb = total_size / (1024 * 1024)
        return images, len(images), total_mb, None
        
    except Exception as e:
        return None, 0, 0, str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TikTok Downloader\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send a TikTok link, get the content.\n\n"
        "Supported: video, photo, slideshow\n"
        "No watermark. No size limit.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/help",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not is_tiktok_link(url):
        await update.message.reply_text(
            "Invalid TikTok link. Please send a valid TikTok URL.",
            parse_mode="Markdown"
        )
        return

    status_msg = await update.message.reply_text("Processing...")

    # Resolve URL pendek kalo perlu
    if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
        url = await resolve_tiktok_url(url)

    # Coba download sebagai video dulu
    file_path, title, file_size, error = await download_tiktok_video(url)

    # Kalau error karena photo, download sebagai photo
    if error == 'PHOTO':
        await status_msg.edit_text("Downloading photos...")

        images, count, total_size, photo_error = await download_tiktok_photo(url)

        if photo_error:
            await status_msg.edit_text(f"Failed: {photo_error[:100]}")
            return

        if total_size > 50:
            await status_msg.edit_text(
                f"File too large: {total_size:.1f}MB (limit: 50MB)"
            )
            for img in images:
                os.remove(img)
            shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)
            return

        # Kirim gambar
        try:
            await status_msg.edit_text(f"Sending {count} photo(s)...")

            if count == 1:
                with open(images[0], 'rb') as img:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=img,
                        caption="TikTok Photo",
                        parse_mode="Markdown"
                    )
            else:
               # Kirim dalam batch (max 10 per album)
for i in range(0, count, 10):
    batch = images[i:i+10]
    media_group = []
    for j, img_path in enumerate(batch):
        with open(img_path, 'rb') as img_file:
            if j == 0 and i == 0:
                media_group.append(
                    InputMediaPhoto(
                        media=img_file,
                        caption=f"TikTok Slideshow ({count} photos)\nDownload via @link2vidsbot"
                    )
                )
            else:
                media_group.append(InputMediaPhoto(media=img_file))
    await context.bot.send_media_group(chat_id=chat_id, media=media_group)
            await status_msg.delete()

            # Bersihkan file
            for img in images:
                os.remove(img)
            shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)

        except Exception as e:
            await status_msg.edit_text(f"Failed to send: {str(e)[:80]}")
            for img in images:
                if os.path.exists(img):
                    os.remove(img)
            shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)

        return

    # Kalau error lain
    if error:
        await status_msg.edit_text("Download failed. Ensure the link is public and accessible.")
        return

    # Kirim video
    if file_size > 50:
        await status_msg.edit_text(f"File too large: {file_size:.1f}MB (limit: 50MB)")
        os.remove(file_path)
        return

    try:
        await status_msg.edit_text("Sending video...")

        with open(file_path, 'rb') as video:
    await context.bot.send_video(
        chat_id=chat_id,
        video=video,
        caption=f"TikTok Video\nDownload via @link2vidsbot",
        supports_streaming=True
    )

        await status_msg.delete()
        os.remove(file_path)

    except Exception as e:
        await status_msg.edit_text(f"Failed to send: {str(e)[:80]}")
        if os.path.exists(file_path):
            os.remove(file_path)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*How to Use*\n\n"
        "1. Open TikTok\n"
        "2. Copy video/photo link\n"
        "3. Send link here\n"
        "4. Wait for download\n\n"
        "Supports: Videos, Photos & Slideshows\n"
        "Formats: tiktok.com & short links (vt.tiktok.com, vm.tiktok.com)",
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN environment variable not found")
        return

    logging.info("TikTok Downloader Bot started")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Import yt-dlp di sini biar ga error kalo pindah-pindah
    import yt_dlp
    main()