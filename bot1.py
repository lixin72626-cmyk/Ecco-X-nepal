from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run_flask():
    # Render က ပေးတဲ့ Port ကို Auto ဖတ်ခိုင်းတာပါ
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Web Server ကို နောက်ကွယ်ကနေ Auto Run ခိုင်းထားမယ်
threading.Thread(target=run_flask, daemon=True).start()import asyncio
import time
import sqlite3
import os
import json
import re
import aiohttp
import requests
import aiosqlite
from telethon import TelegramClient, events, Button, errors
from telethon.tl.types import ChannelParticipantsAdmins, UpdateChatParticipantAdd, ChannelParticipantsSearch, ChannelParticipant, User, Chat, ChatBannedRights, InputMessagesFilterVideo, PeerUser
from telethon.errors import FloodWaitError, RPCError
from telethon.errors.rpcerrorlist import ChatAdminRequiredError
from telethon.tl.custom.message import Message
from telethon.tl.functions.channels import EditBannedRequest, InviteToChannelRequest, GetFullChannelRequest
from telethon.utils import get_display_name
from datetime import datetime, date, timedelta
from collections import defaultdict
from googletrans import Translator

# ==========================
# TRACE_API URL သတ်မှတ်
# ==========================
TRACE_API = "https://api.trace.moe/search"

# ==========================
# Config (Render Env Support)
# ==========================
API_ID = int(os.environ.get("API_ID", 34166212))
API_HASH = os.environ.get("API_HASH", "753aae555e6d5901145fc8685d47bffe")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8959700806:AAGXpnjbOlUCUeZW9twboBhUtODbCwZ2Tf8")

OWNER_ID = 7681995468
BOT_OWNER_ID = 7681995468

# Render Disk သုံးလျှင် /data/ လမ်းကြောင်းပြောင်းရန်
DB_PATH = "/data/" if os.path.exists("/data") else ""
DB_FILE = f"{DB_PATH}bot_data.db"
PROTECTED_DB_FILE = f"{DB_PATH}protected.db"
RSAVE_FILE = f"{DB_PATH}rsave_data.json"

# ==========================
# MAIN BOT DATABASE
# ==========================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS asave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS rsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS tsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_groups (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, reply TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY)")
conn.commit()

# -------- Protected Users Database --------
protected_conn = sqlite3.connect(PROTECTED_DB_FILE, check_same_thread=False)
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

# ==========================
# TYPING WRAPPER
# ==========================
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

# ==========================
# Permission Check (FIXED Columns)
# ==========================
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

GROUPS = set()

@bot.on(events.ChatAction)
async def save_group(event):
    if event.is_group:
       GROUPS.add(event.chat_id)

@bot.on(events.Raw)
async def raw_handler(event):
    if isinstance(event, UpdateChatParticipantAdd):
        print("User joined")

# ==========================
# RSAVE FILE SYSTEM
# ==========================
rsave_list = []

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

# Global States
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
user_state = {}
ban_tracker = {}
alert_lock = {}
ctc_active = False
user1_id = None
user2_id = None
user_messages = defaultdict(list)
time_users = {}
notified_bots = {}

PAGE_SIZE = 50
REPLY_DURATION = 86400
REPLY_INTERVAL = 1
LINK_WORDS = ["@", "bio", "ဘိုင်o", "ဘိုင်အို", "http://", "https://", "t.me/", "telegram.me"]

@bot.on(events.NewMessage(pattern=r"(?i)^/start$"))
async def start_command(event):
    user = await bot.get_entity(event.sender_id)
    username = f"@{user.username}" if user.username else "No Username"
    msg = f"👋 မင်္ဂလာပါ {user.first_name}!\n\nUsername: {username}\nဒီ bot နဲ့ သုံးနိုင်တဲ့ commands အားလုံးကို (အကူအညီ) စမ်းကြည့်နိုင်ပါတယ်:\n"
    await event.reply(msg)

@bot.on(events.NewMessage(pattern=r"(?i)^အရှိန် (.+)"))
async def set_speed(event):
    if not has_permission(event.sender_id):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
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
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
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
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

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
                if chat_id not in attack_tasks or target_id not in attack_tasks[chat_id]:
                    break
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
        return await event.reply("သခင်နတ်စောင်းဆီက ခွင့်ပြုချက်မရထားပါ")
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
    if page > 0:
        buttons.append(Button.inline("⬅ Previous", data=f"rsave_prev_{page-1}".encode()))
    if end < len(rsave_list):
        buttons.append(Button.inline("Next ➡", data=f"rsave_next_{page+1}".encode()))
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
    if page > 0:
        buttons.append(Button.inline("⬅ Previous", data=f"rsave_prev_{page-1}".encode()))
    if end < len(rsave_list):
        buttons.append(Button.inline("Next ➡", data=f"rsave_next_{page+1}".encode()))
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
            "expire": time.time() + REPLY_DURATION,
            "base_msg_id": reply_msg.id,
            "chat_id": event.chat_id,
            "last_bot_msg": None,
            "mode": "reply",
            "username": target_entity.username,
            "index": 0
        }
    asyncio.create_task(reply_loop(target_id))
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
        if not found:
            return await event.reply("ဘယ်လိုခွေးမျိုး အမျိုးစားများကိုမှနှိမ်နှင်းထားချင်းမရှိသေးပါ")
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
        data = reply_targets[event.sender_id]
        data["base_msg_id"] = event.id
        data["mode"] = "reply"

@bot.on(events.MessageDeleted)
async def detect_delete(event):
    for target_id, data in reply_targets.items():
        if data["last_bot_msg"] in event.deleted_ids:
            data["mode"] = "mention"

async def reply_loop(target_id):
    global current_index
    while target_id in reply_targets:
        data = reply_targets.get(target_id)
        if not data: break
        if not rsave_list:
            await asyncio.sleep(2)
            continue
        try:
            text = rsave_list[current_index]
            msg = await bot.send_message(data["chat_id"], text, reply_to=data["base_msg_id"])
            data["last_bot_msg"] = msg.id
            current_index = (current_index + 1) % len(rsave_list)
        except:
            pass
        await asyncio.sleep(REPLY_INTERVAL)

@bot.on(events.MessageDeleted)
async def track_delete(event):
    for uid, data in reply_targets.items():
        if data["base_msg_id"] in event.deleted_ids:
            data["base_msg_id"] = None
            data["mode"] = "mention"

async def reply_engine():
    while True:
        await asyncio.sleep(REPLY_INTERVAL)
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
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    if not event.is_reply:
        return await event.reply("❌အသုံးပြုပုံမှားယွင်းနေပါတယ် (ရိုက်သတ်) <reply_user> .....။")
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")
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
    if event.sender_id in reply_targets:
        texts = cursor.execute("SELECT text FROM rsave ORDER BY id ASC").fetchall()
        if texts:
            data = reply_targets[event.sender_id]
            if time.time() > data.get("expire", 0):
                del reply_targets[event.sender_id]
                return
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1
            message = f"<a href='tg://user?id={event.sender_id}'>User</a>\n{text}"
            reply_mode = True
            if data.get("last_bot_msg"):
                try: await bot.get_messages(event.chat_id, ids=data["last_bot_msg"])
                except: reply_mode = False
            try:
                msg = await event.reply(message, parse_mode="html") if reply_mode else await bot.send_message(event.chat_id, message, parse_mode="html")
                data["last_bot_msg"] = msg.id
            except: pass
            await asyncio.sleep(attack_speed)

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
    try:
        async for user in bot.iter_participants(chat_id):
            if user.bot: target_ids.append(user.id)
    except: pass

    if event.sender_id in target_ids:
        try: await bot.delete_messages(chat_id, event.id)
        except Exception as e: print(f"Failed to delete message: {e}")
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id in delete_targets:
            try: await bot.delete_messages(chat_id, event.id)
            except Exception as e: print(f"Failed to delete reply: {e}")

@bot.on(events.NewMessage(pattern=r"(?i)^ထိန်းချုပ်လိုက်$"))
async def set_att(event):
    try:
        if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
            return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")
        if not event.is_reply: return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")
        reply_msg = await event.get_reply_message()
        if is_owner(reply_msg.sender_id): return await event.reply("⚠️ Owner ကို mute / control လုပ်လို့မရပါ။")
        att_targets[reply_msg.sender_id] = event.chat_id
        await event.reply("✅ User ကို 10s Auto Mute System ထဲထည့်လိုက်ပါပြီ။")
    except Exception as e:
        await event.reply("⚠️ Bot မှာ တစ်စုံတစ်ရာ အမှားဖြစ်နေပါတယ်။ Admin ကို contact လုပ်ပါ။")

@bot.on(events.NewMessage(pattern=r"(?i)^လွတ်ပေးလိုက်$"))
async def unset_att(event):
    try:
        if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
            return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")
        if not event.is_reply: return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")
        reply_msg = await event.get_reply_message()
        if reply_msg.sender_id in att_targets:
            del att_targets[reply_msg.sender_id]
            await event.reply("✅ User ကို Control System မှ ဖယ်ရှားလိုက်ပါပြီ။")
        else:
            await event.reply("⚠️ ဒီ User Control List ထဲမှာမရှိပါ။")
    except Exception as e:
        await event.reply("⚠️ Bot မှာ တစ်စုံတစ်ရာ အမှားဖြစ်နေပါတယ်။ Admin ကို contact လုပ်ပါ။")

@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):
    try:
        user_id = event.sender_id
        chat_id = event.chat_id
        if user_id not in att_targets or att_targets[user_id] != chat_id: return
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
    try:
        async for user in bot.iter_participants(chat_id): members.append(user)
    except: return
    batch_size = 5
    delay_seconds = 2
    for i in range(0, len(members), batch_size):
        if stop_flags.get(chat_id): break
        batch = members[i:i + batch_size]
        mentions = [f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" for user in batch]
        message = " ".join(mentions) + "\n\n" + text
        try: await bot.send_message(chat_id, message, parse_mode="html")
        except: pass
        await asyncio.sleep(delay_seconds)
    stop_flags[chat_id] = False
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
async def save_attack_text(event):
    if event.sender_id == OWNER_ID or event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Attack text saved")
    await event.reply("❌ Permission denied")

@bot.on(events.NewMessage(pattern=r"/Tsave (.+)"))
async def save_troll_text(event):
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
    rows = cursor.execute("SELECT id, text FROM asave").fetchall() if "Attack" in title else cursor.execute("SELECT id, text FROM tsave").fetchall()
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
    shared_count, failed_count = 0, 0
    status_msg = await event.reply("📤 Forwarding started...")
    cursor.execute("SELECT chat_id FROM active_groups")
    groups = [row[0] for row in cursor.fetchall()]
    for group_id in groups:
        try:
            await bot.forward_messages(group_id, reply_msg)
            shared_count += 1
            await asyncio.sleep(1)
        except: failed_count += 1
        await status_msg.edit(f"📤 Forwarding...\n✅ Success: {shared_count}\n❌ Failed: {failed_count}")
    await status_msg.edit(f"✅ Completed!\n📦 Forwarded to: {shared_count} groups\n❌ Failed: {failed_count} groups")

@bot.on(events.NewMessage)
async def track_groups(event):
    chat = await event.get_chat()
    if not any([getattr(chat, "megagroup", False), getattr(chat, "gigagroup", False), getattr(chat, "broadcast", False)]): return
    cursor.execute("SELECT chat_id FROM active_groups WHERE chat_id = ?", (chat.id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO active_groups(chat_id) VALUES(?)", (chat.id,))
        conn.commit()

# FIXED: Added missing event.reply() to send the text
@bot.on(events.NewMessage(pattern=r"(?i)^groupid"))
async def chat_info(event):
    chat = await event.get_chat()
    admins = await bot.get_participants(chat, filter=ChannelParticipantsAdmins)
    admin_text = "".join([f"{idx}. {a.first_name}\n   {a.id}\n" for idx, a in enumerate(admins, start=1)])
    group_id_display = f"-100{chat.id}" if getattr(chat, 'megagroup', False) or getattr(chat, 'broadcast', False) else str(chat.id)
    msg = f"<blockquote>Group Name: {chat.title}\nGroup ID: {group_id_display}\n\nAdmins:\n{admin_text}</blockquote>"
    await event.reply(msg, parse_mode="html")

# FIXED: Removed duplicate duplicate reply call at the end
@bot.on(events.NewMessage(pattern=r"^သူ့စောက်ကြောင်း(?: (.+))?$"))
async def user_id(event):
    arg = event.pattern_match.group(1)
    try:
        if event.is_reply: user = await bot.get_entity((await event.get_reply_message()).sender_id)
        elif arg: user = await bot.get_entity(arg)
        else: user = await bot.get_entity(event.sender_id)
        username = f"@{user.username}" if user.username else "No Username"
        msg = f"<blockquote>Name : {user.first_name}\nUser ID : {user.id}\nUsername : {username}</blockquote>"
        await event.reply(msg, parse_mode="html")
    except:
        await event.reply("User ရှာမတွေ့ပါ။ Username မှန်မမှန်စစ်ပါ။")

@bot.on(events.NewMessage(pattern=r"/gplist"))
async def group_list(event):
    rows = cursor.execute("SELECT id FROM groups").fetchall()
    if rows: await event.reply(f"📂 Groups:\n" + "\n".join([str(r[0]) for r in rows]))
    else: await event.reply("No groups saved.")

@bot.on(events.NewMessage(pattern=r"/Botadmlist"))
async def list_admins(event):
    rows = cursor.execute("SELECT user_id FROM bot_admins").fetchall()
    if not rows: return await event.reply("<blockquote>⚠️ No Bot Admins assigned.</blockquote>", parse_mode="html")
    msg_lines = []
    for r in rows:
        try: msg_lines.append(f"{(await bot.get_entity(r[0])).first_name} — {r[0]}")
        except: msg_lines.append(f"Unknown — {r[0]}")
    await event.reply("<blockquote>👮 Bot Admins:\n\n" + "\n".join(msg_lines) + "</blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^မှတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def add_admin(event):
    if not is_owner(event.sender_id): return
    bot_mention, uid = event.pattern_match.group(1), event.pattern_match.group(2)
    me = await bot.get_me()
    if bot_mention and bot_mention.lower() != me.username.lower(): return
    if event.is_reply: uid = (await event.get_reply_message()).sender_id
    elif uid: uid = int(uid)
    else: return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")
    cursor.execute("INSERT OR IGNORE INTO bot_admins(user_id) VALUES(?)", (uid,))
    conn.commit()
    await event.reply(f"✅ User `{uid}` ကို Bot Admin အဖြစ်ထည့်လိုက်ပါပြီ")

@bot.on(events.NewMessage(pattern=r"(?i)^ဖြုတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def remove_admin(event):
    if not is_owner(event.sender_id): return
    bot_mention, uid = event.pattern_match.group(1), event.pattern_match.group(2)
    me = await bot.get_me()
    if bot_mention and bot_mention.lower() != me.username.lower(): return
    if event.is_reply: uid = (await event.get_reply_message()).sender_id
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
    help_text = "<blockquote>BOT COMMANDS GUIDE (မြန်မာလို)\n...\n( အကူအညီ ) ကို လူတိုင်း အသုံးပြုနိုင်ပါသည်</blockquote>"
    await event.reply(help_text, parse_mode="html")

LANGUAGES = {"English": "en", "Japanese": "ja", "Myanmar": "my"} # အတိုချုံ့ထားပါသည်

@bot.on(events.NewMessage(pattern=r'^ဘာသာပြန်မယ်$', incoming=True))
async def translate_cmd(event):
    if not event.is_reply: return await event.reply("Reply ထောက်ပြီး /translate သုံးပါ")
    reply_msg = await event.get_reply_message()
    if not reply_msg.text: return await event.reply("Text မရှိပါ")
    user_state[event.sender_id] = {"original": reply_msg.text, "waiting_language": True}
    await event.reply("🌐 ဘာသာစကားနာမည် ရိုက်ပါ (ဥပမာ: English, Japanese)")

@bot.on(events.NewMessage(incoming=True))
async def language_input(event):
    user_id = event.sender_id
    if user_id not in user_state or not user_state[user_id].get("waiting_language"): return
    lang_name = event.text.strip()
    if lang_name not in LANGUAGES: return await event.reply("❌ Language မမှန်ပါ။")
    lang_code = LANGUAGES[lang_name]
    original = user_state[user_id]["original"]
    translated = translator.translate(original, dest=lang_code).text
    user_state[user_id]["waiting_language"] = False
    user_state[user_id]["pages"] = [f"<blockquote>Original:\n{original}</blockquote>", f"<blockquote>Translated:\n{translated}</blockquote>"]
    user_state[user_id]["current_page"] = 0
    await event.reply(user_state[user_id]["pages"][0], parse_mode="html", buttons=[[Button.inline("Next ▶", data=f"next_{user_id}")]])

@bot.on(events.CallbackQuery)
async def page_callback(event):
    data = event.data.decode("utf-8")
    if not any([data.startswith("next"), data.startswith("prev")]): return
    user_id = int(data.split("_")[-1])
    if user_id not in user_state: return await event.answer("Session expired ❌", alert=True)
    page_data = user_state[user_id]
    current = page_data["current_page"]
    if data.startswith("next"):
        current += 1
        if current >= len(page_data["pages"]): return await event.answer("End!", alert=True)
    elif data.startswith("prev"):
        current -= 1
        if current < 0: return await event.answer("Start!", alert=True)
    page_data["current_page"] = current
    buttons = [[Button.inline("◀ Previous", data=f"prev_{user_id}"), Button.inline("Next ▶", data=f"next_{user_id}")]]
    await event.edit(page_data["pages"][current], parse_mode="html", buttons=buttons)

def parse_time(text):
    if text:
        match = re.match(r"(\d+)([mhd])", text.lower())
        if match:
            num, unit = match.groups()
            num = int(num)
            if unit == "m": return num * 60
            if unit == "h": return num * 3600
            if unit == "d": return num * 86400
    return 600

@bot.on(events.NewMessage(pattern=r"(?i)^/ban$"))
async def ban_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return await event.reply("❌ Admin only.")
    if not event.is_reply: return await event.reply("⚠️ Reply to the user.")
    try:
        reply = await event.get_reply_message()
        await bot.edit_permissions(event.chat_id, reply.sender_id, view_messages=False)
        await event.reply("🚫 User banned successfully.")
    except: await event.reply("⚠️ Error")

@bot.on(events.NewMessage(pattern=r"(?i)^/unban$"))
async def unban_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return await event.reply("❌ Admin only.")
    if not event.is_reply: return await event.reply("⚠️ Reply to user.")
    try:
        reply = await event.get_reply_message()
        await bot.edit_permissions(event.chat_id, reply.sender_id, view_messages=True, send_messages=True)
        await event.reply("✅ User unbanned.")
    except: await event.reply("⚠️ Error")

@bot.on(events.NewMessage(pattern=r"(?i)^/mute(?:\s+(.+))?$"))
async def mute_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return await event.reply("❌ Admin only.")
    if not event.is_reply: return await event.reply("⚠️ Reply to user.")
    reply = await event.get_reply_message()
    text = event.pattern_match.group(1)
    seconds = parse_time(text)
    try:
        await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=False)
        await event.reply(f"🔇 User muted")
        if seconds > 0:
            await asyncio.sleep(seconds)
            await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
            await event.reply("🔊 Unmuted")
    except: await event.reply("⚠️ Error")

@bot.on(events.NewMessage(pattern=r"(?i)^/unmute$"))
async def unmute_user(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return await event.reply("❌ Admin only.")
    if not event.is_reply: return await event.reply("⚠️ Reply to user.")
    try:
        reply = await event.get_reply_message()
        await bot.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
        await event.reply("🔊 User manually unmuted")
    except: await event.reply("⚠️ Error")

@bot.on(events.NewMessage(pattern=r"(?i)^/filter"))
async def add_filter(event):
    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)): return await event.reply("❌ Admin only.")
    args = event.raw_text.split(maxsplit=2)
    if len(args) < 3: return await event.reply("Usage: /Filter trigger reply")
    cursor.execute("INSERT INTO filters (chat_id, trigger, reply) VALUES (?, ?, ?)", (event.chat_id, args[1].lower(), args[2]))
    conn.commit()
    await event.reply("✅ Filter added")

@bot.on(events.NewMessage(incoming=True))
async def filter_reply(event):
    if event.raw_text is None: return
    cursor.execute("SELECT trigger, reply FROM filters WHERE chat_id=?", (event.chat_id,))
    for trigger, reply in cursor.fetchall():
        if event.raw_text.lower() == trigger:
            await event.reply(reply)
            break

BAN_THRESHOLD = 10
@bot.on(events.ChatAction)
async def auto_owner_alert(event):
    chat_id = event.chat_id
    if chat_id not in ban_tracker: ban_tracker[chat_id] = []
    if chat_id not in alert_lock: alert_lock[chat_id] = False
    if event.user_kicked:
        banned_by = event.action_message.sender
        participants = await bot.get_participants(chat_id, filter=ChannelParticipantsAdmins)
        owner = next((p for p in participants if getattr(p.participant, "creator", False)), None)
        if not owner or banned_by.id in [(await bot.get_me()).id, owner.id]: return
        ban_tracker[chat_id].append(banned_by.first_name)
        if len(await bot.get_participants(chat_id)) <= BAN_THRESHOLD: return
        if not alert_lock[chat_id]:
            alert_lock[chat_id] = True
            await bot.send_message(owner.id, f"<blockquote>{owner.first_name} သတိပေးချက်\n\n{', '.join(list(set(ban_tracker[chat_id])))} က Members တွေကို Ban နေပါတယ်။</blockquote>", parse_mode="html")
            await asyncio.sleep(1)
            alert_lock[chat_id] = False
            ban_tracker[chat_id] = []

@bot.on(events.NewMessage(pattern=r'^စလိုက်'))
async def start_ctc(event):
    global ctc_active, user1_id, user2_id
    if not has_permission(event.sender_id): return
    try:
        parts = event.raw_text.split()
        user1_id, user2_id = int(parts[1]), int(parts[2])
        ctc_active = True
        await event.reply("Activated")
    except: await event.reply("Error")

@bot.on(events.NewMessage(pattern=r'^တော်တော့'))
async def stop_ctc(event):
    global ctc_active
    if not has_permission(event.sender_id): return
    ctc_active = False
    await event.reply("Deactivated")

@bot.on(events.NewMessage(incoming=True))
async def handle_message(event):
    if not ctc_active or event.sender_id not in (user1_id, user2_id): return
    target_id = user2_id if event.sender_id == user1_id else user1_id
    await event.reply(f"{event.raw_text} <a href='tg://user?id={target_id}'>{(await bot.get_entity(target_id)).first_name}</a>", parse_mode="html")

# FIXED: Added from telethon import errors at top to prevent NameError
@bot.on(events.NewMessage(incoming=True))
async def anti_spam(event):
    if event.is_private: return
    try:
        sender = await event.get_sender()
        if not sender or (await bot.get_permissions(event.chat_id, sender.id)).is_admin: return
        text = (event.raw_text or "").lower()
        if any([event.forward, any(w in text for w in LINK_WORDS), bool(re.search(r'@\w+', text))]):
            try: await event.delete()
            except errors.ChatAdminRequiredError: return
            await event.reply(f"<blockquote><a href='tg://user?id={sender.id}'>{sender.first_name}</a> စည်းကမ်းမရှိလို့ ဖျက်လိုက်ပြီ ❌</blockquote>", parse_mode="html")
    except Exception as e: print("AntiSpam Error:", e)

WELCOME_TEXT = "{mention_name} ကြိုဆိုပါတယ်"
@bot.on(events.ChatAction)
async def auto_welcome(event):
    if not (event.user_joined or event.user_added): return
    chat = await event.get_chat()
    for user in await event.get_users():
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        text = WELCOME_TEXT.replace("{mention_name}", user_mention)
        await bot.send_message(event.chat_id, f"<blockquote>{text}</blockquote>", parse_mode="html")

@bot.on(events.ChatAction)
async def goodbye_user(event):
    if event.user_left or event.user_kicked:
        try:
            user = await bot.get_entity(event.user_id)
            await event.reply(f"<blockquote><a href='tg://user?id={user.id}'>{user.first_name}</a> ထွက်သွားပါပြီ။</blockquote>", parse_mode="html")
        except: pass

def fetch_anime_title(anilist_id: int):
    try:
        resp = requests.post("https://graphql.anilist.co", json={"query": "query($id:Int){Media(id:$id,type:ANIME){title{english romaji}}}", "variables": {"id": anilist_id}}, timeout=10).json()
        m = resp["data"]["Media"]
        return m["title"]["english"] or m["title"]["romaji"]
    except: return "Unknown"

def fetch_characters(anilist_id: int):
    try:
        resp = requests.post("https://graphql.anilist.co", json={"query": "query($id:Int){Media(id:$id,type:ANIME){characters(sort:ROLE){edges{node{name{full}}}}}}", "variables": {"id": anilist_id}}, timeout=10).json()
        return [e["node"]["name"]["full"] for e in resp["data"]["Media"]["characters"]["edges"][:3]]
    except: return ["Unknown"]

@bot.on(events.NewMessage(pattern=r"^နံမည်$"))
async def wa_handler(event):
    if not event.is_reply: return await event.reply("❌ Reply to Photo/Video")
    reply = await event.get_reply_message()
    if not (reply.photo or reply.video): return await event.reply("❌ Media required")
    file_path = await reply.download_media()
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("image", f)
                async with session.post(TRACE_API, data=data) as resp: result = await resp.json()
        if not result.get("result"): return await event.reply("❌ Not Found")
        best = result["result"][0]
        if best["similarity"] >= 0.92:
            await event.reply(f"<blockquote>🎬 {fetch_anime_title(best['anilist'])}\n🎯 {round(best['similarity']*100,2)}%</blockquote>", parse_mode="html")
        else: await event.reply("<blockquote>No perfect match found.</blockquote>", parse_mode="html")
    except Exception as e: await event.reply(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@bot.on(events.NewMessage)
async def auto_antispam(event):
    if event.is_private or event.sender_id == BOT_OWNER_ID: return
    now = time.time()
    user_messages[event.sender_id].append(now)
    user_messages[event.sender_id] = [t for t in user_messages[event.sender_id] if now - t < 5]
    if len(user_messages[event.sender_id]) >= 4:
        try:
            await bot.edit_permissions(event.chat_id, event.sender_id, send_messages=False)
            await event.reply("<blockquote>⚠️ Spam သဖြင့် 20 စက္ကန့် Mute လိုက်သည်။</blockquote>", parse_mode="html")
            await asyncio.sleep(20)
            await bot.edit_permissions(event.chat_id, event.sender_id, send_messages=True)
        except: pass
        user_messages[event.sender_id] = []

@bot.on(events.NewMessage(pattern=r"(?i)^/report(?: |$)(.*)"))
async def user_report(event):
    if not event.is_reply: return await event.reply("Reply to user with /report <reason>")
    reason = event.pattern_match.group(1).strip() or "No reason"
    try:
        await bot.send_message(OWNER_ID, f"<b>Report</b>\nTarget: { (await event.get_reply_message()).sender_id }\nReason: {reason}")
        await event.reply("Report Sent.")
    except: await event.reply("Failed")

@bot.on(events.NewMessage(pattern=r'^အချိန် (\d+)([smhd])'))
async def set_time(event):
    if not event.is_reply: return await event.reply("❌ Reply user message")
    amount, unit = int(event.pattern_match.group(1)), event.pattern_match.group(2)
    seconds = amount
    if unit == "m": seconds = amount * 60
    elif unit == "h": seconds = amount * 3600
    elif unit == "d": seconds = amount * 86400
    time_users[(await event.get_reply_message()).sender_id] = time.time() + seconds
    await event.reply(f"⏰ Time set for {amount}{unit}")

def has_time(user_id):
    return user_id in time_users and time.time() < time_users[user_id]

@bot.on(events.NewMessage(pattern=r"(?i)^ဖျက်ချလိုက်$"))
async def ban_all(event):
    if event.sender_id != OWNER_ID: return await event.reply("Owner only.")
    participants = []
    async for u in bot.iter_participants(event.chat_id): participants.append(u)
    status = await event.reply("Processing...")
    count = 0
    for user in participants:
        if user.id == OWNER_ID or (await bot.get_permissions(event.chat_id, user.id)).is_admin: continue
        try:
            await bot(EditBannedRequest(event.chat_id, user.id, ChatBannedRights(until_date=None, view_messages=True)))
            count += 1
            await asyncio.sleep(0.1)
        except FloodWaitError as e: await asyncio.sleep(e.seconds + 1)
        except: continue
    await status.edit(f"Done. Banned: {count}")

@bot.on(events.ChatAction)
async def anti_bot_join(event):
    if not (event.user_added or event.user_joined): return
    user = await event.get_user()
    if not user.bot or user.id in TRUSTED_BOTS: return
    try:
        await bot.kick_participant(event.chat_id, user.id)
        if event.chat_id not in notified_bots: notified_bots[event.chat_id] = set()
        if user.id not in notified_bots[event.chat_id]:
            await event.reply(f"<a href='tg://user?id={user.id}'>{user.first_name}</a> ကို ဖယ်ရှားလိုက်ပြီ။ ⚡️", parse_mode="html")
            notified_bots[event.chat_id].add(user.id)
    except Exception as e:
        await bot.send_message(OWNER_ID, f"⚠ Failed to remove bot: {e}")

def handle_exception(loop, context): print(f"⚠️ Unhandled exception: {context.get('message')}")
asyncio.get_event_loop().set_exception_handler(handle_exception)

load_rsave()

async def main():
    print("Bot is running...")
    asyncio.create_task(reply_engine()) # Start running loop background
    await bot.run_until_disconnected()

with bot:
    bot.loop.run_until_complete(main())
