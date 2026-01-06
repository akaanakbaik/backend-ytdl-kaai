from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin=False):
    buttons = [
        [
            InlineKeyboardButton(text="📺 Download YTDL", callback_data="menu_ytdl"),
            InlineKeyboardButton(text="📊 Stats Live", callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton(text="📈 Traffic Data", callback_data="menu_traffic"),
            InlineKeyboardButton(text="🌐 Website", url="https://api-ytdlpy.akadev.me")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠 ADMIN PANEL", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Speedtest", callback_data="adm_speedtest"),
            InlineKeyboardButton(text="📡 Cek IP", callback_data="adm_ip")
        ],
        [
            InlineKeyboardButton(text="🧹 Cleaner", callback_data="adm_clean"),
            InlineKeyboardButton(text="💻 Terminal", callback_data="adm_shell")
        ],
        [
            InlineKeyboardButton(text="💾 Backup & Push Repo", callback_data="menu_backup"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast")
        ],
        [
            InlineKeyboardButton(text="🔙 Kembali", callback_data="menu_home")
        ]
    ])

def back_home():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_home")]])

def ytdl_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 MP3 Audio", callback_data="dl_mode_audio"),
            InlineKeyboardButton(text="🎬 MP4 Video", callback_data="dl_mode_video")
        ],
        [InlineKeyboardButton(text="❌ Batal", callback_data="menu_home")]
    ])
