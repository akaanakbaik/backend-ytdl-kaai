import os, uvicorn, asyncio, time, mimetypes, json, logging
from urllib.parse import quote
from fastapi import FastAPI, Body, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from config import Config, STATUS_OK
from logger import log, save_detailed_error
from engine import run_dual_engine_buffer
import tunnel
from proxy_manager import start_scheduler as start_proxy_scheduler

# --- TELEGRAM MODULES ---
from bot_tele.loader import bot, dp
from bot_tele.handlers import router as bot_router
from bot_tele.scheduler import start_bot_scheduler
from bot_tele.system.db import record_traffic

# HAPUS BARIS INI DARI SINI:
# dp.include_router(bot_router) <--- INI PENYEBAB ERRORNYA

# INIT FOLDERS
for path in [Config.TMP_DIR, Config.RAW_DIR, Config.CACHE_DIR, Config.ERROR_DIR, Config.LOG_DIR, Config.BACKUP_DIR]: 
    os.makedirs(path, exist_ok=True)

TMP_DIR = Config.TMP_DIR
EXPIRE_SECONDS = 60 * 60 * 3 

app = FastAPI(title="KAAI YTDL Ultimate + Bot", version="6.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self): self.active_connections = []
    async def connect(self, websocket: WebSocket): await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try: await connection.send_json(message)
            except: pass

ws_manager = ConnectionManager()

def get_client_ip(request: Request): return request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

def process_database_ip(ip_address):
    try:
        if not os.path.exists(Config.DATABASE_FILE): 
            with open(Config.DATABASE_FILE, "w") as f: json.dump({}, f)
        
        db = {}
        try:
            with open(Config.DATABASE_FILE, "r") as f: 
                content = f.read().strip()
                if content: db = json.loads(content)
        except: db = {}
        
        current_time = time.time()
        if ip_address not in db: db[ip_address] = {"min_ts": current_time, "day_ts": current_time, "req_min": 0, "req_day": 0, "req_total": 0}
        
        user = db[ip_address]
        if current_time - user.get("min_ts", 0) > 60: user["min_ts"] = current_time; user["req_min"] = 0
        if current_time - user.get("day_ts", 0) > 86400: user["day_ts"] = current_time; user["req_day"] = 0
        
        if user["req_min"] >= Config.RATE_LIMIT_MIN: return False, f"Rate limit ({Config.RATE_LIMIT_MIN}/min)"
        if user["req_day"] >= Config.RATE_LIMIT_DAY: return False, f"Rate limit ({Config.RATE_LIMIT_DAY}/day)"
        
        user["req_min"] += 1; user["req_day"] += 1; user["req_total"] = user.get("req_total", 0) + 1
        
        with open(Config.DATABASE_FILE, "w") as f: json.dump(db, f, indent=None)
        return True, user
    except: return True, {}

# --- TELEGRAM LOGGER (WITH IP MASKING) ---
async def send_tele_log(type_log, data):
    if not Config.TELE_LOG_ID: return
    try:
        # MASKING IP (Sensor 4 digit terakhir)
        raw_ip = data.get('ip', '0.0.0.0')
        parts = raw_ip.split('.')
        if len(parts) == 4:
            safe_ip = f"{parts[0]}.{parts[1]}.xxx.xxx"
        else:
            safe_ip = "xxx.xxx.xxx.xxx"

        msg = f"""
<b>🔔 LOG: {type_log}</b>
━━━━━━━━━━━━━━━━
<b>👤 User IP:</b> <code>{safe_ip}</code>
<b>🔗 Link:</b> <a href="{data.get('url')}">YouTube Video</a>
<b>📂 Type:</b> {data.get('type').upper()}
<b>⚡ Speed:</b> {data.get('time')}s
━━━━━━━━━━━━━━━━
"""
        await bot.send_message(Config.TELE_LOG_ID, msg, disable_web_page_preview=True)
    except: pass

# --- BACKGROUND TASKS ---
async def background_tasks():
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
    # INCLUDE ROUTER DISINI SAJA AGAR AMAN
    if not dp.sub_routers:
        dp.include_router(bot_router)
        
    asyncio.create_task(background_tasks())
    asyncio.create_task(asyncio.to_thread(tunnel.run_tunnel))
    
    try: start_proxy_scheduler()
    except: pass
    try: start_bot_scheduler()
    except: pass
    
    # Start Bot Polling
    asyncio.create_task(dp.start_polling(bot))
    log.info("✅ SYSTEM ONLINE (WEB + BOT + MONITOR)")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = save_detailed_error({"url": str(request.url), "method": request.method}, exc)
    return JSONResponse(status_code=500, content={"status": False, "msg": "Internal Error", "error_id": error_id})

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except: ws_manager.disconnect(websocket)

@app.get("/")
async def root(): 
    record_traffic("view")
    return {"status": "online", "system": "v6.0"}

@app.post("/api/ytdl/info")
async def ytdl_info(request: Request, url: str = Body(..., embed=True), type: str = Body("video", embed=True)):
    client_ip = get_client_ip(request)
    allowed, user_stat = process_database_ip(client_ip)
    
    if not allowed: 
        record_traffic("fail")
        return JSONResponse(status_code=429, content={"status": False, "msg": user_stat})
    
    start_time = time.time()
    await ws_manager.broadcast({"status": "processing", "msg": f"Req from {client_ip}..."})
    
    asyncio.create_task(send_tele_log("REQUEST", {"ip": client_ip, "url": url, "type": type, "status": "PROCESSING", "engine": "-", "time": "0"}))

    data = await run_dual_engine_buffer(url, type, ws_manager)
    duration = time.time() - start_time
    
    if data["status"] != STATUS_OK:
        record_traffic("fail")
        asyncio.create_task(send_tele_log("FAIL", {"ip": client_ip, "url": url, "type": type, "time": f"{duration:.1f}"}))
        await ws_manager.broadcast({"status": "error", "msg": "Failed"})
        return JSONResponse(status_code=503, content={"status": False, "msg": "Failed", "details": data.get("error_detail", [])})
    
    record_traffic("success")
    asyncio.create_task(send_tele_log("SUCCESS", {"ip": client_ip, "url": url, "type": type, "time": f"{duration:.1f}"}))
    
    filename = data["filename"]
    safe_name = quote(filename)
    await ws_manager.broadcast({"status": "complete", "msg": "Done"})
    
    return {
        "status": True,
        "metadata": {
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"),
            "author": data.get("author"),
            "engine": data.get("engine"),
            "filename": filename,
            "preview_url": f"https://{Config.HOSTNAME}/cdn/ytdl/{safe_name}",
            "download_url": f"https://{Config.HOSTNAME}/cdn/ytdl/{safe_name}?download=1",
            "stats": user_stat
        }
    }

def file_iterator(path: str, start: int, end: int, chunk_size=1024*512):
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
    if request.query_params.get("download") == "1": headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else: headers["Content-Disposition"] = f'inline; filename="{filename}"'
    
    if range_header:
        try:
            start_str, end_str = range_header.replace("bytes=", "").split("-")
            start = int(start_str)
            end = int(end_str) if end_str else size - 1
            end = min(end, size - 1)
            headers.update({"Content-Range": f"bytes {start}-{end}/{size}", "Content-Length": str(end - start + 1)})
            return StreamingResponse(file_iterator(path, start, end), status_code=206, headers=headers, media_type=ctype)
        except: pass
        
    headers["Content-Length"] = str(size)
    return StreamingResponse(file_iterator(path, 0, size - 1), headers=headers, media_type=ctype)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, workers=1, log_level="info")
