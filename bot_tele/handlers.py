import os
import sys
import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

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

# State Management Updated
class AppStates(StatesGroup):
    shell = State()
    broadcast = State()
    memo = State()
    ban_user = State()

# --- HELPER: SAFE EDIT ---
async def safe_edit(call, text, reply_markup=None):
    try:
        await call.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e): return # Ignore if same
        await call.message.answer(text, reply_markup=reply_markup) # Fallback new msg

# --- START & WELCOME ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = (message.from_user.id == Config.TELE_ADMIN_ID)
    status = "👑 Administrator" if is_admin else "👤 User"
    
    txt = f"""
<b>🤖 KAAI SYSTEM OPERATIONAL v8.0</b>
━━━━━━━━━━━━━━━━━━━━━━━━
👋 <b>Welcome, {message.from_user.full_name}!</b>
🔑 <b>Access Level:</b> {status}
🆔 <b>ID:</b> <code>{message.from_user.id}</code>

<i>"System is ready. Select a module below."</i>
"""
    await message.answer(txt, reply_markup=main_menu(is_admin))

@router.callback_query(F.data == "menu_home")
async def cb_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == Config.TELE_ADMIN_ID)
    await safe_edit(call, "<b>🏠 MAIN DASHBOARD</b>", reply_markup=main_menu(is_admin))

# --- INFO MODULES ---
@router.callback_query(F.data == "menu_stats")
async def cb_stats(call: types.CallbackQuery):
    await bot.send_chat_action(call.message.chat.id, "typing")
    msg = get_server_status()
    await safe_edit(call, f"{msg}\n\n<i>Live Data</i>", reply_markup=back_home())

@router.callback_query(F.data == "menu_traffic")
async def cb_traffic(call: types.CallbackQuery):
    msg = get_traffic_stats()
    await safe_edit(call, msg, reply_markup=back_home())

@router.callback_query(F.data == "adv_info")
async def cb_adv_info(call: types.CallbackQuery):
    msg = get_server_deep_info()
    await safe_edit(call, msg, reply_markup=back_home())

# --- ADMIN CORE ---
@router.callback_query(F.data == "menu_admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id != Config.TELE_ADMIN_ID:
        return await call.answer("⛔ RESTRICTED ACCESS!", show_alert=True)
    await safe_edit(call, "<b>🛠 GOD MODE ACTIVATED</b>", reply_markup=admin_menu())

# Feature 1: Security Audit
@router.callback_query(F.data == "adv_sec")
async def cb_sec(call: types.CallbackQuery):
    msg = security_audit()
    await safe_edit(call, msg, reply_markup=admin_menu())

# Feature 2: Memo System
@router.callback_query(F.data == "adv_memo")
async def cb_memo(call: types.CallbackQuery):
    memos = get_memos()
    txt = "<b>📝 ADMIN NOTES</b>\n━━━━━━━━━━\n"
    if not memos: txt += "<i>No active notes found.</i>"
    else:
        for i, m in enumerate(memos, 1):
            txt += f"{i}. {m['text']} <i>({m['date']})</i>\n"
    await safe_edit(call, txt, reply_markup=memo_menu())

@router.callback_query(F.data == "memo_add")
async def cb_memo_add(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "✍️ <b>Type your note:</b>", reply_markup=back_home())
    await state.set_state(AppStates.memo)

@router.message(AppStates.memo)
async def process_memo(message: types.Message, state: FSMContext):
    add_memo(message.text)
    await message.reply("✅ <b>Note Saved!</b>")
    await state.clear()

@router.callback_query(F.data == "memo_clear")
async def cb_memo_clear(call: types.CallbackQuery):
    clear_memos()
    await call.answer("🗑 Deleted!")
    await cb_memo(call)

# Feature 3: Speedtest
@router.callback_query(F.data == "adm_speedtest")
async def cb_speed(call: types.CallbackQuery):
    await safe_edit(call, "🚀 <b>Running Speedtest...</b>\n<i>Please wait ~20s...</i>")
    try:
        dl, ul, ping = await run_speedtest_task()
        res = f"<b>🚀 RESULT</b>\n⬇️ {dl:.2f} Mbps\n⬆️ {ul:.2f} Mbps\n📶 {ping:.0f} ms"
        await safe_edit(call, res, reply_markup=admin_menu())
    except: await safe_edit(call, "❌ Failed", reply_markup=admin_menu())

# Feature 4: Backup
@router.callback_query(F.data == "menu_backup")
async def cb_backup(call: types.CallbackQuery):
    await safe_edit(call, "📦 <b>Backup Process Started...</b>\n<i>Syncing GitHub & Compressing...</i>")
    files, status = await perform_smart_backup()
    
    if files:
        await call.message.answer(f"✅ <b>Done!</b>\nRepo: {status}\nSending files...")
        try:
            for path in files:
                await call.message.answer_document(FSInputFile(path))
                os.remove(path)
        except Exception as e:
            await call.message.answer(f"⚠️ Upload Err: {e}")
    else:
        await call.message.answer(f"❌ Error: {status}")

# Feature 5: Clean
@router.callback_query(F.data == "adm_clean")
async def cb_clean(call: types.CallbackQuery):
    count = force_clean_system()
    await call.answer(f"🧹 {count} Files Purged!", show_alert=True)

# Feature 6: Shell
@router.callback_query(F.data == "adm_shell")
async def cb_shell(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "💻 <b>TERMINAL</b>\nType command:", reply_markup=back_home())
    await state.set_state(AppStates.shell)

@router.message(AppStates.shell)
async def process_shell(message: types.Message):
    cmd = message.text
    res = await exec_shell(cmd)
    if len(res) > 4000: res = res[:4000] + "..."
    await message.reply(f"<pre>{res}</pre>")

# Feature 7: Broadcast
@router.callback_query(F.data == "adm_broadcast")
async def cb_bc(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "📢 <b>BROADCAST</b>\nSend message to pin:", reply_markup=back_home())
    await state.set_state(AppStates.broadcast)

@router.message(AppStates.broadcast)
async def process_bc(message: types.Message, state: FSMContext):
    if Config.TELE_LOG_ID:
        sent = await message.copy_to(Config.TELE_LOG_ID)
        try: await bot.pin_chat_message(Config.TELE_LOG_ID, sent.message_id)
        except: pass
        await message.reply("✅ Sent!")
    await state.clear()

# Feature 8 (NEW): Ban User System
@router.callback_query(F.data == "adm_ban")
async def cb_ban(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "🚫 <b>BAN USER</b>\nKirim ID User Telegram:", reply_markup=back_home())
    await state.set_state(AppStates.ban_user)

@router.message(AppStates.ban_user)
async def process_ban(message: types.Message, state: FSMContext):
    # Logic banned user (simple append to file)
    with open(Config.BANNED_FILE, "a") as f: f.write(f"{message.text}\n")
    await message.reply(f"🚫 ID {message.text} Banned!")
    await state.clear()

# Feature 9 (NEW): Auto Reboot
@router.callback_query(F.data == "adm_reboot")
async def cb_reboot(call: types.CallbackQuery):
    await call.answer("🔄 Rebooting System...", show_alert=True)
    os.execv(sys.executable, ['python3'] + sys.argv)

# --- YTDL ---
@router.callback_query(F.data == "menu_ytdl")
async def cb_ytdl(call: types.CallbackQuery):
    await safe_edit(call, "<b>📺 YTDL DOWNLOADER</b>\nKirim Link YouTube:", reply_markup=back_home())

@router.message(F.text.regexp(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'))
async def process_link(message: types.Message):
    # Check Ban
    try:
        if os.path.exists(Config.BANNED_FILE):
            with open(Config.BANNED_FILE) as f:
                if str(message.from_user.id) in f.read(): return
    except: pass

    global url_cache
    url_cache = getattr(globals(), 'url_cache', {})
    url_cache[message.from_user.id] = message.text
    
    await message.reply("🔗 <b>Link Detected!</b>\nSelect Format:", reply_markup=ytdl_menu())

@router.callback_query(F.data.startswith("dl_mode_"))
async def cb_dl_start(call: types.CallbackQuery):
    url = globals().get('url_cache', {}).get(call.from_user.id)
    if not url: return await call.answer("❌ Expired", show_alert=True)
    
    mode = call.data.split("_")[2]
    await call.message.delete()
    
    msg = await call.message.answer(f"⚙️ <b>Processing {mode.upper()}...</b>")
    await process_ytdl_request(bot, call.message.chat.id, url, mode, msg.message_id)
