from fastapi import APIRouter, Body, Request, HTTPException
from fastapi.responses import JSONResponse
from urllib.parse import quote
import time
import os
import asyncio

from config import Config, STATUS_OK
from engine import run_dual_engine_buffer
from logger import log

router = APIRouter()

async def handle_ytdl_process(request: Request, url: str, type_req: str):
    # 1. Access Shared Resources
    ws_manager = request.app.state.ws_manager
    process_db_ip = request.app.state.process_db_ip
    send_tele_log = request.app.state.send_tele_log
    
    # Ambil Semaphore dari Main
    semaphore = request.app.state.semaphore
    
    # 2. Rate Limit
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    allowed, user_stat = process_db_ip(client_ip)
    
    if not allowed:
        return JSONResponse(status_code=429, content={"status": False, "msg": user_stat})

    # 3. Log Start (Non-blocking)
    start_time = time.time()
    await ws_manager.broadcast({"status": "processing", "msg": f"Req from {client_ip}..."})
    
    if send_tele_log:
        asyncio.create_task(send_tele_log("REQUEST", {
            "ip": client_ip, "url": url, "type": type_req, 
            "status": "PROCESSING", "engine": "-", "time": "0"
        }))

    # 4. EXECUTE ENGINE (WITH CONCURRENCY CONTROL)
    # Ini kuncinya: Membatasi jumlah job berat, tapi membiarkan job lain antri di async loop
    async with semaphore:
        data = await run_dual_engine_buffer(url, type_req, ws_manager)
        
    duration = time.time() - start_time

    # 5. Handle Result
    if data["status"] != STATUS_OK:
        if send_tele_log:
            asyncio.create_task(send_tele_log("FAIL", {
                "ip": client_ip, "url": url, "type": type_req, 
                "time": f"{duration:.1f}"
            }))
        
        await ws_manager.broadcast({"status": "error", "msg": "Failed"})
        return JSONResponse(
            status_code=503, 
            content={
                "status": False, 
                "msg": "Gagal memproses media. Coba lagi nanti.", 
                "details": data.get("error_detail", [])
            }
        )

    # 6. Success Response
    if send_tele_log:
        asyncio.create_task(send_tele_log("SUCCESS", {
            "ip": client_ip, "url": url, "type": type_req, 
            "time": f"{duration:.1f}"
        }))
    
    filename = data["filename"]
    safe_name = quote(filename)
    await ws_manager.broadcast({"status": "complete", "msg": "Done"})

    return {
        "status": True,
        "author": "aka",
        "email_author": "akaanakbaik17@proton.me",
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

# --- ENDPOINTS ---

@router.api_route("/mp3", methods=["GET", "POST"])
async def get_mp3(request: Request, url: str = Body(None), type: str = Body("audio")):
    if request.method == "GET": url = request.query_params.get("url")
    if not url: return JSONResponse(status_code=400, content={"status": False, "msg": "URL is required"})
    return await handle_ytdl_process(request, url, "audio")

@router.api_route("/mp4", methods=["GET", "POST"])
async def get_mp4(request: Request, url: str = Body(None), type: str = Body("video")):
    if request.method == "GET": url = request.query_params.get("url")
    if not url: return JSONResponse(status_code=400, content={"status": False, "msg": "URL is required"})
    return await handle_ytdl_process(request, url, "video")

@router.post("/process")
async def process_legacy(request: Request, url: str = Body(..., embed=True), type: str = Body("video", embed=True)):
    real_type = "audio" if type == "mp3" else "video"
    return await handle_ytdl_process(request, url, real_type)
