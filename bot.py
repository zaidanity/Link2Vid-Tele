import os
import re
import asyncio
import subprocess
import tempfile
import shutil
import requests
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
        print(f"Resolve error: {e}")
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
        "🎵 *TikTok Downloader Bot*\n\n"
        "Kirimkan link TikTok, bot akan download:\n"
        "✓ Video (tanpa watermark)\n"
        "✓ Foto/Slideshow (semua gambar)\n\n"
        "Support link:\n"
        "• tiktok.com/@username/video/xxx\n"
        "• tiktok.com/@username/photo/xxx\n"
        "• vt.tiktok.com/xxxxx\n"
        "• vm.tiktok.com/xxxxx\n\n"
        "⚠️ Maksimal 50MB (kebijakan Telegram)",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    # Cek apakah link TikTok
    if not is_tiktok_link(url):
        await update.message.reply_text(
            "❌ *Bukan link TikTok!*\n\n"
            "Bot ini khusus untuk download video & foto dari TikTok.\n"
            "Silakan kirim link TikTok yang valid.",
            parse_mode="Markdown"
        )
        return
    
    status_msg = await update.message.reply_text(
        "🔍 *Memproses link TikTok...*\n⏳ Mohon tunggu sebentar.",
        parse_mode="Markdown"
    )
    
    # Resolve URL pendek kalo perlu
    if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
        url = await resolve_tiktok_url(url)
        await status_msg.edit_text(
            f"✅ *Link resolved*\n"
            f"Sedang memproses...",
            parse_mode="Markdown"
        )
    
    # Coba download sebagai video dulu
    file_path, title, file_size, error = await download_tiktok_video(url)
    
    # Kalau error karena photo, download sebagai photo
    if error == 'PHOTO':
        await status_msg.edit_text(
            "🖼️ *Mendeteksi postingan FOTO...*\n"
            "Mengunduh semua gambar...",
            parse_mode="Markdown"
        )
        
        images, count, total_size, photo_error = await download_tiktok_photo(url)
        
        if photo_error:
            await status_msg.edit_text(
                f"❌ *Gagal download foto*\n\nError: `{photo_error[:150]}`\n\n"
                f"Pastikan link bisa diakses publik.",
                parse_mode="Markdown"
            )
            return
        
        if total_size > 50:
            await status_msg.edit_text(
                f"⚠️ *Total ukuran terlalu besar*\n\n"
                f"Jumlah gambar: `{count}`\n"
                f"Total ukuran: `{total_size:.1f} MB`\n"
                f"Batasan Telegram: `50 MB`\n\n"
                f"Tidak bisa mengirim album karena terlalu besar.",
                parse_mode="Markdown"
            )
            # Bersihkan file
            for img in images:
                os.remove(img)
            shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)
            return
        
        # Kirim gambar
        try:
            await status_msg.edit_text(
                f"✅ *{count} gambar* berhasil didownload!\n"
                f"📦 Total: `{total_size:.1f} MB`\n\n"
                f"📤 *Mengirim album...*",
                parse_mode="Markdown"
            )
            
            if count == 1:
                with open(images[0], 'rb') as img:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=img,
                        caption="🖼️ *TikTok Photo*\n📱 Download dari TikTok",
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
                                        caption=f"🖼️ *TikTok Slideshow*\n📸 {count} images\n\n📱 Download dari TikTok",
                                        parse_mode="Markdown"
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
            await status_msg.edit_text(
                f"❌ *Gagal mengirim album*\n\nError: `{str(e)[:150]}`",
                parse_mode="Markdown"
            )
            for img in images:
                if os.path.exists(img):
                    os.remove(img)
            shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)
        
        return
    
    # Kalau error lain
    if error:
        await status_msg.edit_text(
            f"❌ *Gagal mendownload*\n\n"
            f"Error: `{error[:200]}`\n\n"
            f"💡 *Tips:*\n"
            f"• Pastikan link bisa diakses\n"
            f"• Coba buka link di browser dulu\n"
            f"• Pastikan postingan tidak private",
            parse_mode="Markdown"
        )
        return
    
    # Kirim video
    if file_size > 50:
        await status_msg.edit_text(
            f"⚠️ *Ukuran video terlalu besar*\n\n"
            f"Ukuran: `{file_size:.1f} MB`\n"
            f"Batasan Telegram: `50 MB`\n\n"
            f"💡 Coba link video dengan durasi lebih pendek.",
            parse_mode="Markdown"
        )
        os.remove(file_path)
        return
    
    try:
        await status_msg.edit_text(
            f"✅ *Download berhasil!*\n"
            f"📦 Ukuran: `{file_size:.1f} MB`\n\n"
            f"📤 *Sedang mengirim video...*",
            parse_mode="Markdown"
        )
        
        with open(file_path, 'rb') as video:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=f"🎬 *{title}*\n\n📱 TikTok (No Watermark)",
                parse_mode="Markdown",
                supports_streaming=True
            )
        
        await status_msg.delete()
        os.remove(file_path)
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Gagal mengirim video*\n\nError: `{str(e)[:150]}`",
            parse_mode="Markdown"
        )
        if os.path.exists(file_path):
            os.remove(file_path)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cara Pakai*\n\n"
        "1. Buka TikTok\n"
        "2. Tekan Share → Copy Link\n"
        "3. Paste di chat ini\n"
        "4. Tunggu video/foto terkirim\n\n"
        "✅ Support video & foto\n"
        "✅ Tanpa watermark\n"
        "✅ Link pendek (vt.tiktok.com) juga bisa\n\n"
        "Kirim link sekarang! 🚀",
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN tidak ditemukan!")
        print("   Set environment variable BOT_TOKEN di Railway.")
        return
    
    print("🚀 TikTok Downloader Bot berjalan...")
    print("   Support: Video & Photo/Slideshow")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Import yt-dlp di sini biar ga error kalo pindah-pindah
    import yt_dlp
    main()