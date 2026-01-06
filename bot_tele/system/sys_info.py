import psutil
import time
import platform
from datetime import datetime

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_server_status():
    # CPU
    cpu_usage = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq().current
    cpu_cores = psutil.cpu_count(logical=True)
    
    # RAM
    svmem = psutil.virtual_memory()
    ram_total = get_size(svmem.total)
    ram_used = get_size(svmem.used)
    ram_percent = svmem.percent
    
    # Disk
    partition = psutil.disk_usage("/")
    disk_total = get_size(partition.total)
    disk_used = get_size(partition.used)
    disk_percent = partition.percent
    
    # Network
    net_io = psutil.net_io_counters()
    net_sent = get_size(net_io.bytes_sent)
    net_recv = get_size(net_io.bytes_recv)
    
    # System
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    uptime = datetime.now() - bt
    uptime_str = str(uptime).split('.')[0]
    
    os_name = platform.system()
    os_release = platform.release()

    msg = f"""
<b>🖥 SERVER STATUS LIVE</b>
━━━━━━━━━━━━━━━━━━━━
<b>⚙️ CPU:</b> {cpu_usage}% ({cpu_cores} Cores @ {cpu_freq:.0f}Mhz)
<b>🧠 RAM:</b> {ram_used} / {ram_total} ({ram_percent}%)
<b>💾 DISK:</b> {disk_used} / {disk_total} ({disk_percent}%)
<b>🌐 OS:</b> {os_name} {os_release}
<b>⏱ UPTIME:</b> {uptime_str}

<b>📡 NETWORK TRAFFIC</b>
<b>⬇️ IN:</b> {net_recv}
<b>⬆️ OUT:</b> {net_sent}
━━━━━━━━━━━━━━━━━━━━
<i>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
    return msg
