import logging, os, json, uuid, traceback, colorlog
from datetime import datetime
from config import Config

os.makedirs(Config.LOG_DIR, exist_ok=True); os.makedirs(Config.ERROR_DIR, exist_ok=True)

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s | %(levelname)s | %(message)s', log_colors={'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'bold_red'}))

log = logging.getLogger("KAAI_CORE_V2")
log.addHandler(handler)
log.setLevel(logging.INFO)

file_handler = logging.FileHandler(os.path.join(Config.LOG_DIR, "runtime.log"))
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
log.addHandler(file_handler)

def save_detailed_error(request_info: dict, exc: Exception) -> str:
    try:
        now = datetime.now()
        error_id = str(uuid.uuid4())[:8]
        filename = f"{now.strftime('%H.%M-%d-%m-%Y')}_{error_id}.json"
        filepath = os.path.join(Config.ERROR_DIR, filename)
        
        log_data = {
            "error_id": error_id,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "system_mode": "Mode 2 (High Performance)",
            "request_context": request_info,
            "error_summary": {"type": type(exc).__name__, "message": str(exc)},
            "full_traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        }
        
        with open(filepath, "w", encoding="utf-8") as f: json.dump(log_data, f, indent=4, ensure_ascii=False)
        log.critical(f"🔥 SNAPSHOT ERROR SAVED: {filename} (ID: {error_id})")
        return error_id
    except Exception as e:
        log.error(f"⚠️ CRITICAL: Failed to save error log snapshot: {e}")
        return "LOG_FAILED"
