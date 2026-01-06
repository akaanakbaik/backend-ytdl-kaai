import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from config import Config

if not Config.TELE_TOKEN:
    print("WARNING: TELE_TOKEN is missing in Config!")

# --- CARA INISIALISASI YANG LEBIH AMAN ---
# Hapus DefaultBotProperties, masukkan parse_mode langsung saat send message nanti
# atau set default di Dispatcher jika versi support.
try:
    # Coba cara V3 terbaru
    from aiogram.client.default import DefaultBotProperties
    bot = Bot(token=Config.TELE_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
except ImportError:
    # Fallback untuk versi lama/berbeda (Safe Mode)
    bot = Bot(token=Config.TELE_TOKEN, parse_mode="HTML")

dp = Dispatcher()

# Simple Dictionary based I18n
I18N = {
    "id": {
        "welcome": "<b>👋 Halo!</b>\nSaya adalah <b>KAAI Bot Assistant</b>.\n\nGunakan menu di bawah untuk akses fitur.",
        "processing": "⏳ <b>Sedang Memproses...</b>\nMohon tunggu sebentar.",
        "downloading": "🚀 <b>Sedang Mengunduh...</b>\nFile sedang diambil dari server.",
        "uploading": "outbox <b>Mengunggah ke Telegram...</b>",
        "success": "✅ <b>Berhasil!</b>",
        "failed": "❌ <b>Gagal!</b>",
        "backup_start": "📦 <b>Memulai Backup...</b>",
        "backup_done": "✅ <b>Backup Selesai!</b>",
        "select_format": "👇 <b>Pilih Format Unduhan:</b>"
    }
}

def get_text(key, lang="id"):
    return I18N.get(lang, I18N["id"]).get(key, key)
