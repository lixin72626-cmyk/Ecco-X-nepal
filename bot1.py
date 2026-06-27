import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Render အကြိုက် Port ဖွင့်ပေးမယ့် Server အတု ဆောက်ခြင်း
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_dummy_server():
    # Render က ပေးတဲ့ PORT ကို ယူမယ်၊ မရှိရင် 10000 ကို သုံးမယ်
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

# 2. သင့်ရဲ့ Bot ကုဒ်တွေ မပွင့်ခင် ဒါကို Background မှာ အရင် Run ခိုင်းထားမယ်
Thread(target=run_dummy_server, daemon=True).start()

# =========================================================
# ဒီအောက်ကနေစပြီး ဘရိုရဲ့ မူလ Bot ကုဒ်အဟောင်းတွေကို ဆက်ထားလိုက်ပါ
# ဥပမာ - import telebot သို့မဟုတ် bot.polling() စတာတွေ...
# =========================================================
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
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import FloodWaitError
from telethon.utils import get_display_name
from datetime import datetime
from telethon.tl.types import UpdateChatParticipantAdd
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.custom.message import Message
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from datetime import date
from telethon.tl.types import ChannelParticipant, User, Chat
from telethon.tl.types import ChatBannedRights
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
from googletrans import Translator
from telethon.tl.types import InputMessagesFilterVideo
from telethon.tl.types import PeerUser
from datetime import timedelta
from collections import defaultdict

# ==========================
# TRACE_API URL သတ်မှတ်
# ==========================
TRACE_API = "https://api.trace.moe/search"

# ==========================
# Config
# ==========================
API_ID = 34166212
API_HASH = "753aae555e6d5901145fc8685d47bffe"
BOT_TOKEN = "8959700806:AAGfxZ0OX9JJ9Q-SPm1xSxeZTYHzV70aTac"

OWNER_ID = 7681995468
BOT_OWNER_ID = 7681995468
DB_FILE = "bot_data.db"

# ==========================
# MAIN BOT DATABASE
# ==========================
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

# Tables Setup
cursor.execute("CREATE TABLE IF NOT EXISTS asave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS rsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS tsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_groups (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, reply TEXT)")
conn.commit()

# Protected Users Database (Added check_same_thread=False)
protected_conn = sqlite3.connect("protected.db", check_same_thread=False)
protected_cursor = protected_conn.cursor()
protected_cursor.execute("CREATE TABLE IF NOT EXISTS protected_users (user_id INTEGER PRIMARY KEY)")
protected_conn.commit()

protected_cursor.execute("SELECT user_id FROM protected_users")
protected_users = set(row[0] for row in protected_cursor.fetchall())

# ==========================
# TELETHON CLIENT
# ==========================
bot = TelegramClient("Bot10", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("✅ All databases created and verified successfully!")

# Helper functions
async def remember_group(chat_id):
    cursor.execute("INSERT OR IGNORE INTO active_groups (chat_id) VALUES (?)", (chat_id,))
    conn.commit()

def get_active_groups():
    rows = cursor.execute("SELECT chat_id FROM active_groups").fetchall()
    return [r[0] for r in rows]

# Typing Wrappers
original_send_message = bot.send_message
original_send_file = bot.send_file

async def send_message_with_typing(chat_id, *args, **kwargs):
    try:
        async with bot.action(chat_id, 'typing'):
            await asyncio.sleep(0.5)
    except:
        pass
    return await original_send_message(chat_id, *args, **kwargs)

async def send_file_with_typing(chat_id, *args, **kwargs):
    try:
        async with bot.action(chat_id, 'typing'):
            await asyncio.sleep(0.5)
    except:
        pass
    return await original_send_file(chat_id, *args, **kwargs)

bot.send_message = send_message_with_typing
bot.send_file = send_file_with_typing

# Permission Checks
def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    cursor.execute("SELECT user_id FROM bot_admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def is_member(user_id):
    return not (is_owner(user_id) or is_admin(user_id))

def is_bot_admin(user_id):
    cursor.execute("SELECT user_id FROM bot_admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def has_permission(user_id):
    return is_owner(user_id) or is_admin(user_id)

# Global States
GROUPS = set()
troll_targets = {}
delete_targets = {}
att_targets = {}
attack_speed = 1
translator = Translator()
TRUSTED_BOTS = [OWNER_ID]
calling_tasks = {}
stop_flags = {}
reply_targets = {}
bot_id = None
current_index = 0
group_speeds = {}
attack_tasks = {}
permitted_users = set()
user_messages = defaultdict(list)
time_users = {}
notified_bots = {}
ban_tracker = {}
alert_lock = {}
ctc_active = False
user1_id = None
user2_id = None

RSAVE_FILE = "rsave_data.json"
rsave_list = []
PAGE_SIZE = 50
LINK_WORDS = ["@", "bio", "ဘိုင်o", "ဘိုင်အို", "http://", "https://", "t.me/", "telegram.me"]
BAN_THRESHOLD = 10
BAN_DELAY = 0.1

def save_rsave():
    with open(RSAVE_FILE, "w") as f:
        json.dump(rsave_list, f)

def load_rsave():
    global rsave_list
    if os.path.exists(RSAVE_FILE):
        with open(RSAVE_FILE, "r") as f:
            rsave_list = json.load(f)
    else:
        rsave_list = []

# ==========================
# COMMAND HANDLERS
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/start$"))
async def start_command(event):
    user = await bot.get_entity(event.sender_id)
    username = f"@{user.username}" if user.username else "No Username"
    msg = f"👋 မင်္ဂလာပါ {user.first_name}!\n\nUsername: {username}\nဒီ bot နဲ့ သုံးနိုင်တဲ့ commands အားလုံးကို (အကူအညီ) စမ်းကြည့်နိုင်ပါတယ်:\n"
    await event.reply(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^အရှိန် (.+)"))
async def set_speed(event):
    if not has_permission(event.sender_id):
        return await event.reply("မင်းကသခင်အီကိုကို့မလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    chat_id = event.chat_id
    try:
        speed = float(event.pattern_match.group(1))
        if speed < 0: speed = 0
        group_speeds[chat_id] = speed
        await event.reply(f"အမြန်နှုန်းကို {speed} စက္ကန့်သို့ချိန်ညှိလိုက်ပါပီ (ဒီ Group အတွက်ပဲ)")
    except:
        await event.reply("Invalid number.")

@bot.on(events.NewMessage(pattern=r"(?i)^သတ်ပလိုက်(?:\s|$)"))
async def attack_user(event):
    if not has_permission(event.sender_id):
        return await event.reply("မင်းကသခင်အီကို့ကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    chat_id = event.chat_id
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
    else:
        args = event.message.text.split()
        if len(args) < 2:
            return await event.reply("မျိုးမစစ်တွေကိုနှိမ်နှင်းစေချင်ရင်မိန့်ကိုမှန်ကန်စွာအသုံးပြုပါ (သတ်ပလိုက်) (Reply)")
        try:
            entity = await bot.get_entity(args[1])
            target_id = entity.id
        except:
            return await event.reply("မင်းပြောတဲ့ခွေးမျိုးလေးကိုရှာမတွေ့သေးပါ Try.")

    if is_owner(target_id):
        return await event.reply("သခင်အီကို့ကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    texts = cursor.execute("SELECT text FROM asave ORDER BY id ASC").fetchall()
    if not texts:
        return await event.reply("နှိမ်နှင်းရမဲ့စာသားတွေကိုသိမ်းဆည်းထားချင်းမရှိသောကြေင့်ပြုလုပ်၍မရပါ")

    if chat_id not in attack_tasks:
        attack_tasks[chat_id] = {}
    if target_id in attack_tasks[chat_id]:
        return await event.reply("Already attacking this user.")

    user = await bot.get_entity(target_id)

    async def spam():
        index = 0
        end_time = asyncio.get_event_loop().time() + (24 * 60 * 60)
        try:
            while asyncio.get_event_loop().time() < end_time:
                if target_id not in attack_tasks.get(chat_id, {}): break
                text = texts[index % len(texts)][0]
                message = f"<a href='tg://user?id={user.id}'>{user.first_name}</a> {text}"
                try:
                    await bot.send_message(chat_id, message, parse_mode="html")
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                    continue
                index += 1
                speed = group_speeds.get(chat_id, 1.0)
                await asyncio.sleep(speed)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(spam())
    attack_tasks[chat_id][target_id] = task
    await event.reply("မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")

@bot.on(events.NewMessage(pattern=r"(?i)^ရပ်တော့"))
async def stop_attack(event):
    if not has_permission(event.sender_id):
        return await event.reply("သခင်အီကို့က ခွင့်ပြုချက်မရထားပါ")
    chat_id = event.chat_id
    if chat_id in attack_tasks:
        for task in attack_tasks[chat_id].values():
            task.cancel()
        attack_tasks[chat_id].clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

@bot.on(events.NewMessage(pattern=r"(?i)^/rsave (.+)"))
async def save_r(event):
    if not is_owner(event.sender_id): return
    text = event.pattern_match.group(1)
    rsave_list.append(text)
    save_rsave()
    await event.reply(f"Saved ✅\nTotal Saved: {len(rsave_list)}")

async def show_rsave_page(event, page):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_rows = rsave_list[start:end]
    if not current_rows:
        await event.answer("No more pages.", alert=True)
        return
    msg_lines = [f"{i+1+start}. {msg}" for i, msg in enumerate(current_rows)]
    msg_text = "<blockquote>🔥 Rsave List 🔥\n\n" + "\n".join(msg_lines) + "</blockquote>"
    buttons = []
    if page > 0: buttons.append(Button.inline("⬅ Previous", data=f"rsave_prev_{page-1}".encode()))
    if end < len(rsave_list): buttons.append(Button.inline("Next ➡", data=f"rsave_next_{page+1}".encode()))
    await event.reply(msg_text, buttons=buttons, parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^/rlist$"))
async def list_r(event):
    if not is_owner(event.sender_id): return
    if not rsave_list:
        await event.reply("<blockquote>⚠️ Rsave list is empty.</blockquote>", parse_mode="html")
        return
    await show_rsave_page(event, 0)

@bot.on(events.CallbackQuery(pattern=b"rsave_(prev|next)_(\\d+)"))
async def paginate_rsave(event):
    action, page = [x.decode() if isinstance(x, bytes) else x for x in event.pattern_match.groups()]
    page = int(page)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_rows = rsave_list[start:end]
    if not current_rows:
        await event.answer("No more pages.", alert=True)
        return
    msg_lines = [f"{i+1+start}. {msg}" for i, msg in enumerate(current_rows)]
    msg_text = "<blockquote>🔥 Rsave List 🔥\n\n" + "\n".join(msg_lines) + "</blockquote>"
    buttons = []
    if page > 0: buttons.append(Button.inline("⬅ Previous", data=f"rsave_prev_{page-1}".encode()))
    if end < len(rsave_list): buttons.append(Button.inline("Next ➡", data=f"rsave_next_{page+1}".encode()))
    await event.edit(msg_text, buttons=buttons, parse_mode="html")
    await event.answer()

@bot.on(events.NewMessage(pattern=r"(?i)^လွတ်အောင်ပြေး$"))
async def set_reply(event):
    global bot_id
    if not has_permission(event.sender_id): return
    if not event.is_reply: return await event.reply("Reply to target user.")
    reply_msg = await event.get_reply_message()
    if bot_id is None: bot_id = (await bot.get_me()).id
    if reply_msg.sender_id == bot_id or is_owner(reply_msg.sender_id): return

    target_id = reply_msg.sender_id
    target_entity = await bot.get_entity(target_id)

    if target_id not in reply_targets:
        reply_targets[target_id] = {
            "expire": time.time() + 86400,
            "base_msg_id": reply_msg.id,
            "chat_id": event.chat_id,
            "last_bot_msg": None,
            "mode": "reply",
            "username": target_entity.username,
            "index": 0
        }
    await event.reply("မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")

@bot.on(events.NewMessage(pattern=r"(?i)^ပေးနားလိုက်"))
async def unset_reply(event):
    if not has_permission(event.sender_id): return
    chat_id = event.chat_id
    if not event.is_reply:
        found = False
        for uid in list(reply_targets.keys()):
            if reply_targets[uid]["chat_id"] == chat_id:
                del reply_targets[uid]
                found = True
        if not found: return await event.reply("ဘယ်လိုခွေးမျိုး အမျိုးစားများကိုမှနှိမ်နှင်းထားချင်းမရှိသေးပါ")
        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")
    
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    if target_id in reply_targets and reply_targets[target_id]["chat_id"] == chat_id:
        del reply_targets[target_id]
        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")
    await event.reply("This user not active.")

@bot.on(events.NewMessage)
async def track_user(event):
    global bot_id
    if bot_id is None: bot_id = (await bot.get_me()).id
    if event.sender_id == bot_id: return
    if event.sender_id in reply_targets:
        reply_targets[event.sender_id]["base_msg_id"] = event.id
        reply_targets[event.sender_id]["mode"] = "reply"

@bot.on(events.MessageDeleted)
async def track_delete(event):
    for uid, data in reply_targets.items():
        if data["base_msg_id"] in event.deleted_ids:
            data["base_msg_id"] = None
            data["mode"] = "mention"
        if data["last_bot_msg"] in event.deleted_ids:
            data["mode"] = "mention"

async def reply_engine():
    while True:
        await asyncio.sleep(1)
        if not rsave_list: continue
        for uid in list(reply_targets.keys()):
            data = reply_targets.get(uid)
            if not data: continue
            if time.time() > data["expire"]:
                del reply_targets[uid]
                continue
            text = rsave_list[data["index"] % len(rsave_list)]
            data["index"] += 1
            try:
                if data["last_bot_msg"]:
                    try: await bot.delete_messages(data["chat_id"], data["last_bot_msg"])
                    except: pass
                if data["mode"] == "reply" and data["base_msg_id"]:
                    bot_msg = await bot.send_message(data["chat_id"], text, reply_to=data["base_msg_id"])
                else:
                    if data["username"]:
                        bot_msg = await bot.send_message(data["chat_id"], f"@{data['username']} {text}")
                    else:
                        bot_msg = await bot.send_message(data["chat_id"], f"<a href='tg://user?id={uid}'>User</a> {text}", parse_mode="html")
                data["last_bot_msg"] = bot_msg.id
            except Exception as e:
                print("Reply Engine Error:", e)

@bot.on(events.NewMessage(pattern=r"(?i)^ရိုက်သတ်"))
async def set_troll(event):
    if not has_permission(event.sender_id):
        return await event.reply("မင်းကသခင်အီကို့ကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    if not event.is_reply:
        return await event.reply("❌အသုံးပြုပုံမှားယွင်းနေပါတယ် (ရိုက်သတ်) <reply_user> .....။")
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    if is_owner(target_id):
        return await event.reply("သခင်အီကို့ကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")
    troll_targets[target_id] = {"index": 0}
    await event.reply("တိုက်ခိုက်မှုကိုစတင်လိုက်ပါပီ ရပ်တန့်လိုပါက (ခွင့်လွတ်လိုက်) <reply> ....။")

@bot.on(events.NewMessage(pattern=r"(?i)^ခွင့်လွတ်လိုက်"))
async def unset_troll(event):
    if not has_permission(event.sender_id):
        return await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")
    troll_targets.clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

@bot.on(events.NewMessage(incoming=True))
async def monitor_messages(event):
    if event.sender_id is None or is_owner(event.sender_id): return
    if event.sender_id in troll_targets:
        texts = cursor.execute("SELECT text FROM tsave ORDER BY id ASC").fetchall()
        if texts:
            data = troll_targets[event.sender_id]
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1
            try: await event.reply(text)
            except: pass
            await asyncio.sleep(attack_speed)

@bot.on(events.NewMessage(pattern=r"(?i)^စာဖျက်လိုက်"))
async def set_delete(event):
    if not has_permission(event.sender_id): return await event.reply("❌ Permission denied.")
    if not event.is_reply: return await event.reply("⚠️ Reply to target user to activate delete mode.")
    reply_msg = await event.get_reply_message()
    if is_owner(reply_msg.sender_id): return await event.reply("⚠️ Cannot target the owner.")
    delete_targets[reply_msg.sender_id] = event.chat_id
    await event.reply("✅ Delete mode activated for this user.")

@bot.on(events.NewMessage(pattern=r"(?i)^စာပေးရေးလိုက်(?:\s+(\d+|all))?"))
async def unset_delete(event):
    if not has_permission(event.sender_id): return await event.reply("❌ Permission denied.")
    target_id = None
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg: target_id = reply_msg.sender_id
    else:
        arg = event.pattern_match.group(1)
        if arg:
            if arg.lower() == "all":
                delete_targets.clear()
                return await event.reply("✅ All delete targets removed.")
            else:
                try: target_id = int(arg)
                except: return await event.reply("⚠️ Invalid user ID.")
    if target_id:
        if target_id in delete_targets:
            del delete_targets[target_id]
            await event.reply(f"✅ Delete mode removed for user {target_id}.")
        else:
            await event.reply("⚠️ This user is not in delete mode.")
    else:
        await event.reply("⚠️ Reply to a user or provide user ID to remove delete mode.")

@bot.on(events.NewMessage(incoming=True))
async def auto_delete_monitor(event):
    if event.sender_id is None or is_owner(event.sender_id): return
    chat_id = event.chat_id
    target_ids = list(delete_targets.keys())
    
    # Auto-delete matching conditions
    if event.sender_id in target_ids:
        try: await bot.delete_messages(chat_id, event.id)
        except: pass
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id in delete_targets:
            try: await bot.delete_messages(chat_id, event.id)
            except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^ထိန်းချုပ်လိုက်$"))
async def set_att(event):
    if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
        return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")
    if not event.is_reply: return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")
    reply_msg = await event.get_reply_message()
    if is_owner(reply_msg.sender_id): return await event.reply("⚠️ Owner ကို mute / control လုပ်လို့မရပါ။")
    att_targets[reply_msg.sender_id] = event.chat_id
    await event.reply("✅ User ကို 10s Auto Mute System ထဲထည့်လိုက်ပါပြီ။")

@bot.on(events.NewMessage(pattern=r"(?i)^လွတ်ပေးလိုက်$"))
async def unset_att(event):
    if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
        return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")
    if not event.is_reply: return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")
    reply_msg = await event.get_reply_message()
    if reply_msg.sender_id in att_targets:
        del att_targets[reply_msg.sender_id]
        await event.reply("✅ User ကို Control System မှ ဖယ်ရှားလိုက်ပါပြီ။")
    else:
        await event.reply("⚠️ ဒီ User Control List ထဲမှာမရှိပါ။")

@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):
    user_id = event.sender_id
    chat_id = event.chat_id
    if user_id not in att_targets or att_targets[user_id] != chat_id: return
    try:
        await bot.edit_permissions(chat_id, user_id, send_messages=False)
        await asyncio.sleep(10)
        if user_id in att_targets:
            await bot.edit_permissions(chat_id, user_id, send_messages=True)
    except Exception as e:
        print("AUTO CONTROL ERROR:", e)

@bot.on(events.NewMessage(pattern=r"(?i)^အကုန်ခေါ်(?:@\w+)? (.+)"))
async def start_calling(event):
    chat_id = event.chat_id
    text = event.pattern_match.group(1)
    if not has_permission(event.sender_id): return await event.reply("❌ Permission denied")
    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        return await event.reply("⚠️ Calling already running in this group.")
    stop_flags[chat_id] = False
    calling_tasks[chat_id] = asyncio.create_task(calling_engine(chat_id, text))
    await event.reply("🔊🔊‌ခေါ်ဆိုမှုကိုစတင်လိုက်ပါပီ (မခေါ်နဲ့တော့) ဖြင့်ရပ်တန့်လို့ရသည်....။")

@bot.on(events.NewMessage(pattern=r"မခေါ်နဲ့တော့$"))
async def stop_call(event):
    chat_id = event.chat_id
    if not has_permission(event.sender_id): return await event.reply("❌ Permission denied")
    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        stop_flags[chat_id] = True
        await calling_tasks[chat_id]
        await event.reply("🔇🔇ခေါ်ဆိုမှုကိုရပ်တန့်လိုက်ပါပီ...။")
    else:
        await event.reply("⚠️ No calling task running in this group.")

async def calling_engine(chat_id, text):
    members = []
    async for user in bot.iter_participants(chat_id): members.append(user)
    batch_size = 5
    for i in range(0, len(members), batch_size):
        if stop_flags.get(chat_id): break
        batch = members[i:i + batch_size]
        mentions = [f"<a href='tg://user?id={u.id}'>{u.first_name}</a>" for u in batch]
        try: await bot.send_message(chat_id, " ".join(mentions) + "\n\n" + text, parse_mode="html")
        except: pass
        await asyncio.sleep(2)
    calling_tasks.pop(chat_id, None)

@bot.on(events.NewMessage(pattern=r"/Setadd"))
async def setadd_user(event):
    if event.sender_id != OWNER_ID: return await event.reply("❌ Only owner can use /Setadd")
    if not event.is_reply: return await event.reply("❌ Reply to user to give permission")
    reply = await event.get_reply_message()
    permitted_users.add(reply.sender_id)
    await event.reply("✅ One-time permission granted")

@bot.on(events.NewMessage(pattern=r"/Unset"))
async def unset_user(event):
    if event.sender_id != OWNER_ID: return await event.reply("❌ Only owner can use /Unset")
    if not event.is_reply: return await event.reply("❌ Reply to user to remove permission")
    reply = await event.get_reply_message()
    permitted_users.discard(reply.sender_id)
    await event.reply("✅ Permission removed")

@bot.on(events.NewMessage(pattern=r"/Asave (.+)"))
async def save_attack_cmd(event):
    if event.sender_id == OWNER_ID or event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Attack text saved")
    await event.reply("❌ Permission denied")

@bot.on(events.NewMessage(pattern=r"/Tsave (.+)"))
async def save_troll_cmd(event):
    if event.sender_id == OWNER_ID or event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Troll text saved")
    await event.reply("❌ Permission denied")

async def show_page(event, rows, page, title_prefix):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_rows = rows[start:end]
    if not current_rows:
        await event.answer("No more pages.", alert=True)
        return
    msg_lines = [f"{r[0]}: {r[1]}" for r in current_rows]
    msg_text = f"<blockquote>{title_prefix}\n\n" + "\n".join(msg_lines) + "</blockquote>"
    buttons = []
    if page > 0: buttons.append(Button.inline("Previous", data=f"{title_prefix}_prev_{page-1}".encode()))
    if end < len(rows): buttons.append(Button.inline("Next", data=f"{title_prefix}_next_{page+1}".encode()))
    await event.reply(msg_text, buttons=buttons, parse_mode="html")

@bot.on(events.NewMessage(pattern=r"/Alist"))
async def list_attack(event):
    rows = cursor.execute("SELECT id, text FROM asave").fetchall()
    if not rows: return await event.reply("<blockquote>No attack texts saved.</blockquote>", parse_mode="html")
    await show_page(event, rows, 0, "Attack List")

@bot.on(events.NewMessage(pattern=r"/Tlist"))
async def list_troll(event):
    rows = cursor.execute("SELECT id, text FROM tsave").fetchall()
    if not rows: return await event.reply("<blockquote>No troll texts saved.</blockquote>", parse_mode="html")
    await show_page(event, rows, 0, "Troll List")

@bot.on(events.CallbackQuery(pattern=b"(Attack List|Troll List)_(prev|next)_(\\d+)"))
async def paginate(event):
    title, action, page = [x.decode() if isinstance(x, bytes) else x for x in event.pattern_match.groups()]
    page = int(page)
    rows = cursor.execute("SELECT id, text FROM asave" if "Attack" in title else "SELECT id, text FROM tsave").fetchall()
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_rows = rows[start:end]
    if not current_rows: return await event.answer("No more pages.", alert=True)
    msg_lines = [f"{r[0]}: {r[1]}" for r in current_rows]
    msg_text = f"<blockquote>{title}\n\n" + "\n".join(msg_lines) + "</blockquote>"
    buttons = []
    if page > 0: buttons.append(Button.inline("Previous", data=f"{title}_prev_{page-1}".encode()))
    if end < len(rows): buttons.append(Button.inline("Next", data=f"{title}_next_{page+1}".encode()))
    await event.edit(msg_text, buttons=buttons, parse_mode="html")
    await event.answer()

@bot.on(events.NewMessage(pattern=r"(?i)^ဖြန့်လိုက်$"))
async def sends_command(event):
    if event.sender_id != OWNER_ID: return await event.reply("❌ Owner Only.")
    if not event.is_reply: return await event.reply("Reply to a message to forward.")
    reply_msg = await event.get_reply_message()
    cursor.execute("SELECT chat_id FROM active_groups")
    groups = [row[0] for row in cursor.fetchall()]
    shared, failed = 0, 0
    status_msg = await event.reply("📤 Forwarding started...")
    for group_id in groups:
        try:
            await bot.forward_messages(group_id, reply_msg)
            shared += 1
            await asyncio.sleep(1)
        except:
            failed += 1
    await status_msg.edit(f"✅ Forwarding completed!\n📦 Forwarded to: {shared} groups\n❌ Failed: {failed} groups")

@bot.on(events.NewMessage)
async def track_groups_auto(event):
    chat = await event.get_chat()
    if not any([getattr(chat, "megagroup", False), getattr(chat, "gigagroup", False), getattr(chat, "broadcast", False)]): return
    cursor.execute("SELECT chat_id FROM active_groups WHERE chat_id = ?", (chat.id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO active_groups(chat_id) VALUES(?)", (chat.id,))
        conn.commit()

@bot.on(events.NewMessage(pattern=r"(?i)^groupid"))
async def chat_info(event):
    chat = await event.get_chat()
    admins = await bot.get_participants(chat, filter=ChannelParticipantsAdmins)
    admin_text = "".join([f"{i}. {a.first_name}\n   {a.id}\n" for i, a in enumerate(admins, start=1)])
    gid = f"-100{chat.id}" if any([getattr(chat, 'megagroup', False), getattr(chat, 'broadcast', False)]) else str(chat.id)
    await event.reply(f"<blockquote>Group Name: {chat.title}\nGroup ID: {gid}\n\nAdmins:\n{admin_text}</blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"^သူ့စောက်ကြောင်း(?: (.+))?$"))
async def user_id_view(event):
    arg = event.pattern_match.group(1)
    try:
        if event.is_reply: reply = await event.get_reply_message(); user = await bot.get_entity(reply.sender_id)
        elif arg: user = await bot.get_entity(arg)
        else: user = await bot.get_entity(event.sender_id)
        username = f"@{user.username}" if user.username else "No Username"
        await event.reply(f"<blockquote>Name : {user.first_name}\nUser ID : {user.id}\nUsername : {username}</blockquote>", parse_mode="html")
    except:
        await event.reply("User ရှာမတွေ့ပါ။")

@bot.on(events.NewMessage(pattern=r"/Botadmlist"))
async def list_admins(event):
    rows = cursor.execute("SELECT user_id FROM bot_admins").fetchall()
    if not rows: return await event.reply("<blockquote>⚠️ No Bot Admins assigned.</blockquote>", parse_mode="html")
    msg_lines = []
    for r in rows:
        try: u = await bot.get_entity(r[0]); msg_lines.append(f"{u.first_name} — {u.id}")
        except: msg_lines.append(f"Unknown — {r[0]}")
    await event.reply("<blockquote>👮 Bot Admins:\n\n" + "\n".join(msg_lines) + "</blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^မှတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def add_admin(event):
    if not is_owner(event.sender_id): return
    uid = event.pattern_match.group(2)
    if event.is_reply: reply = await event.get_reply_message(); uid = reply.sender_id
    elif uid: uid = int(uid)
    else: return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")
    cursor.execute("INSERT OR IGNORE INTO bot_admins(user_id) VALUES(?)", (uid,))
    conn.commit()
    await event.reply(f"✅ User `{uid}` ကို Bot Admin အဖြစ်ထည့်လိုက်ပါပြီ")

@bot.on(events.NewMessage(pattern=r"(?i)^ဖြုတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def remove_admin(event):
    if not is_owner(event.sender_id): return
    uid = event.pattern_match.group(2)
    if event.is_reply: reply = await event.get_reply_message(); uid = reply.sender_id
    elif uid: uid = int(uid)
    else: return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")
    cursor.execute("DELETE FROM bot_admins WHERE user_id=?", (uid,))
    conn.commit()
    await event.reply(f"❌ User `{uid}` ကို Bot Admin မှ ဖယ်ရှားလိုက်ပါပြီ")

@bot.on(events.ChatAction)
async def bot_added(event):
    if event.user_added:
        me = await bot.get_me()
        if event.user_id == me.id and event.action_message:
            adder = await bot.get_entity(event.action_message.from_id)
            await event.reply(f"<blockquote>ကောင်းကင်စီးနှင်းသူလို့လူသိများတဲ့ {me.first_name} ရောက်ရှိလာပါပီ <a href='tg://user?id={adder.id}'>{adder.first_name}</a> တေးသံလိုညိမ့်‌ညောင်းတဲ့တိုက်ခိုက်မှုကိုစတင်ရန် (သတ်ပလိုက်))Reply Or Uuser အသုံးပြုပါ.....။ </blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^အကူအညီ$"))
async def helps_command(event):
    help_text = "<blockquote>BOT COMMANDS GUIDE (မြန်မာလို)\n════════════════════════\n\n1. Attack & Spam Commands\n• သတ်ပလိုက်, ရပ်တော့, အရှိန် <time>\n\n2. Auto Reply System\n• လွတ်အောင်ပြေး, ပေးနားလိုက်\n\n3. Troll System\n• ရိုက်သတ်, ခွင့်လွတ်လိုက်\n\n4. Message Control\n• စာဖျက်လိုက်, စာပေးရေးလိုက်\n\n5. Group Functions\n• အကုန်ခေါ်, မခေါ်နဲ့တော့\n\n6. CTC Reply System\n• စလိုက် <id1> <id2>, တော်တော့\n\n7. Moderation\n• /ban, /unban, /mute, /unmute\n\n8. Filter\n• /filter <trigger> <reply>\n\n9. Control\n• ထိန်းချုပ်လိုက်, လွတ်ပေးလိုက်\n\n10. Extra\n• ဘာသာပြန်မယ်, /report, သူ့စောက်ကြောင်း, groupid</blockquote>"
    await event.reply(help_text, parse_mode="html")

LANGUAGES = {"English": "en", "Japanese": "ja", "Myanmar": "my"} # Simplified mapping for example

@bot.on(events.NewMessage(pattern=r'^ဘာသာပြန်မယ်$'))
async def translate_cmd(event):
    if not event.is_reply: return await event.reply("Reply ထောက်ပြီး သုံးပါ")
    reply_msg = await event.get_reply_message()
    if not reply_msg.text: return await event.reply("Text မရှိပါ")
    user_state[event.sender_id] = {"original": reply_msg.text, "waiting_language": True}
    await event.reply("🌐 ဘာသာစကားနာမည် ရိုက်ပါ (English / Japanese / Myanmar)")

@bot.on(events.NewMessage(incoming=True))
async def language_input(event):
    uid = event.sender_id
    if uid not in user_state or not user_state[uid].get("waiting_language"): return
    lang_name = event.text.strip()
    if lang_name not in LANGUAGES: return await event.reply("❌ Language မမှန်ပါ။")
    
    user_state[uid]["waiting_language"] = False
    translated = translator.translate(user_state[uid]["original"], dest=LANGUAGES[lang_name]).text
    await event.reply(f"<blockquote>Translated ({lang_name}):\n{translated}</blockquote>", parse_mode="html")

# Ban / Mute Helpers
def parse_time(text):
    if not text: return 600
    match = re.match(r"(\d+)([mhd])", text.lower())
    if not match: return 600
    num, unit = match.groups()
    num = int(num)
    return num * 60 if unit == "m" else num * 3600 if unit == "h" else num * 86400

@bot.on(events.NewMessage(pattern=r"(?i)^/ban$"))
async def ban_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return
    if not event.is_reply: return await event.reply("⚠️ Reply to user")
    reply = await event.get_reply_message()
    if is_owner(reply.sender_id): return
    try:
        await bot.edit_permissions(event.chat_id, reply.sender_id, view_messages=False)
        await event.reply("🚫 User banned successfully.")
    except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^/unban$"))
async def unban_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return
    if not event.is_reply: return
    reply = await event.get_reply_message()
    try:
        await bot.edit_permissions(event.chat_id, reply.sender_id, view_messages=True, send_messages=True)
        await event.reply("✅ User unbanned successfully.")
    except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^/mute(?:\s+(.+))?$"))
async def mute_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return
    if not event.is_reply: return
    reply = await event.get_reply_message()
    if is_owner(reply.sender_id): return
    text = event.pattern_match.group(1)
    secs = parse_time(text)
    try:
        await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=False)
        await event.reply(f"🔇 User muted for {text if text else '10m'}")
        if secs > 0:
            await asyncio.sleep(secs)
            await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
    except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^/unmute$"))
async def unmute_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return
    if not event.is_reply: return
    reply = await event.get_reply_message()
    try:
        await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
        await event.reply("🔊 User manually unmuted")
    except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^/filter"))
async def add_filter(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return
    args = event.raw_text.split(maxsplit=2)
    if len(args) < 3: return
    cursor.execute("INSERT INTO filters (chat_id, trigger, reply) VALUES (?, ?, ?)", (event.chat_id, args[1].lower(), args[2]))
    conn.commit()
    await event.reply(f"✅ Filter added")

@bot.on(events.NewMessage(incoming=True))
async def filter_reply(event):
    if event.raw_text is None: return
    cursor.execute("SELECT trigger, reply FROM filters WHERE chat_id=?", (event.chat_id,))
    for trigger, reply in cursor.fetchall():
        if event.raw_text.lower() == trigger:
            await event.reply(reply)
            break

@bot.on(events.ChatAction)
async def auto_owner_alert(event):
    if event.user_kicked:
        chat_id = event.chat_id
        banned_by = event.action_message.sender
        me = await bot.get_me()
        if banned_by.id in [me.id, OWNER_ID]: return
        try:
            participants = await bot.get_participants(chat_id, filter=ChannelParticipantsAdmins)
            owner = next((p for p in participants if getattr(p.participant, "creator", False)), None)
            if owner:
                await bot.send_message(owner.id, f"<blockquote>သတိပေးချက်: {banned_by.first_name} က Member တွေကို Ban နေပါတယ်။</blockquote>", parse_mode="html")
        except: pass

@bot.on(events.NewMessage(pattern=r'^စလိုက်'))
async def start_ctc(event):
    global ctc_active, user1_id, user2_id
    if not has_permission(event.sender_id): return
    try:
        parts = event.raw_text.split()
        user1_id, user2_id = int(parts[1]), int(parts[2])
        ctc_active = True
        await event.reply("Trolling Mode Activated")
    except: pass

@bot.on(events.NewMessage(pattern=r'^တော်တော့'))
async def stop_ctc(event):
    global ctc_active
    if not has_permission(event.sender_id): return
    ctc_active = False
    await event.reply("Trolling Mode Deactivated.")

@bot.on(events.NewMessage(incoming=True))
async def handle_ctc_messages(event):
    if not ctc_active or event.sender_id not in (user1_id, user2_id): return
    tid = user2_id if event.sender_id == user1_id else user1_id
    try:
        target = await bot.get_entity(tid)
        await event.reply(f"{event.raw_text} <a href='tg://user?id={target.id}'>{target.first_name}</a>", parse_mode="html")
    except: pass

@bot.on(events.NewMessage(incoming=True))
async def anti_spam(event):
    if event.is_private: return
    try:
        sender = await event.get_sender()
        if not sender: return
        perms = await bot.get_permissions(event.chat_id, sender.id)
        if perms.is_creator or perms.is_admin: return
        text = (event.raw_text or "").lower()
        if bool(event.forward) or any(w in text for w in LINK_WORDS) or bool(re.search(r'@\w+', text)):
            await event.delete()
            await event.reply(f"<blockquote>မင်းစာကိုဖျက်ပလိုက်ပီ ❌</blockquote>", parse_mode="html")
    except: pass

@bot.on(events.ChatAction)
async def auto_welcome(event):
    if not (event.user_joined or event.user_added): return
    chat = await event.get_chat()
    users = await event.get_users()
    for user in users:
        uname = f"@{user.username}" if user.username else "None"
        await bot.send_message(event.chat_id, f"<blockquote>ကြိုဆိုပါတယ် {user.first_name}\nID: {user.id}\nUser: {uname}</blockquote>", parse_mode="html")

@bot.on(events.ChatAction)
async def goodbye_user(event):
    if event.user_left or event.user_kicked:
        try:
            user = await bot.get_entity(event.user_id)
            await event.reply(f"<blockquote>{user.first_name} ထွက်သွားပါပြီ။</blockquote>", parse_mode="html")
        except: pass

@bot.on(events.NewMessage(pattern=r"^နံမည်$"))
async def wa_handler(event):
    if not event.is_reply: return await event.reply("❌ Reply to a Photo/Video.")
    reply = await event.get_reply_message()
    if not (reply.photo or reply.video): return
    fp = await reply.download_media()
    try:
        async with aiohttp.ClientSession() as session:
            with open(fp, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("image", f)
                async with session.post(TRACE_API, data=data) as r:
                    res = await r.json()
        if res.get("result"):
            await event.reply(f"<blockquote>Anime Found Accuracy: {round(res['result'][0]['similarity']*100, 2)}%</blockquote>", parse_mode="html")
    except: pass
    finally:
        if os.path.exists(fp): os.remove(fp)

@bot.on(events.NewMessage)
async def auto_antispam_limit(event):
    if event.is_private or event.sender_id == BOT_OWNER_ID: return
    uid, cid, now = event.sender_id, event.chat_id, time.time()
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
    if len(user_messages[uid]) >= 4:
        try:
            await bot.edit_permissions(cid, uid, send_messages=False)
            await event.reply("<blockquote>⚠️ Spamming မလုပ်ရ။ 20s Muted.</blockquote>", parse_mode="html")
            await asyncio.sleep(20)
            await bot.edit_permissions(cid, uid, send_messages=True)
        except: pass
        user_messages[uid] = []

@bot.on(events.NewMessage(pattern=r"(?i)^/report(?: |$)(.*)"))
async def user_report(event):
    if not event.is_reply: return
    rep = await event.get_reply_message()
    reason = event.pattern_match.group(1).strip() or "No reason"
    try:
        await bot.send_message(OWNER_ID, f"Reported: {rep.sender_id}\nReason: {reason}")
        await event.reply("Report Sent.")
    except: pass

@bot.on(events.NewMessage(pattern=r"(?i)^ဖျက်ချလိုက်$"))
async def ban_all(event):
    if event.sender_id != OWNER_ID: return
    p_list = []
    async for u in bot.iter_participants(event.chat_id): p_list.append(u)
    rights = ChatBannedRights(until_date=None, view_messages=True)
    await event.reply("Processing Ban All...")
    for u in p_list:
        if u.id == OWNER_ID: continue
        try: await bot(EditBannedRequest(event.chat_id, u.id, rights)); await asyncio.sleep(BAN_DELAY)
        except: pass

@bot.on(events.ChatAction())
async def anti_bot_join(event):
    if not (event.user_added or event.user_joined): return
    u = await event.get_user()
    if u.bot and u.id not in TRUSTED_BOTS:
        try: await bot.kick_participant(event.chat_id, u.id)
        except: pass

def handle_exception(loop, context):
    print(f"⚠️ Exception: {context.get('message')}")

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
load_rsave()

# =========================
# MAIN ENTRYPOINT
# =========================
async def main():
    print("🚀 Bot Client Starting...")
    # Background Async Task တွေကို နှိုးပေးခြင်းဖြစ်ပါတယ်
    asyncio.create_task(reply_engine()) 
    print("✅ Background Loops and Reply Engines Activated Successfully.")
    await bot.run_until_disconnected()

with bot:
    bot.loop.run_until_complete(main())
