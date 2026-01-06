import yt_dlp, asyncio, os, uuid, subprocess, shutil, random
from config import Config, STATUS_OK, STATUS_FAIL
from logger import log

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
]

async def run_video_engine(url: str, output_path: str):
    loop = asyncio.get_running_loop()
    request_id = str(uuid.uuid4())[:8]
    raw_dir = os.path.join(Config.RAW_DIR, request_id)
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. SETUP COOKIES
    cookie_file = None
    for cf in Config.COOKIES_FILES:
        p = os.path.join(Config.BASE_DIR, cf)
        if os.path.exists(p):
            cookie_file = p; break

    # 2. CONFIG TURBO YTDLP
    ydl_opts = {
        "format": "bestvideo+bestaudio/best", 
        "outtmpl": os.path.join(raw_dir, "%(id)s.%(ext)s"),
        "quiet": True, 
        "no_warnings": True, 
        "ignoreerrors": True,
        "nocheckcertificate": True,
        "user_agent": random.choice(UAS),
        
        # --- TURBO NETWORK SETTINGS ---
        "socket_timeout": 15,
        "retries": 10,
        # INI KUNCINYA: Download 8 bagian sekaligus!
        "concurrent_fragment_downloads": 8, 
        "buffersize": 1024 * 1024,
        "http_chunk_size": 10485760,
    }
    
    if cookie_file: ydl_opts["cookiefile"] = cookie_file

    try:
        # 3. DOWNLOAD
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: return ydl.extract_info(url, download=True)
        info = await loop.run_in_executor(None, _download)

        raw_files = os.listdir(raw_dir)
        if not raw_files: raise Exception("Download failed (No file)")
        raw_path = os.path.join(raw_dir, raw_files[0])

        title = info.get("title", f"video-{request_id}")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:50]
        final_path = os.path.join(Config.TMP_DIR, f"{safe_title}.mp4")

        # 4. BINARIES
        ffmpeg_bin = os.path.join(Config.BASE_DIR, "ffmpeg-master-latest-linux64-gpl", "bin", "ffmpeg")
        ffprobe_bin = os.path.join(Config.BASE_DIR, "ffmpeg-master-latest-linux64-gpl", "bin", "ffprobe")
        if not os.path.exists(ffmpeg_bin): ffmpeg_bin = "ffmpeg"
        if not os.path.exists(ffprobe_bin): ffprobe_bin = "ffprobe"

        # 5. SMART CHECK (Anti-Crash)
        video_codec = ["-c:v", "libx264", "-preset", "superfast", "-crf", "23"] # Default Safe
        
        try:
            # Cek codec pakai ffprobe
            probe_cmd = [ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", raw_path]
            codec = subprocess.check_output(probe_cmd, stderr=subprocess.DEVNULL).decode().strip()
            
            # Jika H264, JANGAN re-encode. Cukup COPY stream (Sangat Cepat & Hemat CPU)
            if codec == "h264": 
                video_codec = ["-c:v", "copy"]
        except: 
            pass

        # 6. FFMPEG PROCESSING
        cmd = [
            ffmpeg_bin, "-y", 
            "-i", raw_path,
            *video_codec, 
            "-c:a", "aac", 
            "-b:a", "128k",
            "-movflags", "+faststart", 
            "-threads", "0", # Full CPU Cores
            final_path
        ]

        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.wait()

        if not os.path.exists(final_path): raise Exception("FFmpeg conversion failed")
        shutil.rmtree(raw_dir, ignore_errors=True)

        return {
            "status": STATUS_OK, "engine": "Engine A (Video/Turbo)", "filename": os.path.basename(final_path),
            "title": title, "thumbnail": info.get("thumbnail"), "duration": info.get("duration_string"),
            "author": info.get("uploader"), "request_id": request_id
        }
    except Exception as e:
        shutil.rmtree(raw_dir, ignore_errors=True)
        return {"status": STATUS_FAIL, "reason": str(e)}
