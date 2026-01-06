import asyncio, os, re
from config import Config, STATUS_OK, STATUS_FAIL
from logger import log
from user_agent import get_batch_user_agents
from proxy_manager import get_batch_proxies
from .progress1.audio import run_audio_engine
from .progress1.video import run_video_engine
from .progress2 import run_engine_b

def standardize_url(url: str) -> str:
    try:
        video_id = None
        if "youtu.be" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com/watch" in url:
            query = url.split("?")[1]
            for param in query.split("&"):
                if param.startswith("v="): video_id = param.split("=")[1]; break
        if video_id: return f"https://www.youtube.com/watch?v={video_id}"
        return url
    except: return url

async def run_dual_engine_buffer(url: str, type_req: str, ws_manager=None):
    clean_url = standardize_url(url)
    log.info(f"ROUTER: {url} -> {clean_url} [{type_req}]")
    uas = get_batch_user_agents(Config.REQ_UA_COUNT)
    proxies = get_batch_proxies(Config.REQ_PROXY_COUNT)
    ua_list = uas[:6]; proxy_list = proxies[:11]
    error_detail = []

    log.info("PHASE 1: ENGINE PRIMARY (Progress 1)")
    if ws_manager: await ws_manager.broadcast({"status": "progress", "msg": "Engine 1 Started..."})
    
    try:
        if type_req == "audio":
            task = run_audio_engine(clean_url, Config.TMP_DIR, proxy_list, ua_list)
        else:
            task = run_video_engine(clean_url, Config.TMP_DIR, proxy_list, ua_list)
            
        res_a = await asyncio.wait_for(task, timeout=60)
        
        if res_a.get("status") == STATUS_OK:
            log.info("ENGINE 1 SUCCESS")
            if ws_manager: await ws_manager.broadcast({"status": "progress", "msg": "Engine 1 Success, Finalizing..."})
            return _finalize_result(res_a)
        error_detail.append(f"Engine1: {res_a.get('reason')}")
    except asyncio.TimeoutError:
        log.warning("ENGINE 1 TIMEOUT (>60s) -> Switch to Engine 2")
        error_detail.append("Engine1: Timeout")
    except Exception as e:
        log.error(f"ENGINE 1 ERROR: {e}")
        error_detail.append(f"Engine1: {str(e)}")

    log.info("PHASE 2: ENGINE FALLBACK (Progress 2)")
    if ws_manager: await ws_manager.broadcast({"status": "progress", "msg": "Switching to Fallback Engine..."})
    res_b = await run_engine_b(clean_url, Config.TMP_DIR, type_req, proxies[11:], uas[6:])
    if res_b.get("status") == STATUS_OK:
        log.info("ENGINE 2 SUCCESS")
        return _finalize_result(res_b)
    error_detail.append(f"Engine2: {res_b.get('reason')}")
    
    return {"status": STATUS_FAIL, "engine": None, "filename": None, "error_detail": error_detail}

def _finalize_result(data: dict):
    filename = data.get("filename")
    if not filename: return {"status": STATUS_FAIL, "engine": None, "filename": None, "error_detail": ["filename missing"]}
    file_path = os.path.join(Config.TMP_DIR, filename)
    if not os.path.exists(file_path): return {"status": STATUS_FAIL, "engine": None, "filename": None, "error_detail": [f"file lost: {filename}"]}
    data["filename"] = filename
    return data
