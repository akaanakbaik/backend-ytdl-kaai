import asyncio
import schedule
import time
import os
from datetime import datetime
from config import Config
from aiogram.types import FSInputFile
from .loader import bot
from .system.db import _init_db

# IMPORT YANG DIPERBAIKI (Gunakan perform_smart_backup)
from .feature.backup import perform_smart_backup 

def run_scheduler_loop():
    """Loop untuk menjalankan pending schedule"""
    while True:
        schedule.run_pending()
        time.sleep(60)

async def auto_backup_task():
    """Backup otomatis dikirim ke Admin"""
    if not Config.TELE_ADMIN_ID: return
    
    # Gunakan fungsi baru
    path, status = await perform_smart_backup()
    
    if path:
        try:
            await bot.send_document(
                Config.TELE_ADMIN_ID, 
                FSInputFile(path), 
                caption=f"📦 <b>Auto Backup 3-Daily</b>\n📅 {datetime.now().strftime('%Y-%m-%d')}\n{status}"
            )
            os.remove(path)
        except: pass

def start_bot_scheduler():
    # Backup setiap 3 hari
    schedule.every(3).days.at("00:00").do(lambda: asyncio.create_task(auto_backup_task()))
    
    # Init DB check every day
    schedule.every().day.at("00:01").do(_init_db)
    
    import threading
    t = threading.Thread(target=run_scheduler_loop, daemon=True)
    t.start()
