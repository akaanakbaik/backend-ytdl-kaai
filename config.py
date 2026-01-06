import os
from datetime import datetime
import uuid

class Config:
    # --- NETWORK ---
    PORT = 2000 
    HOSTNAME = "example.domain.com"
    TUNNEL_TOKEN = "eyxxxx"

    # --- PATHS (PTERODACTYL ROOT) ---
    BASE_DIR = os.getcwd()
    TMP_DIR = os.path.join(BASE_DIR, "tmp", "ytdl")
    RAW_DIR = os.path.join(BASE_DIR, "tmp", "ytdl_mentah")
    CACHE_DIR = os.path.join(BASE_DIR, "cache")
    ERROR_DIR = os.path.join(BASE_DIR, "log_error")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")

    # --- DATA FILES ---
    PROXY_FILE = os.path.join(BASE_DIR, "proxy.json")
    BANNED_FILE = os.path.join(BASE_DIR, "banned_proxies.json")
    SCORE_FILE = os.path.join(BASE_DIR, "proxy_score.json")
    UA_FILE = os.path.join(BASE_DIR, "user_agents.json")
    DATABASE_FILE = os.path.join(BASE_DIR, "database.json")
    COOKIES_FILES = ["cookies.txt", "www.youtube.com_cookies.txt", "m.youtube.com_cookies.txt"]

    # --- SETTINGS ---
    REQ_UA_COUNT = 12
    REQ_PROXY_COUNT = 22
    TIMEOUT_COORDINATOR = 150 
    TIMEOUT_ENGINE = 60
    PROXY_UPDATE_INTERVAL = 1800
    CLEANUP_AGE = 10800
    CLEANUP_INTERVAL = 600
    
    # --- RATE LIMIT ---
    RATE_LIMIT_MIN = 5
    RATE_LIMIT_DAY = 100

    # --- TELEGRAM CONFIG ---
    TELE_TOKEN = "tokenbottele" 
    TELE_ADMIN_ID = 0
    TELE_LOG_ID = -100

    @staticmethod
    def get_filename(ext="mp4"):
        now = datetime.now()
        unique = str(uuid.uuid4())[:6]
        return f"{now.strftime('%H.%M-%d-%m-%Y')}-{unique}.{ext}"

STATUS_OK = "ok"
STATUS_FAIL = "fail"
