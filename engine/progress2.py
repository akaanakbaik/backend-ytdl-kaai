import asyncio
import aiohttp
import re
import json
import base64
import time
import random
import os
from urllib.parse import quote, urlparse, parse_qs, urlencode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import STATUS_OK, STATUS_FAIL
from logger import log
from proxy_manager import report_proxy_status

# --- HELPER: ROBUST REQUESTER ---
async def fetch_smart(session, url, method="GET", proxy=None, **kwargs):
    """
    Mencoba request dengan Proxy. 
    Jika gagal (Timeout/ConnectError), otomatis retry TANPA Proxy.
    """
    # 1. Try with Proxy
    if proxy:
        try:
            async with session.request(method, url, proxy=proxy, **kwargs) as resp:
                # Jika sukses, lapor proxy bagus
                if resp.status == 200:
                    report_proxy_status(proxy, True)
                    if kwargs.get("json_res"): return await resp.json()
                    if kwargs.get("text_res"): return await resp.text()
                    return resp
                # Jika status code error fatal (403/429), jangan retry direct (karena IP server mungkin juga kena)
                if resp.status in [403, 429]:
                    return None
        except Exception:
            # Proxy error, lapor proxy jelek
            report_proxy_status(proxy, False)
            # Lanjut ke retry direct di bawah

    # 2. Retry Direct (Tanpa Proxy)
    try:
        # Hapus proxy dari kwargs jika ada (untuk safety)
        kwargs.pop("proxy", None)
        async with session.request(method, url, proxy=None, **kwargs) as resp:
            if resp.status == 200:
                if kwargs.get("json_res"): return await resp.json()
                if kwargs.get("text_res"): return await resp.text()
                return resp
    except:
        pass
    
    return None

# --- MAIN ENGINE ---
async def run_engine_b(url: str, output_path: str, type_req: str, proxies: list, uas: list):
    log.info("ENGINE B SWARM STARTED (Smart Fallback)")
    
    tasks = []
    
    # Pastikan pool tidak kosong
    proxies_pool = proxies if proxies else [None] * 5
    uas_pool = uas if uas else ["Mozilla/5.0"] * 5
    
    # Launch Swarm (Semua Scraper Jalan Bareng)
    # Kita acak proxy/ua untuk variasi
    tasks.append(asyncio.create_task(scraper_savetube(url, type_req, random.choice(proxies_pool), random.choice(uas_pool))))
    tasks.append(asyncio.create_task(scraper_ytdlp_online(url, type_req, random.choice(proxies_pool), random.choice(uas_pool))))
    tasks.append(asyncio.create_task(scraper_ytdown(url, type_req, random.choice(proxies_pool), random.choice(uas_pool))))
    tasks.append(asyncio.create_task(scraper_optiklink(url, type_req, random.choice(proxies_pool), random.choice(uas_pool))))
    tasks.append(asyncio.create_task(scraper_y2mate(url, type_req, random.choice(proxies_pool), random.choice(uas_pool))))

    try:
        # Tunggu siapa yang selesai duluan (FIRST_COMPLETED)
        # Timeout total 120 detik
        for future in asyncio.as_completed(tasks, timeout=120):
            try:
                res = await future
                if res and res.get('url'):
                    # Pemenang ditemukan!
                    download_url = res['url']
                    engine_name = res.get('engine', 'Unknown')
                    
                    log.info(f"Engine B WINNER: ({engine_name}). Downloading...")
                    
                    # Download File Akhir
                    dl_proxy = random.choice(proxies_pool)
                    dl_ua = random.choice(uas_pool)
                    
                    if await _download_safe(download_url, output_path, dl_proxy, dl_ua):
                        # Cancel sisa task yang masih jalan biar hemat resource
                        for t in tasks: t.cancel()
                        
                        return {
                            "status": STATUS_OK,
                            "engine": f"Engine B ({engine_name})",
                            "title": res.get('title', 'Video Downloaded'),
                            "thumbnail": res.get('thumbnail'),
                            "duration": res.get('duration'),
                            "author": engine_name,
                            "filename": os.path.basename(output_path)
                        }
            except Exception:
                continue
    except asyncio.TimeoutError:
        pass
    
    # Jika semua gagal
    for t in tasks: t.cancel()
    return {"status": STATUS_FAIL, "reason": "All Scrapers Failed"}

# --- SAFE DOWNLOADER ---
async def _download_safe(url, path, proxy, ua):
    try:
        headers = {"User-Agent": ua, "Connection": "keep-alive"}
        timeout = aiohttp.ClientTimeout(total=600, connect=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Gunakan fetch_smart logic manual disini karena ini streaming
            # Try Proxy First
            try:
                if proxy:
                    async with session.get(url, headers=headers, proxy=proxy) as resp:
                        if resp.status == 200:
                            return await _stream_to_file(resp, path)
            except: pass
            
            # Try Direct
            async with session.get(url, headers=headers, proxy=None) as resp:
                if resp.status == 200:
                    return await _stream_to_file(resp, path)
                    
    except Exception as e:
        log.error(f"Engine B Download Error: {e}")
        pass

    if os.path.exists(path):
        try: os.remove(path)
        except: pass
    return False

async def _stream_to_file(resp, path):
    try:
        with open(path, 'wb') as f:
            async for chunk in resp.content.iter_chunked(1024*1024):
                f.write(chunk)
        if os.path.exists(path) and os.path.getsize(path) > 5000: return True
    except: pass
    return False

# ==========================================
# SCRAPER 1: SAVETUBE (AES DECRYPTION)
# ==========================================
async def scraper_savetube(url, type_req, proxy, ua):
    try:
        # Key Statis SaveTube (Hex)
        KEY_HEX = "C5D58EF67A7584E4A29F6C35BBC4EB12"
        KEY_BYTES = bytes.fromhex(KEY_HEX)
        
        def decrypt_savetube(enc_str):
            try:
                # 1. Base64 Decode (Remove whitespace)
                cleaned = enc_str.replace(" ", "").replace("\n", "")
                raw = base64.b64decode(cleaned)
                
                # 2. Split IV (16 bytes) & Data
                iv = raw[:16]
                ciphertext = raw[16:]
                
                # 3. AES-128-CBC Decrypt
                cipher = AES.new(KEY_BYTES, AES.MODE_CBC, iv)
                decrypted_padded = cipher.decrypt(ciphertext)
                
                # 4. Unpad (PKCS7)
                decrypted = unpad(decrypted_padded, AES.block_size)
                
                return json.loads(decrypted.decode('utf-8'))
            except Exception as e:
                log.error(f"SaveTube Decrypt Error: {e}")
                return None

        headers = {
            "User-Agent": ua,
            "Content-Type": "application/json",
            "origin": "https://ytsave.savetube.me",
            "referer": "https://ytsave.savetube.me/"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Get CDN
            cdn_data = await fetch_smart(session, "https://media.savetube.me/api/random-cdn", proxy=proxy, json_res=True)
            if not cdn_data: return None
            cdn_host = cdn_data.get("cdn")
            
            # 2. Get Info (Encrypted)
            info_res = await fetch_smart(session, f"https://{cdn_host}/v2/info", method="POST", json={"url": url}, proxy=proxy, json_res=True)
            if not info_res or not info_res.get("status"): return None
            
            # 3. Decrypt
            data = decrypt_savetube(info_res["data"])
            if not data: return None
            
            # 4. Select Format
            key = data["key"]
            id_val = data["id"]
            
            target_type = "audio" if type_req == 'audio' else "video"
            target_q = "720" # Default
            
            if target_type == "audio":
                # Cari bitrate tertinggi
                formats = data.get("audio_formats", [])
                if formats: target_q = formats[0]["quality"]
            else:
                # Cari MP4 720p atau tertinggi yg ada
                formats = data.get("video_formats", [])
                for fmt in formats:
                    if fmt["quality"] == 720: target_q = 720; break
                else:
                    if formats: target_q = formats[0]["quality"]

            # 5. Request Download Link
            dl_payload = {
                "id": id_val,
                "key": key,
                "downloadType": target_type,
                "quality": str(target_q)
            }
            
            dl_res = await fetch_smart(session, f"https://{cdn_host}/download", method="POST", json=dl_payload, proxy=proxy, json_res=True)
            
            if dl_res and dl_res.get("data", {}).get("downloadUrl"):
                return {
                    "engine": "SaveTube",
                    "url": dl_res["data"]["downloadUrl"],
                    "title": data.get("title"),
                    "thumbnail": data.get("thumbnail"),
                    "duration": data.get("duration")
                }
    except Exception as e: 
        pass
    return None

# ==========================================
# SCRAPER 2: YTDLP ONLINE
# ==========================================
async def scraper_ytdlp_online(url, type_req, proxy, ua):
    try:
        endpoint = "https://ytdlp.online/stream?command="
        # Regex extract ID
        if "youtu.be" in url: clean_url = url
        elif "v=" in url: clean_url = url
        else: return None
        
        if type_req == 'audio':
            command = f"-x --audio-format mp3 {clean_url}"
        else:
            command = f"-f best[ext=mp4] {clean_url}"
            
        request_url = endpoint + quote(command)
        
        async with aiohttp.ClientSession(headers={"User-Agent": ua, "Accept": "*/*"}) as session:
            # Ini streaming text response, jadi pakai logic khusus
            try:
                # Try Proxy
                if proxy:
                    async with session.get(request_url, proxy=proxy, timeout=45) as resp:
                        if resp.status == 200:
                            res = await _parse_ytdlp_stream(resp)
                            if res: report_proxy_status(proxy, True); return res
                            
                # Try Direct
                async with session.get(request_url, proxy=None, timeout=45) as resp:
                    if resp.status == 200:
                        return await _parse_ytdlp_stream(resp)
            except: pass
    except: pass
    return None

async def _parse_ytdlp_stream(resp):
    regex_dl = re.compile(r'href="([^"]+\.(mp3|mp4|m4a|webm))"|r(https:\/\/ytdlp\.online\/[^"\s]+\.(mp3|mp4|m4a|webm))', re.IGNORECASE)
    async for chunk in resp.content.iter_chunked(1024):
        text = chunk.decode(errors="ignore")
        m = regex_dl.search(text)
        if m:
            found = m.group(1) or m.group(3)
            if found and not found.startswith("http"): found = "https://ytdlp.online" + found
            return {"engine": "YtDlpOnline", "url": found, "title": "YtDlp Video"}
    return None

# ==========================================
# SCRAPER 3: OPTIKLINK
# ==========================================
async def scraper_optiklink(url, type_req, proxy, ua):
    try:
        api_url = "https://host.optikl.ink/download/youtube"
        fmt = "mp3" if type_req == 'audio' else "720"
        
        async with aiohttp.ClientSession(headers={"User-Agent": ua}) as session:
            data = await fetch_smart(session, api_url, params={"url": url, "format": fmt}, proxy=proxy, json_res=True)
            
            if data and data.get("code") == 200 and data.get("result"):
                r = data["result"]
                return {
                    "engine": "OptikLink",
                    "url": r.get("download"),
                    "title": r.get("title"),
                    "thumbnail": r.get("thumbnail"),
                    "duration": r.get("duration")
                }
    except: pass
    return None

# ==========================================
# SCRAPER 4: YTDOWN
# ==========================================
async def scraper_ytdown(url, type_req, proxy, ua):
    try:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": ua,
            "Referer": "https://ytdown.io/"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Get Init Data
            data = await fetch_smart(session, "https://ytdown.io/proxy.php", method="POST", data=urlencode({"url": url}), proxy=proxy, json_res=True)
            if not data: return None
            
            api_data = data.get("api", {})
            media_items = api_data.get("mediaItems", [])
            
            target_type = "audio" if type_req == 'audio' else "video"
            selected = None
            
            for item in media_items:
                if item["type"] == target_type: selected = item; break
            
            if not selected and media_items: selected = media_items[0]
            
            if selected:
                # 2. Resolve Final URL (Redirect check)
                async with session.get(selected["mediaUrl"], proxy=proxy, timeout=15) as m_resp:
                    if m_resp.status == 200:
                        m_json = await m_resp.json()
                        return {
                            "engine": "YTDown",
                            "url": m_json.get("fileUrl"),
                            "title": api_data.get("title"),
                            "thumbnail": api_data.get("imagePreviewUrl")
                        }
    except: pass
    return None

# ==========================================
# SCRAPER 5: Y2MATE (COMPLEX)
# ==========================================
async def scraper_y2mate(url, type_req, proxy, ua):
    try:
        headers = {"User-Agent": ua, "Referer": "https://y2mate.nu/"}
        if "youtu.be" in url: vid = url.split("/")[-1].split("?")[0]
        else: vid = parse_qs(urlparse(url).query).get("v", [""])[0]
        if not vid: return None

        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Init
            u_init = "ODh0VzVGdnB3a3BhTDhSWWhIVUxYZ1ZKaVp4STF1TFJiNDlBemtUM1ZNQ2lmejVfNFNoMVBpTTdMYnNTOUU1V050UzRJUXpF"
            t_init = int(time.time())
            init_url = f"https://eta.etacloud.org/api/v1/init?u={u_init}&t={t_init}"
            
            init_data = await fetch_smart(session, init_url, proxy=proxy, json_res=True)
            if not init_data: return None
            sig = init_data["sig"]

            # 2. Convert
            domains = ["eta.etacloud.org", "cocccc.etacloud.org", "ococoo.etacloud.org"]
            convert_url = f"https://{random.choice(domains)}/api/v1/convert"
            
            params = {
                "sig": sig, "v": vid,
                "f": "mp3" if type_req == 'audio' else "mp4",
                "t": int(time.time())
            }
            
            data = await fetch_smart(session, convert_url, params=params, proxy=proxy, json_res=True)
            
            if data and "data" in data:
                # Cari kualitas terbaik
                items = data["data"]
                # Sorting sederhana berdasarkan angka di string quality
                best = sorted(items, key=lambda x: int(re.findall(r"\d+", x.get("quality", "0") or "0")[0]), reverse=True)[0]
                return {
                    "engine": "Y2Mate",
                    "url": best.get("url"),
                    "title": data.get("title")
                }
    except: pass
    return None
