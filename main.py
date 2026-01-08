import os, uvicorn, asyncio, time, mimetypes, json, logging
from urllib.parse import quote
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from config import Config, STATUS_OK
from logger import log, save_detailed_error
import tunnel
from proxy_manager import start_scheduler as start_proxy_scheduler

# --- IMPORT ROUTERS ---
from routers import ytdl

# --- TELEGRAM MODULES ---
from bot_tele.loader import bot, dp
from bot_tele.handlers import router as bot_router
from bot_tele.scheduler import start_bot_scheduler
from bot_tele.system.db import record_traffic

# INIT FOLDERS
for path in [Config.TMP_DIR, Config.RAW_DIR, Config.CACHE_DIR, Config.ERROR_DIR, Config.LOG_DIR, Config.BACKUP_DIR]: 
    os.makedirs(path, exist_ok=True)

TMP_DIR = Config.TMP_DIR
EXPIRE_SECONDS = 60 * 60 * 3 

# SETTING CONCURRENCY
# Izinkan 10 proses download BERAT berjalan bersamaan. 
# Sisanya antri di RAM (cepat), bukan antri di Network.
MAX_CONCURRENT_JOBS = 10 

app = FastAPI(title="KAAI REST API System V8 (Multi-Thread)", version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OPTIMIZED CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self): 
        self.active_connections = set() # Ganti list ke set agar remove lebih cepat O(1)

    async def connect(self, websocket: WebSocket): 
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket): 
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Fire-and-forget: Kirim pesan tanpa nunggu balasan client (biar server gak bengong)
        if not self.active_connections: return
        
        # Buat task list untuk broadcast paralel
        tasks = [self._send_safe(ws, message) for ws in self.active_connections]
        await asyncio.gather(*tasks)

    async def _send_safe(self, ws: WebSocket, message: dict):
        try: await ws.send_json(message)
        except: self.disconnect(ws)

ws_manager = ConnectionManager()

# --- DATABASE & LOGGING HELPERS ---
def process_database_ip(ip_address):
    try:
        if not os.path.exists(Config.DATABASE_FILE): 
            with open(Config.DATABASE_FILE, "w") as f: json.dump({}, f)
        
        # Baca DB dengan mode aman
        try:
            with open(Config.DATABASE_FILE, "r") as f: content = f.read().strip(); db = json.loads(content) if content else {}
        except: db = {}
        
        current_time = time.time()
        if ip_address not in db: db[ip_address] = {"min_ts": current_time, "day_ts": current_time, "req_min": 0, "req_day": 0, "req_total": 0}
        
        user = db[ip_address]
        if current_time - user.get("min_ts", 0) > 60: user["min_ts"] = current_time; user["req_min"] = 0
        if current_time - user.get("day_ts", 0) > 86400: user["day_ts"] = current_time; user["req_day"] = 0
        
        if user["req_min"] >= Config.RATE_LIMIT_MIN: return False, f"Rate limit ({Config.RATE_LIMIT_MIN}/min)"
        if user["req_day"] >= Config.RATE_LIMIT_DAY: return False, f"Rate limit ({Config.RATE_LIMIT_DAY}/day)"
        
        user["req_min"] += 1; user["req_day"] += 1; user["req_total"] = user.get("req_total", 0) + 1
        
        # Tulis balik (blocking I/O tapi cepat untuk file kecil)
        with open(Config.DATABASE_FILE, "w") as f: json.dump(db, f, indent=None)
        return True, user
    except: return True, {}

async def send_tele_log(type_log, data):
    if not Config.TELE_LOG_ID: return
    try:
        raw_ip = data.get('ip', '0.0.0.0')
        parts = raw_ip.split('.')
        safe_ip = f"{parts[0]}.{parts[1]}.xxx.xxx" if len(parts) == 4 else "xxx.xxx.xxx.xxx"
        msg = f"<b>🔔 {type_log}</b>\nIP: {safe_ip}\nLink: {data.get('url')}\nMode: {data.get('type')}\nSpeed: {data.get('time')}s"
        await bot.send_message(Config.TELE_LOG_ID, msg, disable_web_page_preview=True)
    except: pass

# --- MOUNT STATE & RESOURCES ---
# Inject Global State untuk dipakai di Router
app.state.ws_manager = ws_manager
app.state.process_db_ip = process_database_ip
app.state.send_tele_log = send_tele_log
# SEMAPHORE: Pembatas jumlah proses berat sekaligus
app.state.semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# Router
app.include_router(ytdl.router, prefix="/api/v1/ytdl", tags=["Youtube DL"])

# --- BACKGROUND TASKS ---
async def background_cleanup():
    while True:
        try:
            now = time.time()
            for f in os.listdir(TMP_DIR):
                path = os.path.join(TMP_DIR, f)
                if not os.path.isfile(path): continue
                if now - os.path.getmtime(path) > EXPIRE_SECONDS: os.remove(path)
        except: pass
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    # Setup Telegram Router
    if not dp.sub_routers: dp.include_router(bot_router)
    
    # Jalankan Service di Background (Parallel)
    asyncio.create_task(background_cleanup())
    asyncio.create_task(asyncio.to_thread(tunnel.run_tunnel))
    
    try: start_proxy_scheduler()
    except: pass
    try: start_bot_scheduler()
    except: pass
    
    asyncio.create_task(dp.start_polling(bot))
    log.info(f"✅ SYSTEM ONLINE (Multi-Thread Mode: Max {MAX_CONCURRENT_JOBS} Jobs)")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = save_detailed_error({"url": str(request.url), "method": request.method}, exc)
    return JSONResponse(status_code=500, content={"status": False, "msg": "Internal Error", "error_id": error_id})

# --- CDN STREAMING ---
def file_iterator(path, start, end, chunk_size=1024*512):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk: break
            remaining -= len(chunk)
            yield chunk

@app.get("/cdn/ytdl/{filename}")
async def cdn_stream(filename: str, request: Request):
    if ".." in filename or filename.startswith("/"): raise HTTPException(400, "Invalid")
    path = os.path.join(TMP_DIR, filename)
    if not os.path.exists(path): raise HTTPException(404, "Not Found")
    
    size = os.path.getsize(path)
    range_header = request.headers.get("range")
    ctype, _ = mimetypes.guess_type(path)
    if not ctype: ctype = "application/octet-stream"
    headers = {"Accept-Ranges": "bytes", "Content-Type": ctype}
    
    if request.query_params.get("download") == "1":
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    if range_header:
        try:
            start, end = range_header.replace("bytes=", "").split("-")
            start = int(start)
            end = int(end) if end else size - 1
            headers.update({"Content-Range": f"bytes {start}-{end}/{size}", "Content-Length": str(end - start + 1)})
            return StreamingResponse(file_iterator(path, start, end), status_code=206, headers=headers, media_type=ctype)
        except: pass
    headers["Content-Length"] = str(size)
    return StreamingResponse(file_iterator(path, 0, size - 1), headers=headers, media_type=ctype)

@app.get("/")
async def root(): 
    record_traffic("view")
    return {"status": "online", "mode": "multi-process", "version": "v8.0"}

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except: ws_manager.disconnect(websocket)

if __name__ == "__main__":
    # WORKERS=1 Wajib untuk Bot Telegram, tapi loop='auto' akan pakai uvloop (cepat)
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, workers=1, log_level="info", loop="auto")
