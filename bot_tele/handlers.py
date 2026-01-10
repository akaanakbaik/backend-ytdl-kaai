import os
import sys
import asyncio
import time
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, URLInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from config import Config
from .system.sys_info import get_server_status
from .system.db import get_traffic_stats
from .feature.backup import perform_smart_backup
from .feature.ytdl_bot import process_ytdl_request
from .feature.extras import (
    run_speedtest_task, get_ip_info, force_clean_system, exec_shell,
    get_cpu_temp, list_temp_files, whois_lookup, random_quote,
    make_qr, gen_password, get_top_processes
)
from .feature.advanced import get_server_deep_info, security_audit, get_memos, add_memo, clear_memos
from .keyboards import main_menu, admin_menu, back_home, ytdl_menu, memo_menu, tools_menu
from .loader import bot

router = Router()

class AppStates(StatesGroup):
    shell = State()
    broadcast = State()
    memo = State()
    ban_user = State()
    qr_maker = State()
    whois = State()

async def safe_edit(call: types.CallbackQuery, text, reply_markup=None):
    try: 
        await call.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e): return
        await call.message.answer(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except Exception as e:
        await call.message.answer(f"⚠️ Error: {e}", reply_markup=reply_markup)

# --- START & WELCOME ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = (message.from_user.id == Config.TELE_ADMIN_ID)
    role = "SYSTEM ADMINISTRATOR" if is_admin else "GUEST USER"
    
    # URL Banner Logo
    banner = "https://raw.githubusercontent.com/akaanakbaik/belajar-frontand-dan-backend-terpisah/main/media/logo.jpg"
    
    caption = f"""
<b>👋 KAAI CONTROL CENTER V10</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>👤 User:</b> <code>{message.from_user.full_name}</code>
<b>🆔 ID:</b> <code>{message.from_user.id}</code>
<b>🔐 Access:</b> {role}
<b>📡 Server:</b> Online

<i>"Selamat datang di pusat kontrol KAAI. Gunakan menu di bawah untuk mengelola server & layanan."</i>
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    try:
        await message.answer_photo(
            photo=URLInputFile(banner),
            caption=caption,
            reply_markup=main_menu(is_admin)
        )
    except:
        await message.answer(caption, reply_markup=main_menu(is_admin))

# --- MENU NAVIGATION ---
@router.callback_query(F.data == "menu_home")
async def cb_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == Config.TELE_ADMIN_ID)
    
    text = f"""
<b>🏠 MAIN DASHBOARD</b>
━━━━━━━━━━━━━━━━━━━━━━━━
Silakan pilih modul yang ingin diakses:

• <b>Downloader</b>: Unduh media YouTube
• <b>Monitoring</b>: Cek status server
• <b>Tools</b>: Alat bantu utilitas
"""
    await safe_edit(call, text, reply_markup=main_menu(is_admin))

@router.callback_query(F.data == "menu_tools")
async def cb_tools(call: types.CallbackQuery):
    txt = "<b>🛠 UTILITY TOOLS</b>\nPilih alat yang ingin digunakan:"
    await safe_edit(call, txt, reply_markup=tools_menu())

@router.callback_query(F.data == "menu_admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id != Config.TELE_ADMIN_ID:
        return await call.answer("⛔ Access Denied!", show_alert=True)
    await safe_edit(call, "<b>🔐 ADMIN DASHBOARD</b>", reply_markup=admin_menu())

# --- INFO & MONITORING ---
@router.callback_query(F.data == "menu_stats")
async def cb_stats(call: types.CallbackQuery):
    await bot.send_chat_action(call.message.chat.id, "typing")
    stats = get_server_status()
    await safe_edit(call, f"{stats}\n\n<i>Live Data</i>", reply_markup=back_home())

@router.callback_query(F.data == "menu_traffic")
async def cb_traffic(call: types.CallbackQuery):
    msg = get_traffic_stats()
    await safe_edit(call, msg, reply_markup=back_home())

@router.callback_query(F.data == "adv_info")
async def cb_adv_info(call: types.CallbackQuery):
    info = get_server_deep_info()
    quote = random_quote()
    await safe_edit(call, f"{info}\n\n{quote}", reply_markup=back_home())

# --- YTDL DOWNLOADER ---
@router.callback_query(F.data == "menu_ytdl")
async def cb_ytdl(call: types.CallbackQuery):
    txt = """
<b>📺 YOUTUBE DOWNLOADER</b>
━━━━━━━━━━━━━━━━━━━━━━━━
Kirimkan Link YouTube (Video/Shorts) untuk memulai proses download.

<i>Supports: MP3 Audio & MP4 Video High Quality</i>
"""
    await safe_edit(call, txt, reply_markup=back_home())

@router.message(F.text.regexp(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'))
async def process_link(message: types.Message):
    # Check Banned User
    try:
        if os.path.exists(Config.BANNED_FILE):
            with open(Config.BANNED_FILE) as f:
                if str(message.from_user.id) in f.read(): return
    except: pass

    global url_cache
    url_cache = getattr(globals(), 'url_cache', {})
    url_cache[message.from_user.id] = message.text
    
    txt = f"<b>🔗 LINK DETECTED</b>\n<code>{message.text}</code>\n\n👇 <b>Pilih Format Output:</b>"
    await message.reply(txt, reply_markup=ytdl_menu())

@router.callback_query(F.data.startswith("dl_mode_"))
async def cb_dl_start(call: types.CallbackQuery):
    url = globals().get('url_cache', {}).get(call.from_user.id)
    if not url: return await call.answer("❌ Link Expired", show_alert=True)
    
    mode = call.data.split("_")[2]
    await call.message.delete()
    
    msg = await call.message.answer(f"⏳ <b>Memproses {mode.upper()}...</b>\nMohon tunggu sebentar...")
    await process_ytdl_request(bot, call.message.chat.id, url, mode, msg.message_id)

# --- USER TOOLS ---
@router.callback_query(F.data == "feat_whois")
async def cb_whois(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "🔎 <b>WHOIS LOOKUP</b>\nKirim Domain atau IP Address:", reply_markup=back_home())
    await state.set_state(AppStates.whois)

@router.message(AppStates.whois)
async def process_whois(message: types.Message, state: FSMContext):
    res = whois_lookup(message.text)
    await message.reply(res)
    await state.clear()

@router.callback_query(F.data == "feat_files")
async def cb_files(call: types.CallbackQuery):
    msg = list_temp_files()
    await safe_edit(call, msg, reply_markup=tools_menu())

@router.callback_query(F.data == "feat_temp")
async def cb_temp(call: types.CallbackQuery):
    msg = get_cpu_temp()
    await safe_edit(call, msg, reply_markup=tools_menu())

@router.callback_query(F.data == "tool_qr")
async def cb_qr(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "📱 <b>QR GENERATOR</b>\nKirim teks/link:", reply_markup=back_home())
    await state.set_state(AppStates.qr_maker)

@router.message(AppStates.qr_maker)
async def process_qr(message: types.Message, state: FSMContext):
    path = make_qr(message.text)
    await message.reply_photo(FSInputFile(path), caption=f"✅ QR Code: <code>{message.text}</code>")
    try: os.remove(path)
    except: pass
    await state.clear()

@router.callback_query(F.data == "tool_pass")
async def cb_pass(call: types.CallbackQuery):
    pwd = gen_password(16)
    await call.message.answer(f"🔑 <b>Generated Password:</b>\n<code>{pwd}</code>", reply_markup=tools_menu())

# --- ADMIN TOOLS ---
@router.callback_query(F.data == "adm_speedtest")
async def cb_speed(call: types.CallbackQuery):
    await safe_edit(call, "🚀 <b>Running Speedtest...</b>\n<i>Please wait ~20s...</i>")
    try:
        dl, ul, ping = await run_speedtest_task()
        res = f"<b>🚀 RESULT</b>\n⬇️ {dl:.2f} Mbps\n⬆️ {ul:.2f} Mbps\n📶 {ping:.0f} ms"
        await safe_edit(call, res, reply_markup=admin_menu())
    except: await safe_edit(call, "❌ Failed", reply_markup=admin_menu())

@router.callback_query(F.data == "adm_clean")
async def cb_clean(call: types.CallbackQuery):
    count = force_clean_system()
    await call.answer(f"🧹 System Purged: {count} Files Deleted!", show_alert=True)

@router.callback_query(F.data == "menu_backup")
async def cb_backup(call: types.CallbackQuery):
    msg = await call.message.edit_text("📦 <b>Backup Process Started...</b>\n<i>Syncing GitHub & Compressing...</i>")
    paths, status = await perform_smart_backup()
    
    if paths:
        await msg.edit_text(f"✅ <b>Backup Complete</b>\nRepo Status: {status}\n\n<i>Sending {len(paths)} parts...</i>")
        try:
            for path in paths:
                await call.message.answer_document(FSInputFile(path), caption=f"🗂 {os.path.basename(path)}")
                os.remove(path)
            await call.message.answer("<b>✅ All files sent.</b>", reply_markup=admin_menu())
        except Exception as e:
            await call.message.answer(f"⚠️ Upload Error: {e}")
    else:
        await msg.edit_text(f"❌ Backup Error: {status}", reply_markup=admin_menu())

@router.callback_query(F.data == "adm_shell")
async def cb_shell(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "💻 <b>TERMINAL SESSION</b>\nType command:", reply_markup=back_home())
    await state.set_state(AppStates.shell)

@router.message(AppStates.shell)
async def process_shell(message: types.Message):
    res = await exec_shell(message.text)
    if len(res) > 4000: res = res[:4000] + "..."
    await message.reply(f"<pre>{res}</pre>")

@router.callback_query(F.data == "adm_broadcast")
async def cb_bc(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "📢 <b>BROADCAST MODE</b>\nSend message to pin:", reply_markup=back_home())
    await state.set_state(AppStates.broadcast)

@router.message(AppStates.broadcast)
async def process_bc(message: types.Message, state: FSMContext):
    if Config.TELE_LOG_ID:
        sent = await message.copy_to(Config.TELE_LOG_ID)
        try: await bot.pin_chat_message(Config.TELE_LOG_ID, sent.message_id)
        except: pass
        await message.reply("✅ Sent!")
    await state.clear()

@router.callback_query(F.data == "adm_ban")
async def cb_ban(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, "🚫 <b>BAN USER</b>\nKirim ID User Telegram:", reply_markup=back_home())
    await state.set_state(AppStates.ban_user)

@router.message(AppStates.ban_user)
async def process_ban(message: types.Message, state: FSMContext):
    with open(Config.BANNED_FILE, "a") as f: f.write(f"{message.text}\n")
    await message.reply(f"🚫 ID {message.text} Banned!")
    await state.clear()

@router.callback_query(F.data == "adm_reboot")
async def cb_reboot(call: types.CallbackQuery):
    await call.answer("🔄 Rebooting...", show_alert=True)
    os.execv(sys.executable, ['python3'] + sys.argv)

@router.callback_query(F.data == "adm_top")
async def cb_top(call: types.CallbackQuery):
    msg = get_top_processes()
    await safe_edit(call, msg, reply_markup=admin_menu())

@router.callback_query(F.data == "adv_sec")
async def cb_sec(call: types.CallbackQuery):
    msg = security_audit()
    await safe_edit(call, msg, reply_markup=admin_menu())

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
