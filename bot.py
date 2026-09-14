import asyncio
import aiohttp
import os
from telethon import TelegramClient, events, Button

# --- دریافت تنظیمات از محیط Railway ---
API_ID = int(os.environ.get("API_ID", 1234567))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", 123456789))
MMSI_TARGET = "750925000"

client = TelegramClient('signal_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

class State:
    current_modem_side = "ناشناخته"
    waiting_for_ack = False

state = State()

def get_best_side(heading):
    if 0 <= heading < 45 or 315 <= heading <= 360:
        return "سینه کشتی (Forward ⬆️)"
    elif 45 <= heading < 135:
        return "سمت چپ (Port 🔴)"
    elif 135 <= heading < 225:
        return "پاشنه کشتی (Aft ⬇️)"
    elif 225 <= heading < 315:
        return "سمت راست (Starboard 🟢)"

async def get_ship_heading():
    url = "https://persiangulftraffic.com/api/ships_array.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://persiangulftraffic.com/"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    for item in data:
                        if isinstance(item, list) and len(item) > 5:
                            if str(item[0]) == MMSI_TARGET:
                                return float(item[5])
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

async def check_ship_status():
    heading = await get_ship_heading()
    if heading is None: return
        
    target_side = get_best_side(heading)
    print(f"Heading: {heading} -> Best Side: {target_side}")

    if target_side != state.current_modem_side:
        if not state.waiting_for_ack:
            state.waiting_for_ack = True
            keyboard = [[Button.inline(f"✅ مودم را به {target_side} منتقل کردم", data=f"ack_{target_side}")]]
            await client.send_message(ADMIN_USER_ID, f"⚠️ **تغییر مسیر کشتی!**\nزاویه فعلی: {heading} درجه.\nلطفاً مودم را به **{target_side}** منتقل کنید.", buttons=keyboard)

    elif target_side == state.current_modem_side:
        if state.waiting_for_ack:
            state.waiting_for_ack = False
            await client.send_message(ADMIN_USER_ID, f"🔄 **اصلاح خودکار!**\nزاویه به {heading} درجه برگشت. جای فعلی مودم مناسب است.")

@client.on(events.CallbackQuery(pattern=b"ack_(.+)"))
async def handle_acknowledgement(event):
    new_side = event.data_match.group(1).decode('utf-8')
    state.current_modem_side = new_side
    state.waiting_for_ack = False
    await event.edit(f"✅ سیستم بروزرسانی شد.\nموقعیت تایید شده‌ی مودم: **{new_side}**")

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id != ADMIN_USER_ID: return
    keyboard = [
        [Button.inline("سینه کشتی (Forward)", data="set_سینه کشتی (Forward ⬆️)")],
        [Button.inline("سمت راست (Starboard)", data="set_سمت راست (Starboard 🟢)")],
        [Button.inline("سمت چپ (Port)", data="set_سمت چپ (Port 🔴)")],
        [Button.inline("پاشنه کشتی (Aft)", data="set_پاشنه کشتی (Aft ⬇️)")]
    ]
    await event.respond("📍 **سیستم ردیابی فعال شد.**\nمودم الان کجاست؟", buttons=keyboard)

@client.on(events.CallbackQuery(pattern=b"set_(.+)"))
async def set_initial_side(event):
    side = event.data_match.group(1).decode('utf-8')
    state.current_modem_side = side
    state.waiting_for_ack = False
    await event.edit(f"✅ مودم در **{side}** است. مانیتورینگ آغاز شد.")

async def main_loop():
    while True:
        if state.current_modem_side != "ناشناخته":
            await check_ship_status()
        await asyncio.sleep(600)

loop = asyncio.get_event_loop()
loop.create_task(main_loop())
client.run_until_disconnected()