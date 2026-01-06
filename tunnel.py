import os
import subprocess
import sys
import time
from config import Config
from logger import log

def run_tunnel():
    """
    Menjalankan Cloudflare Tunnel dengan Token Permanen.
    """
    # 1. Download Cloudflared Binary jika belum ada
    if not os.path.exists("./cloudflared"):
        log.info("⬇️ Downloading Cloudflared binary...")
        try:
            # Download versi Linux AMD64 (Standar Pterodactyl/VPS)
            subprocess.run("curl -L --output cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", shell=True, check=True)
            subprocess.run("chmod +x cloudflared", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            log.critical(f"❌ Failed to download cloudflared: {e}")
            return # Jangan exit sys, biarkan server tetap jalan lokal
    
    # 2. Cek apakah tunnel sudah jalan
    # (Opsional: kill instance lama jika perlu, tapi hati-hati di container)
    # subprocess.run("pkill cloudflared", shell=True)
    
    # 3. Jalankan Tunnel
    log.info(f"🚀 Starting Cloudflare Tunnel for {Config.HOSTNAME}...")
    
    cmd = f"./cloudflared tunnel run --token {Config.TUNNEL_TOKEN}"
    
    try:
        # Jalankan di background (Non-blocking)
        # stderr/stdout dibuang ke DEVNULL agar log console Python bersih
        subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Beri waktu sedikit untuk inisialisasi
        time.sleep(3)
        log.info("✅ Tunnel Service Running in Background")
        log.info(f"🔗 Public Access: https://{Config.HOSTNAME}")
        
    except Exception as e:
        log.critical(f"❌ Failed to start tunnel process: {e}")

if __name__ == "__main__":
    run_tunnel()
    # Loop dummy agar container tidak mati jika dijalankan manual
    while True:
        time.sleep(60)