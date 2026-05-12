import os
import re
import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# Konfigurasi
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"

# Buat folder download jika belum ada
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Regex untuk mendeteksi link
URL_PATTERNS = {
    'youtube': r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/',
    'tiktok_video': r'(https?://)?(www\.)?tiktok\.com/.*?/video/',
    'tiktok_photo': r'(https?://)?(www\.)?tiktok\.com/.*?/photo/',
}

# Dictionary untuk menyimpan URL sementara (chat_id -> url)
user_urls = {}

def detect_platform(url: str) -> str:
    """Deteksi platform dari URL"""
    # Cek TikTok photo dulu (spesifik)
    if re.search(URL_PATTERNS['tiktok_photo'], url, re.IGNORECASE):
        return 'tiktok_photo'
    
    # Cek TikTok video
    if re.search(URL_PATTERNS['tiktok_video'], url, re.IGNORECASE):
        return 'tiktok_video'
    
    # Cek YouTube
    if re.search(URL_PATTERNS['youtube'], url, re.IGNORECASE):
        return 'youtube'
    
    # Cek TikTok general (fallback untuk link pendek vt.tiktok.com)
    if 'tiktok.com' in url.lower():
        return 'tiktok_unknown'
    
    return None

def get_video_formats(url: str):
    """
    Ambil daftar format video yang tersedia dari YouTube
    Return: list of dict dengan format info
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            
            # Filter format video yang punya height (resolusi)
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('height'):
                    height = f.get('height')
                    fps = f.get('fps', '')
                    
                    # Hindari duplikasi resolusi yang sama
                    if not any(fmt['height'] == height and fmt.get('fps') == fps for fmt in formats):
                        formats.append({
                            'format_id': f['format_id'],
                            'height': height,
                            'fps': fps,
                            'format_note': f.get('format_note', ''),
                            'filesize': f.get('filesize', 0),
                            'ext': f.get('ext', 'mp4')
                        })
            
            # Urutkan dari resolusi tertinggi ke terendah
            formats.sort(key=lambda x: x['height'], reverse=True)
            
            # Hanya ambil resolusi unik (720p, 480p, 360p, dll)
            unique_formats = []
            seen_heights = set()
            for fmt in formats:
                if fmt['height'] not in seen_heights:
                    seen_heights.add(fmt['height'])
                    unique_formats.append(fmt)
            
            return unique_formats, info.get('title', 'Video')
            
    except Exception as e:
        return None, str(e)

async def download_video(url: str, format_id: str = None) -> tuple:
    """
    Download video dengan format tertentu
    Support: YouTube, TikTok Video
    Return: (file_path, title, file_size_mb, error_message)
    """
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }
    
    # Pilih format spesifik jika diberikan
    if format_id:
        ydl_opts['format'] = f'{format_id}+bestaudio/best'
    else:
        ydl_opts['format'] = 'best[height<=720]/best'  # default 720p
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # yt-dlp kadang menambahkan .mp4 sendiri jika perlu
            if not os.path.exists(file_path):
                if os.path.exists(file_path + '.mp4'):
                    file_path = file_path + '.mp4'
                elif os.path.exists(file_path.replace('.webm', '.mp4')):
                    file_path = file_path.replace('.webm', '.mp4')
                elif os.path.exists(file_path.replace('.mkv', '.mp4')):
                    file_path = file_path.replace('.mkv', '.mp4')
            
            title = info.get('title', 'video')
            # Bersihkan title dari karakter aneh
            title = re.sub(r'[^\w\s\-]', '', title)[:60]
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            return file_path, title, file_size_mb, None
            
    except Exception as e:
        return None, None, None, str(e)

async def download_tiktok_photo(url: str) -> tuple:
    """
    Download TikTok photo post menggunakan gallery-dl via subprocess
    Return: (list_of_image_paths, title, total_size_mb, error_message)
    """
    try:
        # Buat folder sementara
        temp_dir = tempfile.mkdtemp(dir=DOWNLOAD_DIR)
        
        # Jalankan gallery-dl sebagai subprocess
        # --destination untuk folder tujuan
        # --range untuk hanya download gambar
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
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            # Hapus folder temp jika error
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, None, None, f"gallery-dl error: {error_msg[:200]}"
        
        # Cari semua gambar yang didownload
        image_files = []
        total_size = 0
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    file_path = os.path.join(root, file)
                    image_files.append(file_path)
                    total_size += os.path.getsize(file_path)
        
        if not image_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None, None, None, "No images found in photo post"
        
        # Ambil title dari username atau gunakan default
        title = f"TikTok Photo ({len(image_files)} images)"
        
        total_size_mb = total_size / (1024 * 1024)
        
        return image_files, title, total_size_mb, None
        
    except Exception as e:
        return None, None, None, str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /start"""
    await update.message.reply_text(
        "🎬 *Bot Downloader Video*\n\n"
        "Kirimkan link video dari:\n"
        "✓ YouTube (dengan pilihan resolusi)\n"
        "✓ TikTok Video (tanpa watermark)\n"
        "✓ TikTok Photo/Slideshow 🆕\n\n"
        "📹 *Fitur YouTube:*\n"
        "• Pilih resolusi 144p sampai 4K\n"
        "• Download audio MP3\n\n"
        "🖼️ *Fitur TikTok Photo:*\n"
        "• Download semua gambar dalam slideshow\n"
        "• Dikirim sebagai album/gallery\n\n"
        "⚠️ *Batasan:* Total file maksimal 50MB per post.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pesan berisi link"""
    url = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    # Deteksi platform
    platform = detect_platform(url)
    
    # Handle TikTok Photo
    if platform == 'tiktok_photo':
        status_msg = await update.message.reply_text(
            "🖼️ *Mendownload TikTok Photo Post...*\n"
            "⏳ Mengambil semua gambar dari slideshow...\n"
            "✨ Photo posts sekarang didukung!",
            parse_mode="Markdown"
        )
        
        images, title, total_size, error = await download_tiktok_photo(url)
        
        if error:
            await status_msg.edit_text(
                f"❌ *Gagal mendownload TikTok Photo*\n\n"
                f"Error: `{error[:200]}`\n\n"
                f"💡 *Tips:*\n"
                f"• Pastikan link bisa diakses publik\n"
                f"• Coba buka link di browser dulu\n"
                f"• Pastikan akun TikTok tidak private",
                parse_mode="Markdown"
            )
            return
        
        if total_size > 50:
            await status_msg.edit_text(
                f"⚠️ *Total ukuran terlalu besar*\n\n"
                f"Jumlah gambar: `{len(images)}`\n"
                f"Total ukuran: `{total_size:.1f} MB`\n"
                f"Batasan Telegram: `50 MB`\n\n"
                f"💡 Tidak bisa mengirim album karena terlalu besar.",
                parse_mode="Markdown"
            )
            # Hapus file-file yang sudah didownload
            for img in images:
                if os.path.exists(img):
                    os.remove(img)
            # Hapus folder temp
            if images:
                folder = os.path.dirname(images[0])
                shutil.rmtree(folder, ignore_errors=True)
            return
        
        # Kirim gambar sebagai media group (album)
        try:
            await status_msg.edit_text(
                f"✅ *Download berhasil!*\n"
                f"📸 `{len(images)}` gambar ditemukan\n"
                f"📦 Total ukuran: `{total_size:.1f} MB`\n\n"
                f"📤 *Mengirim album...*",
                parse_mode="Markdown"
            )
            
            if len(images) == 1:
                # Single photo
                with open(images[0], 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_file,
                        caption=f"🖼️ *TikTok Photo*\n\n📱 Download dari TikTok",
                        parse_mode="Markdown"
                    )
            else:
                # Multiple photos as album (max 10 per batch)
                for i in range(0, len(images), 10):
                    batch = images[i:i+10]
                    media_group = []
                    
                    for j, img_path in enumerate(batch):
                        with open(img_path, 'rb') as img_file:
                            if j == 0 and i == 0:
                                media_group.append(
                                    InputMediaPhoto(
                                        media=img_file,
                                        caption=f"🖼️ *TikTok Slideshow*\n📸 {len(images)} images\n\n📱 Download dari TikTok",
                                        parse_mode="Markdown"
                                    )
                                )
                            else:
                                media_group.append(InputMediaPhoto(media=img_file))
                    
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)
            
            await status_msg.delete()
            
            # Bersihkan file
            for img in images:
                if os.path.exists(img):
                    os.remove(img)
            if images:
                folder = os.path.dirname(images[0])
                shutil.rmtree(folder, ignore_errors=True)
            
        except Exception as e:
            await status_msg.edit_text(
                f"❌ *Gagal mengirim album*\n\nError: `{str(e)[:200]}`",
                parse_mode="Markdown"
            )
            # Bersihkan file
            for img in images:
                if os.path.exists(img):
                    os.remove(img)
            if images:
                folder = os.path.dirname(images[0])
                shutil.rmtree(folder, ignore_errors=True)
        return
    
    # Handle TikTok Unknown (link pendek yang belum ke-resolve)
    if platform == 'tiktok_unknown':
        await update.message.reply_text(
            "🔍 *Mendeteksi link TikTok...*\n"
            "Silakan tunggu sebentar, bot sedang memproses link.",
            parse_mode="Markdown"
        )
        # Kita coba cek dengan yt-dlp untuk resolusi URL (tanpa download)
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                webpage_url = info.get('webpage_url', '')
                if '/photo/' in webpage_url:
                    # Re-process sebagai photo
                    platform = 'tiktok_photo'
                    # Handle lagi sebagai photo (panggil ulang fungsi dengan platform yang sudah benar)
                    await handle_message(update, context)
                    return
                elif '/video/' in webpage_url:
                    platform = 'tiktok_video'
                else:
                    await update.message.reply_text(
                        "❌ *Tidak dapat menentukan jenis konten*\n\n"
                        "Pastikan link TikTok valid dan bisa diakses.",
                        parse_mode="Markdown"
                    )
                    return
        except Exception as e:
            await update.message.reply_text(
                f"❌ *Gagal memproses link TikTok*\n\n"
                f"Error: `{str(e)[:150]}`\n\n"
                f"💡 Pastikan link valid.",
                parse_mode="Markdown"
            )
            return
    
    # Handle YouTube dengan pilihan resolusi
    if platform == 'youtube':
        status_msg = await update.message.reply_text(
            "📹 *Mengambil daftar resolusi...*\n⏳ Mohon tunggu sebentar.",
            parse_mode="Markdown"
        )
        
        # Ambil daftar format video
        formats, title = get_video_formats(url)
        
        if not formats:
            await status_msg.edit_text(
                "❌ *Gagal mengambil daftar resolusi*\n\n"
                "Pastikan link YouTube valid dan video bisa diakses.",
                parse_mode="Markdown"
            )
            return
        
        # Simpan URL untuk user ini
        user_urls[chat_id] = url
        
        # Buat tombol pilihan resolusi
        keyboard = []
        for fmt in formats[:8]:  # Maksimal 8 resolusi
            height = fmt['height']
            filesize_mb = fmt['filesize'] / (1024 * 1024) if fmt['filesize'] else 0
            
            # Format teks tombol
            if filesize_mb > 0 and filesize_mb < 100:
                button_text = f"{height}p - {filesize_mb:.1f} MB"
            elif filesize_mb >= 100:
                button_text = f"{height}p - >100 MB (⚠️ terlalu besar)"
            else:
                button_text = f"{height}p - Ukuran tidak diketahui"
            
            # Tambahkan FPS jika lebih dari 30
            if fmt.get('fps') and fmt['fps'] > 30:
                button_text = button_text.replace(f"{height}p", f"{height}p{fmt['fps']}")
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"yt_{fmt['format_id']}")])
        
        # Tambahan tombol download audio
        keyboard.append([InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data="yt_audio")])
        keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Peringatan jika video kemungkinan besar >50MB
        warning = ""
        if formats and formats[0].get('filesize', 0) > 50 * 1024 * 1024:
            warning = "\n\n⚠️ *Peringatan:* Video resolusi tertinggi kemungkinan >50MB dan tidak bisa dikirim Telegram. Pilih resolusi lebih rendah."
        
        await status_msg.edit_text(
            f"🎬 *{title[:60]}*\n\n"
            f"Pilih resolusi video yang diinginkan:{warning}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    # Handle TikTok Video (langsung download tanpa pilihan)
    elif platform == 'tiktok_video':
        status_msg = await update.message.reply_text(
            "📥 *Sedang memproses TikTok video...*\n"
            "⏳ Mohon tunggu 10-30 detik.\n"
            "✨ TikTok akan dikirim tanpa watermark.",
            parse_mode="Markdown"
        )
        
        file_path, title, file_size, error = await download_video(url)
        
        if error:
            await status_msg.edit_text(
                f"❌ *Gagal mendownload TikTok*\n\n"
                f"Error: `{error[:200]}`\n\n"
                f"💡 Mungkin:\n"
                f"• Link perlu di-recopy dari TikTok\n"
                f"• Video bersifat private",
                parse_mode="Markdown"
            )
            return
        
        if file_size > 50:
            await status_msg.edit_text(
                f"⚠️ *Ukuran video terlalu besar*\n\n"
                f"Ukuran: `{file_size:.1f} MB`\n"
                f"Batasan Telegram: `50 MB`\n\n"
                f"💡 Coba link TikTok lain dengan durasi lebih pendek.",
                parse_mode="Markdown"
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            return
        
        try:
            await status_msg.edit_text(
                f"✅ *Download berhasil!*\n"
                f"📦 Ukuran: `{file_size:.1f} MB`\n\n"
                f"📤 *Sedang mengirim video...*",
                parse_mode="Markdown"
            )
            
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=f"🎬 *{title}*\n\n📱 Download dari TikTok (No Watermark)",
                    parse_mode="Markdown",
                    supports_streaming=True
                )
            
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
            
        except Exception as e:
            await status_msg.edit_text(
                f"❌ *Gagal mengirim video*\n\nError: `{str(e)[:200]}`",
                parse_mode="Markdown"
            )
            if os.path.exists(file_path):
                os.remove(file_path)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk tombol pilihan resolusi"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    
    # Handle cancel
    if data == "cancel":
        await query.message.edit_text("❌ Download dibatalkan.")
        if chat_id in user_urls:
            del user_urls[chat_id]
        return
    
    # Handle download audio
    if data == "yt_audio":
        await query.message.edit_text(
            "🎵 *Mengunduh audio...*\n"
            "⏳ Mohon tunggu sebentar.",
            parse_mode="Markdown"
        )
        
        url = user_urls.get(chat_id)
        if not url:
            await query.message.edit_text("❌ URL tidak ditemukan. Silakan kirim link YouTube lagi.")
            return
        
        # Download audio
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
                
                if not os.path.exists(file_path):
                    file_path = file_path.replace('.webm', '.mp3')
                
                title = info.get('title', 'audio')
                title = re.sub(r'[^\w\s\-]', '', title)[:50]
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                
                if file_size_mb > 50:
                    await query.message.edit_text(
                        f"⚠️ *Ukuran audio terlalu besar*\n\nUkuran: `{file_size_mb:.1f} MB`",
                        parse_mode="Markdown"
                    )
                    os.remove(file_path)
                    return
                
                await query.message.edit_text(
                    f"✅ *Audio berhasil!*\n📦 Ukuran: `{file_size_mb:.1f} MB`\n\n📤 *Mengirim...*",
                    parse_mode="Markdown"
                )
                
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_file,
                        title=title,
                        performer="YouTube"
                    )
                
                os.remove(file_path)
                
        except Exception as e:
            await query.message.edit_text(
                f"❌ *Gagal download audio*\n\nError: `{str(e)[:200]}`",
                parse_mode="Markdown"
            )
        
        if chat_id in user_urls:
            del user_urls[chat_id]
        return
    
    # Handle download video
    if data.startswith("yt_"):
        format_id = data[3:]
        url = user_urls.get(chat_id)
        
        if not url:
            await query.message.edit_text("❌ URL tidak ditemukan.")
            return
        
        await query.message.edit_text(
            "📥 *Mengunduh video...*\n⏳ Bisa memakan waktu 1-3 menit.",
            parse_mode="Markdown"
        )
        
        file_path, title, file_size, error = await download_video(url, format_id)
        
        if error:
            await query.message.edit_text(f"❌ *Gagal*\n\nError: `{error[:200]}`", parse_mode="Markdown")
            if chat_id in user_urls:
                del user_urls[chat_id]
            return
        
        if file_size > 50:
            await query.message.edit_text(
                f"⚠️ *Ukuran terlalu besar:* `{file_size:.1f} MB`\n💡 Pilih resolusi lebih rendah.",
                parse_mode="Markdown"
            )
            os.remove(file_path)
            if chat_id in user_urls:
                del user_urls[chat_id]
            return
        
        try:
            await query.message.edit_text(
                f"✅ *Berhasil!*\n📦 Ukuran: `{file_size:.1f} MB`\n\n📤 *Mengirim...*",
                parse_mode="Markdown"
            )
            
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=f"🎬 *{title}*\n\n📥 YouTube",
                    parse_mode="Markdown",
                    supports_streaming=True
                )
            
            await query.message.delete()
            os.remove(file_path)
            
        except Exception as e:
            await query.message.edit_text(f"❌ *Gagal kirim:* `{str(e)[:200]}`", parse_mode="Markdown")
            if os.path.exists(file_path):
                os.remove(file_path)
        
        if chat_id in user_urls:
            del user_urls[chat_id]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /help"""
    await update.message.reply_text(
        "📖 *Panduan Penggunaan*\n\n"
        "*YouTube:* Kirim link → pilih resolusi\n"
        "*TikTok Video:* Kirim link → auto download\n"
        "*TikTok Photo:* Kirim link → download semua gambar 🆕\n\n"
        "⚠️ Maksimal 50MB\n"
        "📞 Source: GitHub",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

def main():
    """Main function"""
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN tidak ditemukan!")
        return
    
    print("🚀 Bot sedang berjalan...")
    print("   Support: YouTube, TikTok Video, TikTok Photo 🆕")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()