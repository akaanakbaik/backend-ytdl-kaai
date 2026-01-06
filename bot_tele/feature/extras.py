import speedtest, asyncio, os, shutil, requests, subprocess
from config import Config

async def run_speedtest_task():
    loop = asyncio.get_running_loop()
    def _test():
        st = speedtest.Speedtest()
        st.get_best_server()
        dl = st.download() / 1_000_000
        ul = st.upload() / 1_000_000
        return dl, ul, st.results.ping
    return await loop.run_in_executor(None, _test)

def get_ip_info():
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
    deleted = 0
    # Clean Temp & Cache
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
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    res = stdout.decode() if stdout else stderr.decode()
    return res[:3500] if res else "No Output."
