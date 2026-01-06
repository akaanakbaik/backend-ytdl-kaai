import yt_dlp
import asyncio
import os
from config import Config
from logger import log
from proxy_manager import get_batch_proxies

async def download_to_local(url: str, type_req='video'):
    loop = asyncio.get_running_loop()
    ext = "mp4" if type_req == 'video' else "mp3"
    filename = Config.get_filename(ext)
    output_path = os.path.join(Config.TMP_DIR, filename)
    proxies = get_batch_proxies(1)
    proxy = proxies[0] if proxies else None

    ydl_opts = {
        'format': 'best[ext=mp4]/best' if type_req == 'video' else 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'proxy': proxy,
        'socket_timeout': 15,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }] if type_req == 'audio' else [],
        'concurrent_fragment_downloads': 5,
        'buffersize': 1024 * 1024,
    }

    def run_download():
        if os.path.exists(output_path):
            return
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            info = ydl.extract_info(url, download=False)
            return info

    try:
        log.info(f"BUFFERING: {url} -> {filename}")
        info = await loop.run_in_executor(None, run_download)
        final_filename = filename
        if type_req == 'audio':
            if not os.path.exists(output_path) and os.path.exists(output_path.replace('.mp4', '.mp3')):
                final_filename = filename.replace('.mp4', '.mp3')
            elif os.path.exists(output_path + ".mp3"):
                final_filename = filename + ".mp3"

        return {
            "status": True,
            "filename": final_filename,
            "title": info.get('title', 'Unknown'),
            "thumbnail": info.get('thumbnail'),
            "duration": info.get('duration_string'),
            "author": info.get('uploader'),
            "type": type_req
        }
    except Exception as e:
        log.error(f"Buffer Failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e