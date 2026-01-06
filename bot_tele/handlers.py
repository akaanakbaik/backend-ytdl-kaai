import os
import sys
import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import Config
from .system.sys_info import get_server_status
from .system.db import get_traffic_stats
from .feature.backup import perform_smart_backup
from .feature.ytdl_bot import process_ytdl_request
from .feature.extras import run_speedtest_task, get_ip_info, force_clean_system, exec_shell
from .feature.advanced import get_server_deep_info, security_audit, get_memos, add_memo, clear_memos
from .keyboards import main_menu, admin_menu, back_home, ytdl_menu, memo_menu
from .loader import bot

router = Router()

# State Management
class AppStates(StatesGroup):
    shell = State()
    broadcast = State()
    memo = State()

# --- START & WELCOME ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = (message.from_user.id == Config.TELE_ADMIN_ID)
    status = "👑 Administrator" if is_admin else "👤 User"
    
    txt = f"""
<b>🤖 KAAI SYSTEM OPERATIONAL v7.5</b>
━━━━━━━━━━━━━━━━━━━━━━━━
👋 <b>Welcome, {message.from_user.full_name}!</b>
🔑 <b>Access Level:</b> {status}
🗓 <b>Date:</b> {os.popen('date').read().strip()}

<i>"System is running optimally. Ready to serve requests."</i>

👇 <b>NAVIGATION PANEL</b>
"""
    await message.answer(txt, reply_markup=main_menu(is_admin))

@router.callback_query(F.data == "menu_home")
async def cb_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == Config.TELE_ADMIN_ID)
    await call.message.edit_text("<b>🏠 MAIN DASHBOARD</b>\nSelect module to execute:", reply_markup=main_menu(is_admin))

# --- INFO MODULES ---
@router.callback_query(F.data == "menu_stats")
async def cb_stats(call: types.CallbackQuery):
    msg = get_server_status()
    await call.message.edit_text(f"{msg}\n\n<i>Last Refresh: Just now</i>", reply_markup=back_home())

@router.callback_query(F.data == "menu_traffic")
async def cb_traffic(call: types.CallbackQuery):
    msg = get_traffic_stats()
    await call.message.edit_text(f"{msg}\n\n<i>Data is synchronized daily.</i>", reply_markup=back_home())

@router.callback_query(F.data == "adv_info")
async def cb_adv_info(call: types.CallbackQuery):
    msg = get_server_deep_info()
    await call.message.edit_text(f"{msg}", reply_markup=back_home())

# --- ADMIN CORE ---
@router.callback_query(F.data == "menu_admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id != Config.TELE_ADMIN_ID:
        return await call.answer("⛔ RESTRICTED ACCESS!", show_alert=True)
    await call.message.edit_text("<b>🛠 GOD MODE ACTIVATED</b>\n\nChoose administrative action:", reply_markup=admin_menu())

# Feature 1: Security Audit
@router.callback_query(F.data == "adv_sec")
async def cb_sec(call: types.CallbackQuery):
    msg = security_audit()
    await call.message.edit_text(msg, reply_markup=admin_menu())

# Feature 2: Memo System
@router.callback_query(F.data == "adv_memo")
async def cb_memo(call: types.CallbackQuery):
    memos = get_memos()
    if not memos:
        txt = "<b>📝 ADMIN NOTES</b>\n\n<i>No active notes found.</i>"
    else:
        txt = "<b>📝 ADMIN NOTES</b>\n━━━━━━━━━━\n"
        for i, m in enumerate(memos, 1):
            txt += f"{i}. {m['text']} <i>({m['date']})</i>\n"
    
    await call.message.edit_text(txt, reply_markup=memo_menu())

@router.callback_query(F.data == "memo_add")
async def cb_memo_add(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("✍️ <b>Type your note:</b>", reply_markup=back_home())
    await state.set_state(AppStates.memo)

@router.message(AppStates.memo)
async def process_memo(message: types.Message, state: FSMContext):
    add_memo(message.text)
    await message.reply("✅ <b>Note Saved!</b>")
    await state.clear()
    # Kembali ke menu memo (optional, atau home)

@router.callback_query(F.data == "memo_clear")
async def cb_memo_clear(call: types.CallbackQuery):
    clear_memos()
    await call.answer("🗑 All notes deleted!")
    await cb_memo(call)

# Feature 3: Speedtest Enhanced
@router.callback_query(F.data == "adm_speedtest")
async def cb_speed(call: types.CallbackQuery):
    await call.message.edit_text("🚀 <b>INITIATING SPEEDTEST...</b>\n\n<i>Connecting to nearest server...</i>\n<i>Testing download/upload...</i>")
    try:
        dl, ul, ping = await run_speedtest_task()
        res = f"""
<b>🚀 NETWORK PERFORMANCE RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>⬇️ Download:</b> <code>{dl:.2f} Mbps</code>
<b>⬆️ Upload:</b> <code>{ul:.2f} Mbps</code>
<b>📶 Latency:</b> <code>{ping:.0f} ms</code>
━━━━━━━━━━━━━━━━━━━━━━━━
<i>Test completed successfully.</i>
"""
        await call.message.edit_text(res, reply_markup=admin_menu())
    except: await call.message.edit_text("❌ Connection Timeout / Failed", reply_markup=admin_menu())

# Feature 4: Backup & Sync
@router.callback_query(F.data == "menu_backup")
async def cb_backup(call: types.CallbackQuery):
    prog = await call.message.edit_text("📦 <b>BACKUP SEQUENCE STARTED</b>\n\n1️⃣ Indexing files...\n2️⃣ Compressing data...\n3️⃣ Syncing to GitHub...\n4️⃣ Splitting chunks...")
    
    files, status = await perform_smart_backup()
    
    if files:
        await prog.edit_text(f"✅ <b>BACKUP COMPLETE</b>\n\n📂 Parts: {len(files)}\n🔗 Repo: {status}\n\n<i>Uploading to Telegram...</i>")
        try:
            for path in files:
                await call.message.answer_document(FSInputFile(path), caption=f"🗂 <b>{os.path.basename(path)}</b>")
                os.remove(path)
            await call.message.answer("<b>✅ All files transferred successfully.</b>", reply_markup=admin_menu())
        except Exception as e:
            await call.message.answer(f"⚠️ Upload Error: {e}")
    else:
        await prog.edit_text(f"❌ <b>CRITICAL ERROR</b>\nReason: {status}", reply_markup=admin_menu())

# Feature 5: Clean & Purge
@router.callback_query(F.data == "adm_clean")
async def cb_clean(call: types.CallbackQuery):
    count = force_clean_system()
    await call.answer(f"🧹 System Purged: {count} Junk Files Deleted!", show_alert=True)

# Feature 6: Terminal Shell
@router.callback_query(F.data == "adm_shell")
async def cb_shell(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("💻 <b>TERMINAL SESSION ACTIVE</b>\n\nType any Linux command to execute.\nExample: <code>ls -la</code> or <code>df -h</code>", reply_markup=back_home())
    await state.set_state(AppStates.shell)

@router.message(AppStates.shell)
async def process_shell(message: types.Message):
    cmd = message.text
    res = await exec_shell(cmd)
    
    # Format output agar rapi
    if len(res) > 4000: res = res[:4000] + "... (truncated)"
    
    output = f"<b>root@kaai:~#</b> <code>{cmd}</code>\n\n<pre>{res}</pre>"
    await message.reply(output)

# Feature 7: Advanced Broadcast
@router.callback_query(F.data == "adm_broadcast")
async def cb_bc(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📢 <b>BROADCAST MODE</b>\n\nSend your message (Support HTML, Photo, Video).\nThis message will be pinned in Log Channel.", reply_markup=back_home())
    await state.set_state(AppStates.broadcast)

@router.message(AppStates.broadcast)
async def process_bc(message: types.Message, state: FSMContext):
    if not Config.TELE_LOG_ID: return await message.reply("❌ Log ID not set!")
    
    try:
        # Copy message exactly as is (text/media)
        sent = await message.copy_to(Config.TELE_LOG_ID)
        try: await bot.pin_chat_message(Config.TELE_LOG_ID, sent.message_id)
        except: pass
        
        await message.reply("✅ <b>Broadcast Sent & Pinned!</b>")
        await state.clear()
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# --- YTDL SYSTEM ---
@router.callback_query(F.data == "menu_ytdl")
async def cb_ytdl(call: types.CallbackQuery):
    await call.message.edit_text("<b>📺 YTDL DOWNLOADER</b>\n\nPaste your YouTube link below:", reply_markup=back_home())

@router.message(F.text.regexp(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'))
async def process_link(message: types.Message):
    # Global state (simple)
    global url_cache
    url_cache = getattr(globals(), 'url_cache', {})
    url_cache[message.from_user.id] = message.text
    
    txt = f"<b>🔗 LINK IDENTIFIED</b>\n<code>{message.text}</code>\n\nSelect output format:"
    await message.reply(txt, reply_markup=ytdl_menu())

@router.callback_query(F.data.startswith("dl_mode_"))
async def cb_dl_run(call: types.CallbackQuery):
    url = globals().get('url_cache', {}).get(call.from_user.id)
    if not url: return await call.answer("❌ Session Expired. Send link again.", show_alert=True)
    
    mode = "audio" if "audio" in call.data else "video"
    await call.message.delete()
    
    prog_msg = await call.message.answer(f"⚙️ <b>ENGINE STARTED</b>\nProcessing {mode.upper()} request...")
    await process_ytdl_request(bot, call.message.chat.id, url, mode, prog_msg.message_id)
