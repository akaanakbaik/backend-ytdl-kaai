import requests
import logging
import time
import random
import re
import json
import os
import threading
import concurrent.futures
from typing import Set, List, Optional
from config import Config

# Setup Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("proxy_manager")

PROXY_SOURCES = [
    "https://api.nekolabs.web.id/tls/free-proxy",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=elite"
]

# --- FILE OPERATIONS ---
def _load_json_set(filename: str) -> Set[str]:
    if not os.path.exists(filename): return set()
    try:
        with open(filename, "r") as f: return set(json.load(f))
    except: return set()

def _save_json_set(filename: str, data: Set[str]):
    try:
        with open(filename, "w") as f: json.dump(list(data), f, indent=2)
    except: pass

def _load_score() -> dict:
    if not os.path.exists(Config.SCORE_FILE): return {}
    try:
        with open(Config.SCORE_FILE, "r") as f: return json.load(f)
    except: return {}

def _save_score(score: dict):
    try:
        with open(Config.SCORE_FILE, "w") as f: json.dump(score, f, indent=2)
    except: pass

# --- CORE LOGIC ---
def ban_proxy(proxy: str):
    if not proxy: return
    try:
        banned = _load_json_set(Config.BANNED_FILE)
        active = _load_json_set(Config.PROXY_FILE)
        score = _load_score()
        
        banned.add(proxy)
        active.discard(proxy)
        score.pop(proxy, None)
        
        _save_json_set(Config.BANNED_FILE, banned)
        _save_json_set(Config.PROXY_FILE, active)
        _save_score(score)
        log.warning(f"🚫 BANNED: {proxy}")
    except: pass

def _validate_proxy(proxy: str) -> Optional[str]:
    try:
        resp = requests.get("https://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=5)
        if resp.status_code == 200: return proxy
    except: pass
    return None

def fetch_and_update():
    """Mengambil proxy baru dari API"""
    log.info("🔄 Updating Proxy List...")
    banned = _load_json_set(Config.BANNED_FILE)
    raw = set()
    
    for url in PROXY_SOURCES:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200: continue
            
            if "nekolabs" in url:
                data = r.json().get("result", [])
                for p in data:
                    if p.get("https") == "yes": raw.add(f"http://{p['ip']}:{p['port']}")
            else:
                for line in r.text.splitlines():
                    if re.match(r"^(\d{1,3}\.){3}\d{1,3}:\d+$", line.strip()):
                        raw.add(f"http://{line.strip()}")
        except: continue
        
    candidates = list(raw - banned)
    if not candidates:
        log.info("⚠️ No new candidates found.")
        return

    log.info(f"⚡ Validating {len(candidates)} candidates...")
    valid = set()
    
    # Validation
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_validate_proxy, p) for p in candidates]
        for f in concurrent.futures.as_completed(futures):
            if f.result(): valid.add(f.result())
            
    if valid:
        current_active = _load_json_set(Config.PROXY_FILE)
        current_active.update(valid)
        _save_json_set(Config.PROXY_FILE, current_active)
        
        score = _load_score()
        for p in valid:
            if p not in score: score[p] = 1.0
        _save_score(score)
        log.info(f"✅ Update Complete: {len(current_active)} proxies total")
    else:
        log.warning("⚠️ No valid proxies found in this update.")

# --- BATCH RETRIEVAL ---
def get_batch_proxies(count=22) -> List[str]:
    proxies = list(_load_json_set(Config.PROXY_FILE))
    if len(proxies) < 2: return [] 
    
    try:
        random.shuffle(proxies)
        return proxies[:count]
    except: return proxies[:count]

# --- SCORING SYSTEM (INI YANG HILANG TADI) ---
def report_proxy_status(proxy: str, success: bool):
    """Algoritma Scoring & Auto-Ban"""
    try:
        score = _load_score()
        current = score.get(proxy, 1.0)
        
        if success:
            new_score = min(current + 0.5, 10.0) # Max 10
        else:
            new_score = current * 0.5 # Hukuman eksponensial
        
        score[proxy] = new_score
        _save_score(score)
        
        if new_score < 0.2:
            ban_proxy(proxy)
    except: pass

# --- SCHEDULER ---
def start_scheduler():
    import schedule
    
    # Schedule job
    schedule.every(Config.PROXY_UPDATE_INTERVAL).seconds.do(fetch_and_update)
    
    def loop():
        # Cek awal di dalam thread agar tidak blocking main process
        if not os.path.exists(Config.PROXY_FILE) or os.path.getsize(Config.PROXY_FILE) < 5:
            log.info("⚡ Initial Proxy Fetch (Background)...")
            fetch_and_update()
            
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    log.info("⏰ Proxy Scheduler Active (Background)")
