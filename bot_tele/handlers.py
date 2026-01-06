import os
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
from .keyboards import main_menu, admin_menu, back_home, ytdl_menu
from .loader import bot

router = Router()

# State for Shell/Broadcast
class AdminState(StatesGroup):
    waiting_shell = State()
    waiting_broadcast = State()

# --- START ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = (message.from_user.id == Config.TELE_ADMIN_ID)
    await message.answer(f"<b>🤖 KAAI SYSTEM v7.0</b>\n\nSelamat datang, <b>{message.from_user.full_name}</b>.", reply_markup=main_menu(is_admin))

# --- MENU HANDLERS ---
@router.callback_query(F.data == "menu_home")
async def cb_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == Config.TELE_ADMIN_ID)
    await call.message.edit_text("<b>🏠 MAIN MENU</b>", reply_markup=main_menu(is_admin))

@router.callback_query(F.data == "menu_stats")
async def cb_stats(call: types.CallbackQuery):
    await call.message.edit_text(get_server_status(), reply_markup=back_home())

@router.callback_query(F.data == "menu_traffic")
async def cb_traffic(call: types.CallbackQuery):
    await call.message.edit_text(get_traffic_stats(), reply_markup=back_home())

@router.callback_query(F.data == "menu_admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id != Config.TELE_ADMIN_ID: return
    await call.message.edit_text("<b>🛠 ADMIN TOOLS</b>", reply_markup=admin_menu())

# --- ADMIN FEATURES ---
@router.callback_query(F.data == "adm_speedtest")
async def cb_speed(call: types.CallbackQuery):
    await call.message.edit_text("🚀 <b>Testing Speed...</b>")
    try:
        dl, ul, ping = await run_speedtest_task()
        await call.message.edit_text(f"<b>🚀 RESULT</b>\n\n⬇️ {dl:.2f} Mbps\n⬆️ {ul:.2f} Mbps\n📶 {ping} ms", reply_markup=admin_menu())
    except: await call.message.edit_text("❌ Failed", reply_markup=admin_menu())

@router.callback_query(F.data == "adm_ip")
async def cb_ip(call: types.CallbackQuery):
    await call.message.edit_text(get_ip_info(), reply_markup=admin_menu())

@router.callback_query(F.data == "adm_clean")
async def cb_clean(call: types.CallbackQuery):
    count = force_clean_system()
    await call.answer(f"🧹 {count} Files Removed!", show_alert=True)

@router.callback_query(F.data == "menu_backup")
async def cb_backup(call: types.CallbackQuery):
    if call.from_user.id != Config.TELE_ADMIN_ID: return
    
    msg = await call.message.edit_text("📦 <b>Backup Process...</b>\n1. Compressing Files\n2. Syncing GitHub\n3. Splitting if Large\n\n<i>Mohon tunggu...</i>")
    
    # Return sekarang berupa LIST file paths
    file_paths, status = await perform_smart_backup()
    
    if file_paths:
        await msg.edit_text(f"✅ <b>Backup Selesai!</b>\nGitHub: {status}\n\nMengirim {len(file_paths)} bagian file...")
        
        try:
            for path in file_paths:
                await call.message.answer_document(
                    FSInputFile(path), 
                    caption=f"🗂 <b>{os.path.basename(path)}</b>"
                )
                os.remove(path) # Hapus setelah kirim
            
            await call.message.answer("<b>Semua file terkirim.</b>", reply_markup=admin_menu())
        except Exception as e:
            await call.message.answer(f"❌ Gagal Kirim: {e}")
    else:
        await msg.edit_text(f"❌ <b>Backup Gagal:</b> {status}", reply_markup=admin_menu())


# --- SHELL FEATURE ---
@router.callback_query(F.data == "adm_shell")
async def cb_shell(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("💻 <b>Terminal Mode Active</b>\nKirim perintah Linux (bash) sekarang.", reply_markup=back_home())
    await state.set_state(AdminState.waiting_shell)

@router.message(AdminState.waiting_shell)
async def process_shell(message: types.Message):
    res = await exec_shell(message.text)
    await message.reply(f"<code>{res}</code>")

# --- BROADCAST FEATURE ---
@router.callback_query(F.data == "adm_broadcast")
async def cb_bc(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📢 <b>Broadcast Mode</b>\nKirim pesan untuk disiarkan ke Channel Log.", reply_markup=back_home())
    await state.set_state(AdminState.waiting_broadcast)

@router.message(AdminState.waiting_broadcast)
async def process_bc(message: types.Message):
    if Config.TELE_LOG_ID:
        await bot.send_message(Config.TELE_LOG_ID, f"<b>📢 PENGUMUMAN ADMIN</b>\n\n{message.text}")
        await message.reply("✅ Terkirim.")
    else:
        await message.reply("❌ Log Channel ID belum diset.")

# --- YTDL FEATURE ---
@router.callback_query(F.data == "menu_ytdl")
async def cb_ytdl(call: types.CallbackQuery):
    await call.message.edit_text("<b>📺 YTDL Downloader</b>\nKirim link YouTube sekarang!", reply_markup=back_home())

@router.message(F.text.regexp(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'))
async def process_ytdl_link(message: types.Message):
    # Simpan URL di state global sederhana (per user)
    global url_cache
    url_cache = getattr(globals(), 'url_cache', {})
    url_cache[message.from_user.id] = message.text
    
    await message.reply(f"🔗 <b>Link Diterima!</b>\n<code>{message.text}</code>\n\nPilih format:", reply_markup=ytdl_menu())

@router.callback_query(F.data.startswith("dl_mode_"))
async def cb_dl_start(call: types.CallbackQuery):
    url = globals().get('url_cache', {}).get(call.from_user.id)
    if not url: return await call.answer("❌ Link Expired", show_alert=True)
    
    mode = call.data.split("_")[2]
    await call.message.delete()
    msg = await call.message.answer(f"⏳ <b>Memproses {mode.upper()}...</b>")
    await process_ytdl_request(bot, call.message.chat.id, url, mode, msg.message_id)
