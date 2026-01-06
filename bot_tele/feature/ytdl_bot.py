import os
from aiogram.types import FSInputFile
from config import Config
from engine import run_dual_engine_buffer

async def process_ytdl_request(bot, chat_id, url, type_req, msg_id_to_edit=None):
    """
    Menjalankan proses download dan upload ke Telegram.
    """
    try:
        # Edit pesan jadi "Processing"
        if msg_id_to_edit:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=msg_id_to_edit, 
                text="⏳ <b>Sedang Memproses di Server...</b>\nMohon tunggu, sedang download dan convert."
            )
        
        # Panggil Engine Utama
        res = await run_dual_engine_buffer(url, type_req)
        
        if res['status'] != 'ok':
            text = f"❌ <b>Gagal:</b> {res.get('error_detail', 'Unknown Error')}"
            if msg_id_to_edit:
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id_to_edit, text=text)
            else:
                await bot.send_message(chat_id, text)
            return

        # Upload Phase
        if msg_id_to_edit:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=msg_id_to_edit, 
                text="🚀 <b>Mengunggah ke Telegram...</b>\nFile sudah siap, sedang dikirim."
            )

        filename = res['filename']
        filepath = os.path.join(Config.TMP_DIR, filename)
        
        caption = f"""
<b>✅ DOWNLOAD SUKSES</b>
━━━━━━━━━━━━━━━━
<b>📌 Judul:</b> {res.get('title')}
<b>⏱ Durasi:</b> {res.get('duration')}
<b>👤 Channel:</b> {res.get('author')}
<b>🛠 Engine:</b> {res.get('engine')}
━━━━━━━━━━━━━━━━
<i>Powered by KAAI YTDL</i>
"""
        
        media_file = FSInputFile(filepath)
        thumb_file = None
        
        # Download thumbnail logic (optional, skip for speed)
        # if res.get('thumbnail'): ...

        if type_req == "audio":
            await bot.send_audio(chat_id, audio=media_file, caption=caption)
        else:
            await bot.send_video(chat_id, video=media_file, caption=caption)
            
        # Hapus pesan status
        if msg_id_to_edit:
            await bot.delete_message(chat_id, msg_id_to_edit)
            
    except Exception as e:
        err_text = f"❌ <b>System Error:</b> {str(e)}"
        if msg_id_to_edit:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id_to_edit, text=err_text)
        else:
            await bot.send_message(chat_id, err_text)
