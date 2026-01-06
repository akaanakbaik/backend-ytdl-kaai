import os, shutil, zipfile, asyncio
from datetime import datetime
from git import Repo
from config import Config

# Batas aman Telegram (49MB agar aman dari limit 50MB)
CHUNK_SIZE = 49 * 1024 * 1024 

def split_file(file_path):
    """Memecah file ZIP jika terlalu besar"""
    parts = []
    if os.path.getsize(file_path) <= CHUNK_SIZE:
        return [file_path]
    
    with open(file_path, 'rb') as f:
        part_num = 1
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk: break
            part_name = f"{file_path}.part{part_num}"
            with open(part_name, 'wb') as p:
                p.write(chunk)
            parts.append(part_name)
            part_num += 1
            
    # Hapus file asli yang kegedean agar hemat space
    os.remove(file_path)
    return parts

async def perform_smart_backup():
    try:
        # 1. SETUP
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
        now_str = datetime.now().strftime('%H-%M_%d-%m')
        zip_name = f"backup_{now_str}.zip"
        zip_path = os.path.join(Config.BACKUP_DIR, zip_name)
        
        # 2. CREATE ZIP LOCAL (Exclude sampah berat)
        EXCLUDE = {
            '__pycache__', '.local', 'backups', 'bin', 'venv', 
            'tmp', 'cache', 'logs', 'log_error', '.git', 'node_modules',
            'ffmpeg-master-latest-linux64-gpl' # FFmpeg binary besar, jangan backup
        }
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(Config.BASE_DIR):
                dirs[:] = [d for d in dirs if d not in EXCLUDE]
                for file in files:
                    if file.endswith('.zip') or file.endswith('.log') or file.endswith('.part'): continue
                    abs_path = os.path.join(root, file)
                    # Skip file > 100MB (misal video sisa)
                    if os.path.getsize(abs_path) > 100 * 1024 * 1024: continue
                    rel_path = os.path.relpath(abs_path, Config.BASE_DIR)
                    zipf.write(abs_path, rel_path)

        # 3. GITHUB SYNC (Non-Blocking)
        push_status = "Skipped (No Config)"
        if Config.GH_TOKEN and "ghp_" in Config.GH_TOKEN:
            try:
                # Run Git in executor to avoid blocking bot
                loop = asyncio.get_running_loop()
                push_status = await loop.run_in_executor(None, _sync_github, zip_path, now_str)
            except Exception as e:
                push_status = f"❌ Git Error: {str(e)[:50]}..."

        # 4. SPLIT CHECK
        final_files = split_file(zip_path)
        
        return final_files, push_status

    except Exception as e:
        return None, str(e)

def _sync_github(zip_path, now_str):
    """Fungsi sinkronisasi Git (Blocking I/O - Dijalankan di Thread)"""
    repo_dir = os.path.join(Config.BASE_DIR, "upload_repo")
    if os.path.exists(repo_dir): shutil.rmtree(repo_dir)
    
    try:
        # Clone
        auth_url = Config.GH_REPO.replace("https://", f"https://{Config.GH_TOKEN}@")
        repo = Repo.clone_from(auth_url, repo_dir)
        
        # Bersihkan repo lama (kecuali penting)
        for item in os.listdir(repo_dir):
            if item in ['.git', 'README.md', 'LICENSE']: continue
            p = os.path.join(repo_dir, item)
            if os.path.isdir(p): shutil.rmtree(p)
            else: os.remove(p)
            
        # Extract Backup Baru
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(repo_dir)
            
        # Sanitasi Config
        cfg = os.path.join(repo_dir, "config.py")
        if os.path.exists(cfg):
            with open(cfg, "w") as f: f.write(Config.DUMMY_CONFIG_CONTENT)
            
        # Push
        repo.git.add(all=True)
        repo.index.commit(f"Backup: {now_str}")
        repo.remote('origin').push()
        
        shutil.rmtree(repo_dir, ignore_errors=True)
        return "✅ GitHub Updated"
    except Exception as e:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise e
