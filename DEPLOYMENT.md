# Railway Deployment Guide

Panduan lengkap untuk deploy bot ke Railway.

## Prerequisites

- GitHub account (untuk fork repository)
- Telegram BotFather token
- Railway account (free)

## Step 1: Siapkan BotFather

1. Buka Telegram → cari **@BotFather**
2. Ketik `/newbot`
3. Follow instruksi:
   - Nama bot: *"Link2Vid Downloader"* (atau nama pilihan Anda)
   - Username bot: *"link2vid_tele_bot"* (harus unik)
4. **Copy token yang diberikan**, contoh: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

**Jangan bagikan token ke orang lain!**

## Step 2: Fork Repository (Opsional tapi Disarankan)

1. Buka https://github.com/zaidanity/Link2Vid-Tele
2. Klik **Fork** (pojok kanan atas)
3. Repository akan dicopy ke akun GitHub Anda

Ini memudahkan Anda untuk deploy dan update di masa depan.

## Step 3: Deploy ke Railway

### Cara Termudah - Railway Deploy Button

```markdown
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)
```

Atau langsung buka: https://railway.app/new

### Step-by-Step Railway Setup

1. **Login ke Railway** → https://railway.app
   - Sign up dengan GitHub jika belum punya akun

2. **Create New Project**
   - Klik "+ New" → "New Project"

3. **Connect GitHub Repository**
   - Pilih "GitHub Repo"
   - Authorize Railway untuk akses GitHub
   - Pilih repository `Link2Vid-Tele`

4. **Auto-Deploy**
   - Railway akan membaca `Procfile` secara otomatis
   - Bot akan deploy!

5. **Set Environment Variables**
   - Di Railway dashboard, cari project Anda
   - Klik service "bot" atau yang sedang running
   - Buka tab **"Variables"**
   - Klik "+ Add Variable"
   - Isi:
     - **Key:** `BOT_TOKEN`
     - **Value:** Token dari BotFather (paste here)
   - Klik Save

6. **Restart Bot (jika diperlukan)**
   - Klik tab "Deployments"
   - Klik "Redeploy"

**Bot sekarang LIVE!** 🎉

## Verifikasi Bot Berjalan

1. Buka Telegram
2. Cari bot Anda (username dari langkah 1)
3. Kirim `/start`
4. Jika menerima respon → bot berhasil!

## Troubleshooting

### Bot tidak respond
- **Cek BOT_TOKEN**: Railway Variables → pastikan BOT_TOKEN benar
- **Cek Logs**: Railway Deployments → lihat log error
- **Restart**: Klik Redeploy

### "command not found: python"
- Railway support Python 3.11+ default
- Buat file `railway.json`:
  ```json
  {
    "builder": "heroku.buildpacks",
    "buildpacks": [
      "heroku/python"
    ]
  }
  ```

### Download tidak bekerja
- Cek internet Railway (usually fine)
- Cek link YouTube/TikTok valid & publik
- Lihat Railway logs untuk error detail

## Stop/Delete Bot

- **Pause**: Railway Dashboard → Service → "Pause"
- **Delete**: Railway Dashboard → Settings → "Delete Service"
  - (Tidak bisa recover data setelah delete!)

## Update Bot (Pull Latest Code)

1. Fork Anda → clone latest dari origin
2. Push perubahan ke GitHub fork Anda
3. Railway auto-redeploy ketika push detected!

Atau manual redeploy:
- Railway Dashboard → Deployments → "Redeploy"

---

**Support**: Jika ada pertanyaan, lihat README.md atau buka issue di GitHub.
