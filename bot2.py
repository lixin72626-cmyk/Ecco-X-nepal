from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot 2 is Alive!"

def run_flask():
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()
import asyncio
import time
import sqlite3
import os
import json
import re
import aiohttp
import requests
import aiosqlite

from telethon import TelegramClient, events, Button
from telethon.tl.types import ChannelParticipantsAdmins, UpdateChatParticipantAdd, ChatBannedRights
from telethon.errors import FloodWaitError, RPCError
from googletrans import Translator
from collections import defaultdict

TRACE_API = "https://api.trace.moe/search"

# ==========================
# Config (UPDATED FOR BOT 2)
# ==========================
API_ID = 34166212
API_HASH = "753aae555e6d5901145fc8685d47bffe"
BOT_TOKEN = "8638389490:AAE_OJVvLRb5TNtVqToHchVOudxR3FHvYQU"

OWNER_ID = 7681995468
BOT_OWNER_ID = 7681995468
DB_FILE = "bot_data_2.db"

# ==========================
# DATABASE & CLIENT INITIALIZATION
# ==========================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS asave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS rsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS tsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_groups (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, reply TEXT)")
conn.commit()

bot = TelegramClient("Bot_Session_2", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("✅ Bot 2: Databases created and verified successfully!")

# [Bot 1 ထဲက ကွန်မန်းစနစ်များနှင့် Function အားလုံးကို ဤနေရာတွင် အပြည့်အစုံထည့်သွင်းပါ]
# (မှတ်ချက် - RSAVE_FILE = "rsave_data_2.json" အဖြစ် သတ်မှတ်ရန် မမေ့ပါနှင့်)

RSAVE_FILE = "rsave_data_2.json"
rsave_list = []

# ... [ကျန်ရှိသော Code အားလုံး ထပ်တူဖြစ်သည်] ...

async def main():
    await bot.run_until_disconnected()

with bot:
    bot.loop.run_until_complete(main())
