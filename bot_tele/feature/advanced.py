import platform, socket, os, json, shutil
from datetime import datetime
from config import Config

MEMO_FILE = os.path.join(Config.BASE_DIR, "admin_memos.json")

def get_server_deep_info():
    """Mengambil info mendalam tentang server"""
    uname = platform.uname()
    return f"""
<b>🔍 DEEP SERVER INSPECTION</b>
━━━━━━━━━━━━━━━━━━━━
<b>OS:</b> {uname.system} {uname.release}
<b>Version:</b> {uname.version}
<b>Machine:</b> {uname.machine}
<b>Processor:</b> {uname.processor}
<b>Hostname:</b> {socket.gethostname()}
<b>Python:</b> {platform.python_version()}
<b>PID:</b> {os.getpid()}
━━━━━━━━━━━━━━━━━━━━
"""

def security_audit():
    """Simulasi audit keamanan sederhana"""
    # Cek permission file config
    try:
        conf_perm = oct(os.stat("config.py").st_mode)[-3:]
        risk = "LOW" if conf_perm == "644" else "HIGH (Check Permissions)"
    except:
        conf_perm = "Unknown"
        risk = "UNKNOWN"
        
    return f"""
<b>🛡️ SECURITY AUDIT REPORT</b>
━━━━━━━━━━━━━━━━━━━━
<b>Config Perm:</b> {conf_perm} ({risk})
<b>Root User:</b> {'YES ⚠️' if os.geteuid() == 0 else 'NO ✅'}
<b>Debug Mode:</b> False
<b>Tunneling:</b> Active
━━━━━━━━━━━━━━━━━━━━
"""

# --- MEMO SYSTEM ---
def get_memos():
    if not os.path.exists(MEMO_FILE): return []
    try:
        with open(MEMO_FILE, 'r') as f: return json.load(f)
    except: return []

def add_memo(text):
    memos = get_memos()
    memos.append({"text": text, "date": datetime.now().strftime("%d/%m %H:%M")})
    with open(MEMO_FILE, 'w') as f: json.dump(memos, f)

def clear_memos():
    if os.path.exists(MEMO_FILE): os.remove(MEMO_FILE)
