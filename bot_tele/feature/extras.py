import speedtest, asyncio, os, shutil, requests, subprocess, psutil, random, string, secrets, qrcode, time
from config import Config

async def run_speedtest_task():
    """Menjalankan Speedtest di Thread terpisah"""
    loop = asyncio.get_running_loop()
    def _test():
        st = speedtest.Speedtest()
        st.get_best_server()
        dl = st.download() / 1_000_000
        ul = st.upload() / 1_000_000
        return dl, ul, st.results.ping
    return await loop.run_in_executor(None, _test)

def get_ip_info():
    """Mengambil info IP Server"""
    try:
        r = requests.get("http://ip-api.com/json/")
        data = r.json()
        return f"""
<b>📡 SERVER NETWORK INFO</b>
━━━━━━━━━━━━━━━━
<b>IP:</b> <code>{data.get('query')}</code>
<b>ISP:</b> {data.get('isp')}
<b>Org:</b> {data.get('org')}
<b>Country:</b> {data.get('country')} ({data.get('countryCode')})
<b>Region:</b> {data.get('regionName')}
<b>Timezone:</b> {data.get('timezone')}
━━━━━━━━━━━━━━━━
"""
    except: return "❌ Failed to fetch IP info."

def force_clean_system():
    """Membersihkan file sampah di folder TMP/Cache/Log"""
    deleted = 0
    for folder in [Config.TMP_DIR, Config.CACHE_DIR, Config.ERROR_DIR, Config.LOG_DIR]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                try:
                    if os.path.isfile(fp): os.remove(fp)
                    else: shutil.rmtree(fp)
                    deleted += 1
                except: pass
            os.makedirs(folder, exist_ok=True)
    return deleted

async def exec_shell(cmd):
    """Menjalankan perintah terminal Linux"""
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    res = stdout.decode() if stdout else stderr.decode()
    return res[:3500] if res else "No Output."

# --- NEW FEATURES (YANG HILANG SEBELUMNYA) ---

def get_cpu_temp():
    """Membaca suhu CPU"""
    try:
        if not hasattr(psutil, "sensors_temperatures"): return "⚠️ OS Not Supported"
        temps = psutil.sensors_temperatures()
        if not temps: return "❄️ No Sensors Found"
        msg = "<b>🌡️ THERMAL STATUS</b>\n"
        for name, entries in temps.items():
            for entry in entries:
                msg += f"• {name}: <b>{entry.current}°C</b>\n"
        return msg
    except: return "⚠️ Reading Failed"

def list_temp_files():
    """List file di folder TMP"""
    try:
        files = os.listdir(Config.TMP_DIR)
        if not files: return "📂 <b>TMP is Empty</b>"
        
        files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(Config.TMP_DIR, x)), reverse=True)[:10]
        
        msg = f"<b>📂 FILE MANAGER (Top 10)</b>\nCount: {len(files)}\n━━━━━━━━━━━━\n"
        for f in files:
            size = os.path.getsize(os.path.join(Config.TMP_DIR, f)) / 1024 / 1024
            msg += f"📄 <code>{f[:20]}...</code> ({size:.1f}MB)\n"
        return msg
    except Exception as e: return f"Error: {e}"

def whois_lookup(domain):
    """Cek info WhoIs Domain/IP"""
    try:
        r = requests.get(f"http://ip-api.com/json/{domain}")
        d = r.json()
        if d['status'] == 'fail': return "❌ Invalid Host"
        return f"""
<b>🔎 WHOIS DATA</b>
━━━━━━━━━━━━
<b>Target:</b> {domain}
<b>IP:</b> {d.get('query')}
<b>ISP:</b> {d.get('isp')}
<b>Loc:</b> {d.get('city')}, {d.get('country')}
━━━━━━━━━━━━
"""
    except: return "❌ Lookup Error"

def random_quote():
    """Quote acak untuk hiburan"""
    quotes = [
        "Code is like humor. When you have to explain it, it’s bad.",
        "Fix the cause, not the symptom.",
        "Simplicity is the soul of efficiency.",
        "Make it work, make it right, make it fast.",
        "Talk is cheap. Show me the code."
    ]
    return f"💬 <i>{random.choice(quotes)}</i>"

def make_qr(text):
    """Membuat QR Code"""
    os.makedirs(Config.TMP_DIR, exist_ok=True)
    qr_path = os.path.join(Config.TMP_DIR, f"qr_{int(time.time())}.png")
    img = qrcode.make(text)
    img.save(qr_path)
    return qr_path

def gen_password(length=12):
    """Generate Password Aman"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = ''.join(secrets.choice(chars) for _ in range(length))
    return pwd

def get_top_processes():
    """Melihat proses terberat di server"""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try: procs.append(p.info)
        except: pass
    
    procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
    
    msg = "<b>🔥 TOP 5 CPU PROCESSES</b>\n━━━━━━━━━━━━━━━━\n"
    for p in procs[:5]:
        msg += f"• <b>{p['name']}</b> ({p['pid']}): {p['cpu_percent']}%\n"
    return msg
