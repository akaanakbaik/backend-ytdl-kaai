from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin=False):
    layout = [
        [
            InlineKeyboardButton(text="📺 YTDL Downloader", callback_data="menu_ytdl"),
            InlineKeyboardButton(text="🛠 Tools & Utils", callback_data="menu_tools")
        ],
        [
            InlineKeyboardButton(text="📊 Server Status", callback_data="menu_stats"),
            InlineKeyboardButton(text="📈 Traffic Data", callback_data="menu_traffic")
        ],
        [InlineKeyboardButton(text="🌐 Visit Website", url="https://kaai.vercel.app")]
    ]
    
    if is_admin:
        layout.insert(0, [InlineKeyboardButton(text="🔐 ADMIN DASHBOARD", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=layout)

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Speedtest", callback_data="adm_speedtest"),
            InlineKeyboardButton(text="🛡️ Security", callback_data="adv_sec")
        ],
        [
            InlineKeyboardButton(text="🧹 Clean System", callback_data="adm_clean"),
            InlineKeyboardButton(text="📝 Notes", callback_data="adv_memo")
        ],
        [
            InlineKeyboardButton(text="🔥 Processes", callback_data="adm_top"),
            InlineKeyboardButton(text="📡 Check IP", callback_data="adm_ip")
        ],
        [
            InlineKeyboardButton(text="💾 Backup", callback_data="menu_backup"),
            InlineKeyboardButton(text="🚫 Ban User", callback_data="adm_ban")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="💻 Terminal", callback_data="adm_shell")
        ],
        [
            InlineKeyboardButton(text="🔄 Reboot System", callback_data="adm_reboot")
        ],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="menu_home")]
    ])

def tools_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔎 WhoIs Lookup", callback_data="feat_whois"),
            InlineKeyboardButton(text="📂 File Manager", callback_data="feat_files")
        ],
        [
            InlineKeyboardButton(text="🌡️ CPU Temp", callback_data="feat_temp"),
            InlineKeyboardButton(text="🎲 Random Quote", callback_data="adv_info")
        ],
        [
            InlineKeyboardButton(text="📱 QR Generator", callback_data="tool_qr"),
            InlineKeyboardButton(text="🔑 Pass Generator", callback_data="tool_pass")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu_home")]
    ])

def memo_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Note", callback_data="memo_add"), InlineKeyboardButton(text="🗑 Clear All", callback_data="memo_clear")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu_admin")]
    ])

def back_home():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Back to Home", callback_data="menu_home")]
    ])

def ytdl_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 MP3 Audio", callback_data="dl_mode_audio"),
            InlineKeyboardButton(text="🎬 MP4 Video", callback_data="dl_mode_video")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="menu_home")]
    ])
