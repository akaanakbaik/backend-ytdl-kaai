import json
import os
import time
from datetime import datetime
from config import Config

DB_FILE = os.path.join(Config.BASE_DIR, "traffic_stats.json")

def _init_db():
    if not os.path.exists(DB_FILE):
        data = {
            "total_requests": 0,
            "today_requests": 0,
            "success_count": 0,
            "fail_count": 0,
            "web_views": 0,
            "last_reset": datetime.now().strftime("%Y-%m-%d")
        }
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

def _get_db():
    _init_db()
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    
    # Check Auto Reset Daily
    today = datetime.now().strftime("%Y-%m-%d")
    if data.get("last_reset") != today:
        data["last_reset"] = today
        data["today_requests"] = 0
        _save_db(data)
    
    return data

def _save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def record_traffic(status="success"):
    try:
        data = _get_db()
        data["total_requests"] += 1
        data["today_requests"] += 1
        
        if status == "success":
            data["success_count"] += 1
        elif status == "fail":
            data["fail_count"] += 1
        elif status == "view":
            data["web_views"] += 1
            # Adjust request counts for views if not desired
            data["total_requests"] -= 1
            data["today_requests"] -= 1
            
        _save_db(data)
    except Exception as e:
        print(f"DB Error: {e}")

def get_traffic_stats():
    data = _get_db()
    msg = f"""
<b>📊 TRAFFIC STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━
<b>📅 HARI INI:</b> {data['today_requests']} Requests
<b>♾ TOTAL (ALL TIME):</b> {data['total_requests']} Requests
<b>✅ SUKSES:</b> {data['success_count']}
<b>❌ GAGAL:</b> {data['fail_count']}
<b>👀 WEB VIEWS:</b> {data['web_views']}
━━━━━━━━━━━━━━━━━━━━
<i>Last Reset: {data['last_reset']}</i>
"""
    return msg
