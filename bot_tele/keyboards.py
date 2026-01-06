from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin=False):
    buttons = [
        [
            InlineKeyboardButton(text="📺 YTDL Panel", callback_data="menu_ytdl"),
            InlineKeyboardButton(text="📊 Live Stats", callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton(text="📈 Traffic", callback_data="menu_traffic"),
            InlineKeyboardButton(text="🔍 Deep Info", callback_data="adv_info")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠 GOD MODE (ADMIN)", callback_data="menu_admin")])
        buttons.append([InlineKeyboardButton(text="🌐 Buka Website", url="https://api-ytdlpy.akadev.me")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Speedtest", callback_data="adm_speedtest"),
            InlineKeyboardButton(text="🛡️ Security", callback_data="adv_sec")
        ],
        [
            InlineKeyboardButton(text="🧹 Deep Clean", callback_data="adm_clean"),
            InlineKeyboardButton(text="📝 Notes", callback_data="adv_memo")
        ],
        [
            InlineKeyboardButton(text="💾 Backup & Sync", callback_data="menu_backup"),
            InlineKeyboardButton(text="📡 Cek IP", callback_data="adm_ip")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="💻 Shell", callback_data="adm_shell")
        ],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_home")]
    ])

# INI FUNGSI YANG HILANG SEBELUMNYA
def memo_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Note", callback_data="memo_add")],
        [InlineKeyboardButton(text="🗑 Clear All", callback_data="memo_clear")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu_admin")]
    ])

def back_home():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Kembali", callback_data="menu_home")]])
    
def ytdl_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 MP3 Audio", callback_data="dl_mode_audio"),
            InlineKeyboardButton(text="🎬 MP4 Video", callback_data="dl_mode_video")
        ],
        [InlineKeyboardButton(text="❌ Batal", callback_data="menu_home")]
    ])
