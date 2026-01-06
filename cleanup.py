import os
import time
import asyncio
from config import Config
from logger import log

async def auto_cleanup_loop():
    log.info("Auto Cleanup Service Started")
    while True:
        try:
            now = time.time()
            count = 0
            if os.path.exists(Config.TMP_DIR):
                for filename in os.listdir(Config.TMP_DIR):
                    filepath = os.path.join(Config.TMP_DIR, filename)
                    if os.path.isfile(filepath):
                        file_age = now - os.path.getmtime(filepath)
                        if file_age > Config.CLEANUP_AGE:
                            os.remove(filepath)
                            count += 1
            if count > 0:
                log.info(f"Cleaned {count} old files from buffer.")
        except Exception as e:
            log.error(f"Cleanup Error: {e}")
        await asyncio.sleep(Config.CLEANUP_INTERVAL)