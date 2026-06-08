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
from telethon.utils import get_display_name
from telethon.tl.types import ChannelParticipantsSearch
from datetime import date
from telethon.tl.types import ChannelParticipant, User, Chat
from telethon.tl.types import ChatBannedRights
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon import events, Button
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
BOT_TOKEN = "8959700806:AAEPYVSxBnbvzVlPXOmnqW0dzXf3PgY7OZI"

OWNER_ID = 7681995468
BOT_OWNER_ID = 7681995468
DB_FILE = "bot_data.db"

# ==========================
# MAIN BOT DATABASE
# ==========================

conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

# ==========================
# ATTACK SAVE TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS asave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    text TEXT
)
""")

# ==========================
# REPLY SAVE TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS rsave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    text TEXT
)
""")

# ==========================
# TROLL SAVE TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS tsave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    text TEXT
)
""")

# ==========================
# BOT ADMINS TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS bot_admins (
    user_id INTEGER PRIMARY KEY
)
""")

# ==========================
# ACTIVE GROUPS TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS active_groups (
    chat_id INTEGER PRIMARY KEY
)
""")

# ==========================
# FILTER TABLE
# ==========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS filters (
    chat_id INTEGER,
    trigger TEXT,
    reply TEXT
)
""")

conn.commit()

# -------- Protected Users Database --------
protected_conn = sqlite3.connect("protected.db", check_same_thread=False)
protected_cursor = protected_conn.cursor()

protected_cursor.execute("""
CREATE TABLE IF NOT EXISTS protected_users (
    user_id INTEGER PRIMARY KEY
)
""")
protected_conn.commit()

# Load protected users into memory
protected_cursor.execute("SELECT user_id FROM protected_users")
protected_users = set(row[0] for row in protected_cursor.fetchall())

# ==========================
# TELETHON CLIENT
# ==========================
bot = TelegramClient("Bot10", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

print("✅ All databases created and verified successfully!")

# Helper function: save group
async def remember_group(chat_id):
    cursor.execute("INSERT OR IGNORE INTO active_groups (chat_id) VALUES (?)", (chat_id,))
    conn.commit()

# Helper function: get all saved groups
def get_active_groups():
    rows = cursor.execute("SELECT chat_id FROM active_groups").fetchall()
    return [r[0] for r in rows]

# ==========================
# TYPING WRAPPER ONLY
# ==========================

# Save original functions
original_send_message = bot.send_message
original_send_file = bot.send_file

# --------------------------
# Send message with typing
# --------------------------
async def send_message_with_typing(chat_id, *args, **kwargs):
    try:
        async with bot.action(chat_id, 'typing'):
            await asyncio.sleep(0.5)  # typing duration
    except:
        pass
    return await original_send_message(chat_id, *args, **kwargs)

# --------------------------
# Send file with typing
# --------------------------
async def send_file_with_typing(chat_id, *args, **kwargs):
    try:
        async with bot.action(chat_id, 'typing'):
            await asyncio.sleep(0.5)  # typing duration
    except:
        pass
    return await original_send_file(chat_id, *args, **kwargs)

# --------------------------
# Override bot functions
# --------------------------
bot.send_message = send_message_with_typing
bot.send_file = send_file_with_typing

# ==========================
# Permission Check
# ==========================
def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    cursor.execute("SELECT id FROM bot_admins WHERE id=?", (user_id,))
    return cursor.fetchone() is not None

def is_member(user_id):
    return not (is_owner(user_id) or is_admin(user_id))

def is_bot_admin(user_id):
    cursor.execute("SELECT id FROM bot_admins WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None

GROUPS = set()

@bot.on(events.ChatAction)
async def save_group(event):
    if event.is_group:
       GROUPS.add(event.chat_id)  # append → add

@bot.on(events.Raw)
async def raw_handler(event):
    if isinstance(event, UpdateChatParticipantAdd):
        print("User joined")

# ==========================
# CHECK PERMISSIONS
# ==========================
def has_permission(user_id):
    # True only if user is owner or admin
    return is_owner(user_id) or is_admin(user_id)

# ==========================
# RSAVE FILE SYSTEM
# ==========================

RSAVE_FILE = "rsave_data.json"
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

# ==========================
# Global States
# ==========================
troll_targets = {}
delete_targets = {}
att_targets = {}
attack_speed = 1
GROUPS = set()


translator = Translator()

TRUSTED_BOTS = [OWNER_ID]  # Owner ID ထည့်ပါ
TRUSTED_BOTS += []  # နောက်ထပ် trusted user IDs ထည့်နိုင်

calling_task = None
stop_calling = False

reply_task_started = False

REPLY_DURATION = 86400  # 24 hours
REPLY_INTERVAL = 1

reply_targets = {}
bot_id = None

current_index = 0

LINK_WORDS = ["@", "bio", "ဘိုင်O", "ဘိုင်အို", "http://", "https://", "t.me/", "telegram.me"]

from telethon import events

@bot.on(events.NewMessage(pattern=r"(?i)^/start$"))
async def start_command(event):
    user = await bot.get_entity(event.sender_id)
    username = f"@{user.username}" if user.username else "No Username"

    msg = (
        f"👋 မင်္ဂလာပါ {user.first_name}!\n\n"
        f"Username: {username}\n"
        "ဒီ bot နဲ့ သုံးနိုင်တဲ့ commands အားလုံးကို (အကူအညီ) စမ်းကြည့်နိုင်ပါတယ်:\n"
    )

    await event.reply(msg)

# ==========================
# GROUP SPEED STORAGE
# ==========================
group_speeds = {}   # {chat_id: speed}

# ==========================
# SPEED CONTROL (PER GROUP)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^အရှိန် (.+)"))
async def set_speed(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    chat_id = event.chat_id

    try:
        speed = float(event.pattern_match.group(1))

        if speed < 0:
            speed = 0

        group_speeds[chat_id] = speed

        await event.reply(f"အမြန်နှုန်းကို {speed} စက္ကန့်သို့ချိန်ညှိလိုက်ပါပီ (ဒီ Group အတွက်ပဲ)")

    except:
        await event.reply("Invalid number.")


# ==========================
# ATTACK TASK STORAGE
# ==========================
attack_tasks = {}  # {chat_id: {target_id: task}}


# ==========================
# ATTACK COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^သတ်ပလိုက်(?:\s|$)"))
async def attack_user(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    chat_id = event.chat_id

    # -------- TARGET DETECT --------

    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
    else:
        args = event.message.text.split()

        if len(args) < 2:
            return await event.reply(
                "မျိုးမစစ်တွေကိုနှိမ်နှင်းစေချင်ရင်မိန့်ကိုမှန်ကန်စွာအသုံးပြုပါ (သတ်ပလိုက်) (Reply)"
            )

        try:
            entity = await bot.get_entity(args[1])
            target_id = entity.id
        except:
            return await event.reply("မင်းပြောတဲ့ခွေးမျိုးလေးကိုရှာမတွေ့သေးပါ Try.")

    # -------- OWNER PROTECTION --------

    if is_owner(target_id):
        return await event.reply(
            "သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း"
        )

    # -------- GET ASAVE TEXTS --------

    texts = cursor.execute(
        "SELECT text FROM asave ORDER BY id ASC"
    ).fetchall()

    if not texts:
        return await event.reply(
            "နှိမ်နှင်းရမဲ့စာသားတွေကိုသိမ်းဆည်းထားချင်းမရှိသောကြေင့်ပြုလုပ်၍မရပါ"
        )

    # -------- INIT GROUP DICT --------

    if chat_id not in attack_tasks:
        attack_tasks[chat_id] = {}

    # -------- CHECK ALREADY RUNNING --------

    if target_id in attack_tasks[chat_id]:
        return await event.reply("Already attacking this user.")

    user = await bot.get_entity(target_id)

    # -------- SPAM LOOP --------

    async def spam():

        index = 0
        end_time = asyncio.get_event_loop().time() + (24 * 60 * 60)

        try:
            while asyncio.get_event_loop().time() < end_time:

                if target_id not in attack_tasks.get(chat_id, {}):
                    break

                text = texts[index % len(texts)][0]

                message = (
                    f"<a href='tg://user?id={user.id}'>{user.first_name}</a> {text}"
                )

                try:
                    await bot.send_message(
                        chat_id,
                        message,
                        parse_mode="html"
                    )

                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                    continue

                index += 1

                # -------- GROUP SPEED --------
                speed = group_speeds.get(chat_id, 1.0)

                await asyncio.sleep(speed)

        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(spam())

    attack_tasks[chat_id][target_id] = task

    await event.reply(
        "မင်းနှင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး"
    )


# ==========================
# STOP ONLY CURRENT GROUP
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^ရပ်တော့"))
async def stop_attack(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("သခင်နတ်စောင်းဆီက ခွင့်ပြုချက်မရထားပါ")

    chat_id = event.chat_id

    if chat_id in attack_tasks:

        for task in attack_tasks[chat_id].values():
            task.cancel()

        attack_tasks[chat_id].clear()

    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

PAGE_SIZE = 50  # စာ 50 ခုချင်းပြ

# ==============================
# RSAVE (OWNER ONLY)
# ==============================
@bot.on(events.NewMessage(pattern=r"(?i)^/rsave (.+)"))
async def save_r(event):
    if not is_owner(event.sender_id):
        return

    text = event.pattern_match.group(1)
    rsave_list.append(text)
    save_rsave()  # function to persist list

    await event.reply(f"Saved ✅\nTotal Saved: {len(rsave_list)}")


# ==============================
# Generic Show Page Function for Rsave
# ==============================
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


# ==============================
# List Rsave (/rlist)
# ==============================
@bot.on(events.NewMessage(pattern=r"(?i)^/rlist$"))
async def list_r(event):
    if not is_owner(event.sender_id):
        return

    if not rsave_list:
        await event.reply("<blockquote>⚠️ Rsave list is empty.</blockquote>", parse_mode="html", reply_to=event.message.id)
        return

    await show_rsave_page(event, 0)


# ==============================
# Pagination Button Handler
# ==============================
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

# ================= REPLY ACTIVATE =================

@bot.on(events.NewMessage(pattern=r"(?i)^လွတ်အောင်ပြေး$"))
async def set_reply(event):
    global bot_id

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return

    if not event.is_reply:
        return await event.reply("Reply to target user.")

    reply_msg = await event.get_reply_message()

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if reply_msg.sender_id == bot_id:
        return

    if is_owner(reply_msg.sender_id):
        return

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

# ================= UNREPLY (OWNER + ADMIN) =================

@bot.on(events.NewMessage(pattern=r"(?i)^ပေးနားလိုက်"))
async def unset_reply(event):

    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return

    chat_id = event.chat_id  # ဒီ group id ကို key အနေနဲ့သုံးမယ်

    # Reply မပြန်ဘဲ ရိုက်လိုက်ရင် → ဒီ Group ထဲကပဲ clear
    if not event.is_reply:
        found = False
        for uid in list(reply_targets.keys()):
            # uid က dict key, chat_id နဲ့ filter
            if reply_targets[uid]["chat_id"] == chat_id:
                del reply_targets[uid]
                found = True

        if not found:
            return await event.reply("ဘယ်လိုခွေးမျိုး အမျိုးစားများကိုမှနှိမ်နှင်းထားချင်းမရှိသေးပါ")

        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")

    # Reply ပြန်ပြီး ရိုက်ရင် → ဒီ Group ထဲက user တစ်ယောက်ပဲ ရပ်
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    if target_id in reply_targets and reply_targets[target_id]["chat_id"] == chat_id:
        del reply_targets[target_id]
        return await event.reply("မျိုးမစစ်ပေါင်းသောင်းနဲ့ချီ လွတ်ငြိမ်းချမ်းသာစေ")

    await event.reply("This user not active.")

# ================= TRACK USER NEW MESSAGE =================

@bot.on(events.NewMessage)
async def track_user(event):
    global bot_id

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if event.sender_id == bot_id:
        return

@bot.on(events.NewMessage)
async def track_user(event):
    global bot_id

    if bot_id is None:
        bot_id = (await bot.get_me()).id

    if event.sender_id == bot_id:
        return

    if event.sender_id in reply_targets:
        data = reply_targets[event.sender_id]
        data["base_msg_id"] = event.id
        data["mode"] = "reply"

# ================= DELETE DETECT =================

@bot.on(events.MessageDeleted)
async def detect_delete(event):
    for target_id, data in reply_targets.items():
        if data["last_bot_msg"] in event.deleted_ids:
            data["mode"] = "mention"


async def reply_loop(target_id):
    global current_index

    while target_id in reply_targets:

        data = reply_targets.get(target_id)
        if not data:
            break

        if not rsave_list:
            await asyncio.sleep(2)
            continue

        try:
            text = rsave_list[current_index]

            msg = await bot.send_message(
                data["chat_id"],
                text,
                reply_to=data["base_msg_id"]
            )

            data["last_bot_msg"] = msg.id

            current_index += 1

            if current_index >= len(rsave_list):
                current_index = 0

        except:
            pass

        await asyncio.sleep(REPLY_INTERVAL)


# ==========================
# TRACK DELETE
# ==========================
@bot.on(events.MessageDeleted)
async def track_delete(event):

    for uid, data in reply_targets.items():
        if data["base_msg_id"] in event.deleted_ids:
            data["base_msg_id"] = None
            data["mode"] = "mention"

# TRACK DELETE# ==========================
# REPLY ENGINE (REPLY + MENTION)
# ==========================
async def reply_engine():

    while True:
        await asyncio.sleep(REPLY_INTERVAL)

        if not rsave_list:
            continue

        for uid in list(reply_targets.keys()):

            data = reply_targets.get(uid)
            if not data:
                continue

            # ✅ EXPIRE CHECK (FIXED)
            if time.time() > data["expire"]:
                del reply_targets[uid]
                continue

            text = rsave_list[data["index"] % len(rsave_list)]
            data["index"] += 1

            try:

                # delete previous bot message
                if data["last_bot_msg"]:
                    try:
                        await bot.delete_messages(
                            data["chat_id"],
                            data["last_bot_msg"]
                        )
                    except:
                        pass

                # ==========================
                # REPLY MODE
                # ==========================
                if data["mode"] == "reply" and data["base_msg_id"]:

                    bot_msg = await bot.send_message(
                        data["chat_id"],
                        text,
                        reply_to=data["base_msg_id"]
                    )

                # ==========================
                # MENTION MODE
                # ==========================
                else:

                    if data["username"]:
                        mention_text = f"@{data['username']} {text}"
                        bot_msg = await bot.send_message(
                            data["chat_id"],
                            mention_text
                        )
                    else:
                        mention_text = f"<a href='tg://user?id={uid}'>User</a> {text}"
                        bot_msg = await bot.send_message(
                            data["chat_id"],
                            mention_text,
                            parse_mode="html"
                        )

                data["last_bot_msg"] = bot_msg.id

            except Exception as e:
                print("Reply Engine Error:", e)

# ==========================
# TROLL SYSTEM
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^ရိုက်သတ်"))
async def set_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်နတ်စောင်းကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")

    if not event.is_reply:
        return await event.reply("❌အသုံးပြုပုံမှားယွင်းနေပါတယ် (ရိုက်သတ်) <reply_user> .....။")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # 🚫 OWNER PROTECTION
    if is_owner(target_id):
        return await event.reply("သခင်နတ်စောင်းကို ဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

    troll_targets[target_id] = {
        "index": 0
    }

    await event.reply("တိုက်ခိုက်မှုကိုစတင်လိုက်ပါပီ ရပ်တန့်လိုပါက (ခွင့်လွတ်လိုက်) <reply> ....။")


@bot.on(events.NewMessage(pattern=r"(?i)^ခွင့်လွတ်လိုက်"))
async def unset_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")

    troll_targets.clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")


# ==========================
# AUTO MONITOR
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def monitor_messages(event):

    if event.sender_id is None:
        return

    # 🚫 OWNER IMMUNITY
    if is_owner(event.sender_id):
        return

    # ================= REPLY MODE =================
    if event.sender_id in reply_targets:

        texts = cursor.execute(
            "SELECT text FROM rsave ORDER BY id ASC"
        ).fetchall()

        if texts:

            data = reply_targets[event.sender_id]

            # 24h expire check
            if time.time() > data.get("expire", 0):
                del reply_targets[event.sender_id]
                return

            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1

            mention = f"<a href='tg://user?id={event.sender_id}'>User</a>"
            message = f"{mention}\n{text}"

            reply_mode = True

            # Check if last bot message deleted
            if data.get("last_bot_msg"):
                try:
                    await bot.get_messages(event.chat_id, ids=data["last_bot_msg"])
                except:
                    reply_mode = False

            try:
                if reply_mode:
                    msg = await event.reply(message, parse_mode="html")
                else:
                    msg = await bot.send_message(
                        event.chat_id,
                        message,
                        parse_mode="html"
                    )

                data["last_bot_msg"] = msg.id

            except:
                pass

            await asyncio.sleep(attack_speed)


    # ================= TROLL MODE =================
    if event.sender_id in troll_targets:

        texts = cursor.execute(
            "SELECT text FROM tsave ORDER BY id ASC"
        ).fetchall()

        if texts:

            data = troll_targets[event.sender_id]
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1

            try:
                await event.reply(text)
            except:
                pass

            await asyncio.sleep(attack_speed)

# ==========================
# GLOBAL VARIABLES
# ==========================
delete_targets = {}  # {target_id: chat_id}

# ==========================
# /delete COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^စာဖျက်လိုက်"))
async def set_delete(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied.")

    if not event.is_reply:
        return await event.reply("⚠️ Reply to target user to activate delete mode.")

    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id

    # OWNER IMMUNITY
    if is_owner(target_id):
        return await event.reply("⚠️ Cannot target the owner.")

    delete_targets[target_id] = event.chat_id
    await event.reply("✅ Delete mode activated for this user.")

# ==========================
# /undelete COMMAND (reply optional)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^စာပေးရေးလိုက်(?:\s+(\d+|all))?"))
async def unset_delete(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied.")

    # If reply exists → use reply_msg.sender_id
    target_id = None
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg:
            target_id = reply_msg.sender_id
    else:
        # If /undelete <user_id> or /undelete all
        arg = event.pattern_match.group(1)
        if arg:
            if arg.lower() == "all":
                delete_targets.clear()
                return await event.reply("✅ All delete targets removed.")
            else:
                try:
                    target_id = int(arg)
                except:
                    return await event.reply("⚠️ Invalid user ID.")

    if target_id:
        if target_id in delete_targets:
            del delete_targets[target_id]
            await event.reply(f"✅ Delete mode removed for user {target_id}.")
        else:
            await event.reply("⚠️ This user is not in delete mode.")
    else:
        await event.reply("⚠️ Reply to a user or provide user ID to remove delete mode.")

# ==========================
# AUTO DELETE MONITOR
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def auto_delete_monitor(event):
    if event.sender_id is None:
        return

    chat_id = event.chat_id

    # Skip owner messages
    if is_owner(event.sender_id):
        return

    # Collect target users + all bots in this chat
    target_ids = list(delete_targets.keys())  # target users
    async for user in bot.iter_participants(chat_id):
        if user.bot:
            target_ids.append(user.id)

    # If sender is a target user or a bot → delete message
    if event.sender_id in target_ids:
        try:
            await bot.delete_messages(chat_id, event.id)
        except Exception as e:
            print(f"Failed to delete message: {e}")

    # Delete messages replying to target users
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id in delete_targets:
            try:
                await bot.delete_messages(chat_id, event.id)
            except Exception as e:
                print(f"Failed to delete reply: {e}")

# ==========================
# ATT STORAGE
# ==========================
att_targets = {}  # user_id -> chat_id mapping

# ==========================
# /ATT (BOT ADMIN ONLY)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^ထိန်းချုပ်လိုက်$"))
async def set_att(event):
    try:
        # Only Bot Owner or Bot Admin can use
        if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
            return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")

        if not event.is_reply:
            return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")

        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id

        # Owner cannot be muted
        if is_owner(target_id):
            return await event.reply("⚠️ Owner ကို mute / control လုပ်လို့မရပါ။")

        # Add to ATT system
        att_targets[target_id] = event.chat_id
        await event.reply("✅ User ကို 10s Auto Mute System ထဲထည့်လိုက်ပါပြီ။")

    except Exception as e:
        print("ATT / ERROR:", e)
        await event.reply("⚠️ Bot မှာ တစ်စုံတစ်ရာ အမှားဖြစ်နေပါတယ်။ Admin ကို contact လုပ်ပါ။")

# ==========================
# /UNATT (BOT ADMIN ONLY)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^လွတ်ပေးလိုက်$"))
async def unset_att(event):
    try:
        if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
            return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")

        if not event.is_reply:
            return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")

        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id

        if target_id in att_targets:
            del att_targets[target_id]
            await event.reply("✅ User ကို Control System မှ ဖယ်ရှားလိုက်ပါပြီ။")
        else:
            await event.reply("⚠️ ဒီ User Control List ထဲမှာမရှိပါ။")

    except Exception as e:
        print("UNATT / ERROR:", e)
        await event.reply("⚠️ Bot မှာ တစ်စုံတစ်ရာ အမှားဖြစ်နေပါတယ်။ Admin ကို contact လုပ်ပါ။")

# ==========================
# AUTO CONTROL SYSTEM
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):
    try:
        user_id = event.sender_id
        chat_id = event.chat_id

        # Check if user is in ATT system for this chat
        if user_id not in att_targets or att_targets[user_id] != chat_id:
            return

        # MUTE user for 10 seconds
        await bot.edit_permissions(
            chat_id,
            user_id,
            send_messages=False
        )

        await asyncio.sleep(10)

        # UNMUTE user if still in ATT system
        if user_id in att_targets:
            await bot.edit_permissions(
                chat_id,
                user_id,
                send_messages=True
            )

    except Exception as e:
        print("AUTO CONTROL ERROR:", e)

# ==========================
# CALLING SYSTEM (Multi-Group Safe)
# ==========================

# store tasks and stop flags per chat
calling_tasks = {}   # key = chat_id, value = asyncio.Task
stop_flags = {}      # key = chat_id, value = bool

# ==========================
# /call COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^အကုန်ခေါ်(?:@\w+)? (.+)"))
async def start_calling(event):
    chat_id = event.chat_id
    text = event.pattern_match.group(1)

    # Permission check
    if not has_permission(event.sender_id):
        return await event.reply("❌ Permission denied")

    # Prevent duplicate task per group
    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        return await event.reply("⚠️ Calling already running in this group.")

    stop_flags[chat_id] = False
    calling_tasks[chat_id] = asyncio.create_task(calling_engine(chat_id, text))
    await event.reply("🔊🔊‌ခေါ်ဆိုမှုကိုစတင်လိုက်ပါပီ (မခေါ်နဲ့တော့) ဖြင့်ရပ်တန့်လို့ရသည်....။")

# ==========================
# /stopcall COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"မခေါ်နဲ့တော့$"))
async def stop_call(event):
    chat_id = event.chat_id

    # Permission check
    if not has_permission(event.sender_id):
        return await event.reply("❌ Permission denied")

    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        stop_flags[chat_id] = True
        await calling_tasks[chat_id]  # wait for task to finish
        await event.reply("🔇🔇ခေါ်ဆိုမှုကိုရပ်တန့်လိုက်ပါပီ...။")
    else:
        await event.reply("⚠️ No calling task running in this group.")

# ==========================
# CALLING ENGINE
# ==========================
async def calling_engine(chat_id, text):
    members = []
    async for user in bot.iter_participants(chat_id):
        members.append(user)

    batch_size = 5        # 5 members per batch
    delay_seconds = 2     # 2 seconds delay between batches
    total_members = len(members)

    for i in range(0, total_members, batch_size):
        if stop_flags.get(chat_id):
            break  # manual stop for this group

        batch = members[i:i + batch_size]

        mentions = [f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" for user in batch]
        message = " ".join(mentions) + "\n\n" + text

        try:
            await bot.send_message(chat_id, message, parse_mode="html")
        except Exception as e:
            print(f"Error sending batch in chat {chat_id}: {e}")

        await asyncio.sleep(delay_seconds)

    # Auto reset flag after finishing
    stop_flags[chat_id] = False
    calling_tasks.pop(chat_id, None)

PAGE_SIZE = 50  # စာ 50 ခုချင်းပြ

# ==========================
# Runtime One-Time Permission (Memory Only)
# ==========================
permitted_users = set()


# ==========================
# /Setadd (Owner Only)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Setadd"))
async def setadd_user(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("❌ Only owner can use /Setadd")

    if not event.is_reply:
        return await event.reply("❌ Reply to user to give permission")

    reply = await event.get_reply_message()
    user_id = reply.sender_id

    permitted_users.add(user_id)
    await event.reply("✅ One-time permission granted")


# ==========================
# /Unset (Owner Only)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Unset"))
async def unset_user(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("❌ Only owner can use /Unset")

    if not event.is_reply:
        return await event.reply("❌ Reply to user to remove permission")

    reply = await event.get_reply_message()
    user_id = reply.sender_id

    permitted_users.discard(user_id)
    await event.reply("✅ Permission removed")


# ==========================
# Save Attack (One-Time)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Asave (.+)"))
async def save_attack(event):

    # Owner အမြဲသုံးလို့ရ
    if event.sender_id == OWNER_ID:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Attack text saved (owner)")

    # Permission user တစ်ခါသုံး
    if event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()

        return await event.reply("✅ Attack text saved (permission used)")

    await event.reply("❌ Permission denied")


# ==========================
# Save Troll (One-Time)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Tsave (.+)"))
async def save_troll(event):

    # Owner အမြဲသုံးလို့ရ
    if event.sender_id == OWNER_ID:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Troll text saved (owner)")

    # Permission user တစ်ခါသုံး
    if event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()

        return await event.reply("✅ Troll text saved (permission used)")

    await event.reply("❌ Permission denied")

# ==========================
# Generic Show Page Function
# ==========================
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
    if page > 0:
        buttons.append(Button.inline("Previous", data=f"{title_prefix}_prev_{page-1}".encode()))
    if end < len(rows):
        buttons.append(Button.inline("Next", data=f"{title_prefix}_next_{page+1}".encode()))

    await event.reply(msg_text, buttons=buttons, parse_mode="html")


# ==========================
# List Attack (/Alist)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Alist"))
async def list_attack(event):
    rows = cursor.execute("SELECT id, text FROM asave").fetchall()
    if not rows:
        await event.reply("<blockquote>No attack texts saved.</blockquote>", parse_mode="html")
        return
    await show_page(event, rows, 0, "Attack List")


# ==========================
# List Troll (/Tlist)
# ==========================
@bot.on(events.NewMessage(pattern=r"/Tlist"))
async def list_troll(event):
    rows = cursor.execute("SELECT id, text FROM tsave").fetchall()
    if not rows:
        await event.reply("<blockquote>No troll texts saved.</blockquote>", parse_mode="html")
        return
    await show_page(event, rows, 0, "Troll List")


# ==========================
# Pagination Handler
# ==========================
@bot.on(events.CallbackQuery(pattern=b"(Attack List|Troll List)_(prev|next)_(\\d+)"))
async def paginate(event):
    # Decode bytes → str
    title, action, page = [x.decode() if isinstance(x, bytes) else x for x in event.pattern_match.groups()]
    page = int(page)

    if "Attack" in title:
        rows = cursor.execute("SELECT id, text FROM asave").fetchall()
    else:
        rows = cursor.execute("SELECT id, text FROM tsave").fetchall()

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_rows = rows[start:end]
    if not current_rows:
        await event.answer("No more pages.", alert=True)
        return

    msg_lines = [f"{r[0]}: {r[1]}" for r in current_rows]
    msg_text = f"<blockquote>{title}\n\n" + "\n".join(msg_lines) + "</blockquote>"

    buttons = []
    if page > 0:
        buttons.append(Button.inline("Previous", data=f"{title}_prev_{page-1}".encode()))
    if end < len(rows):
        buttons.append(Button.inline("Next", data=f"{title}_next_{page+1}".encode()))

    await event.edit(msg_text, buttons=buttons, parse_mode="html")
    await event.answer()

# ==========================
# /SENDS COMMAND (Owner Only + Auto Group Tracking)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^ဖြန့်လိုက်$"))
async def sends_command(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("❌ Owner Only.")

    if not event.is_reply:
        return await event.reply("Reply to a message to forward.")

    reply_msg = await event.get_reply_message()

    shared_count = 0
    failed_count = 0

    status_msg = await event.reply("📤 Forwarding started...")

    # Load all active groups from DB
    cursor.execute("SELECT chat_id FROM active_groups")
    groups = [row[0] for row in cursor.fetchall()]

    for group_id in groups:
        try:
            await bot.forward_messages(group_id, reply_msg)
            shared_count += 1
            await asyncio.sleep(1)
        except Exception as e:
            failed_count += 1
            continue

        await status_msg.edit(
            f"📤 Forwarding in progress...\n"
            f"✅ Success: {shared_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"⏳ Remaining: {len(groups) - (shared_count + failed_count)}"
        )

    await status_msg.edit(
        f"✅ Forwarding completed!\n"
        f"📦 Forwarded to: {shared_count} groups\n"
        f"❌ Failed: {failed_count} groups"
    )

# ==========================
# AUTO TRACK GROUPS (Any command used)
# ==========================
@bot.on(events.NewMessage)
async def track_groups(event):
    chat = await event.get_chat()
    chat_id = chat.id

    # Only track group chats
    if not getattr(chat, "megagroup", False) and not getattr(chat, "gigagroup", False) and not getattr(chat, "broadcast", False):
        return

    # Check if already stored
    cursor.execute("SELECT chat_id FROM active_groups WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO active_groups(chat_id) VALUES(?)", (chat_id,))
        conn.commit()
        print(f"📌 New active group tracked: {chat.title} ({chat_id})")

# ==========================
# Chat Info Command (Clean Quote Box)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^groupid"))
async def chat_info(event):
    chat = await event.get_chat()

    admins = await bot.get_participants(chat, filter=ChannelParticipantsAdmins)

    admin_text = ""
    for idx, a in enumerate(admins, start=1):
        admin_text += f"{idx}. {a.first_name}\n   {a.id}\n"

    if getattr(chat, 'megagroup', False) or getattr(chat, 'broadcast', False):
        group_id_display = f"-100{chat.id}"
    else:
        group_id_display = str(chat.id)

    msg = (
        "<blockquote>"
        f"Group Name: {chat.title}\n"
        f"Group ID: {group_id_display}\n\n"
        f"Admins:\n{admin_text}"
        "</blockquote>"
    )

# ==========================
# USER ID VIEW COMMAND
# ==========================

@bot.on(events.NewMessage(pattern=r"^သူ့စောက်ကြောင်း(?: (.+))?$"))
async def user_id(event):

    arg = event.pattern_match.group(1)

    try:
        # Reply user
        if event.is_reply:
            reply = await event.get_reply_message()
            user = await bot.get_entity(reply.sender_id)

        # Username or ID
        elif arg:
            user = await bot.get_entity(arg)

        # Self
        else:
            user = await bot.get_entity(event.sender_id)

        username = f"@{user.username}" if user.username else "No Username"

        msg = (
            "<blockquote>"
            f"Name : {user.first_name}\n"
            f"User ID : {user.id}\n"
            f"Username : {username}"
            "</blockquote>"
        )

        await event.reply(msg, parse_mode="html")

    except:
        await event.reply("User ရှာမတွေ့ပါ။ Username မှန်မမှန်စစ်ပါ။")
    await event.reply(msg, parse_mode="html")


# ==========================
# User Info Command (No Emoji, Quote Box)
# ==========================


@bot.on(events.NewMessage(pattern=r"/gplist"))
async def group_list(event):
    # SQLite ထဲမှာ groups table ထည့်ထားသင့်သည်
    cursor.execute("""CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY)""")
    rows = cursor.execute("SELECT id FROM groups").fetchall()
    if rows:
        msg = "\n".join([str(r[0]) for r in rows])
        await event.reply(f"📂 Groups:\n{msg}")
    else:
        await event.reply("No groups saved.")

from telethon import events

@bot.on(events.NewMessage(pattern=r"/Botadmlist"))
async def list_admins(event):
    rows = cursor.execute("SELECT id FROM bot_admins").fetchall()

    if not rows:
        await event.reply("<blockquote>⚠️ No Bot Admins assigned.</blockquote>", parse_mode="html")
        return

    msg_lines = []
    for r in rows:
        try:
            user = await bot.get_entity(r[0])
            name = user.first_name or "Unknown"
            msg_lines.append(f"{name} — {user.id}")
        except Exception:
            msg_lines.append(f"Unknown — {r[0]}")

    msg_text = "<blockquote>👮 Bot Admins:\n\n" + "\n".join(msg_lines) + "</blockquote>"

    await event.reply(msg_text, parse_mode="html")

# ==========================
# Admin Management (Reply Support)
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^မှတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def add_admin(event):

    if not is_owner(event.sender_id):
        return

    bot_mention = event.pattern_match.group(1)
    uid = event.pattern_match.group(2)

    me = await bot.get_me()

    if bot_mention:
        if bot_mention.lower() != me.username.lower():
            return await event.reply(f"This command is for @{me.username} only.")

    if event.is_reply:
        reply = await event.get_reply_message()
        uid = reply.sender_id

    elif uid:
        uid = int(uid)

    else:
        return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")

    cursor.execute(
        "INSERT OR IGNORE INTO bot_admins(user_id) VALUES(?)",
        (uid,)
    )
    conn.commit()

    await event.reply(f"✅ User `{uid}` ကို Bot Admin အဖြစ်ထည့်လိုက်ပါပြီ")

# ==========================
# Remove Admin
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^ဖြုတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def remove_admin(event):

    if not is_owner(event.sender_id):
        return

    bot_mention = event.pattern_match.group(1)
    uid = event.pattern_match.group(2)

    me = await bot.get_me()

    if bot_mention:
        if bot_mention.lower() != me.username.lower():
            return await event.reply(f"This command is for @{me.username} only.")

    if event.is_reply:
        reply = await event.get_reply_message()
        uid = reply.sender_id

    elif uid:
        uid = int(uid)

    else:
        return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")

    cursor.execute(
        "DELETE FROM bot_admins WHERE user_id=?",
        (uid,)
    )
    conn.commit()

    await event.reply(f"❌ User `{uid}` ကို Bot Admin မှ ဖယ်ရှားလိုက်ပါပြီ")

@bot.on(events.ChatAction)
async def bot_added(event):
    if event.user_added:
        me = await bot.get_me()

        if event.user_id == me.id and event.action_message:
            adder = await bot.get_entity(event.action_message.from_id)

            bot_name = me.first_name
            adder_mention = f"<a href='tg://user?id={adder.id}'>{adder.first_name}</a>"

            await event.reply(
                "<blockquote>"
                f"ကောင်းကင်စီးနှင်းသူလို့လူသိများတဲ့ {bot_name} ရောက်ရှိလာပါပီ {adder_mention} တေးသံလိုညိမ့်‌ညောင်းတဲ့တိုက်ခိုက်မှုကိုစတင်ရန် (သတ်ပလိုက်))Reply Or Uuser အသုံးပြုပါ.....။ "
                "</blockquote>",
                parse_mode="html",
                link_preview=False
            )


# ==========================
# /အကူအညီ COMMAND (မြန်မာလို၊ Emoji မပါ)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^အကူအညီ$"))
async def helps_command(event):

    help_text = (
        "<blockquote>"
        "BOT COMMANDS GUIDE (မြန်မာလို)\n"
        "════════════════════════\n\n"

        "1. Attack & Spam Commands\n"
        "─────────────────────────\n"
        "• သတ်ပလိုက်  - User ကို Spam စတင် (Reply optional)\n"
        "• ရပ်တော့  - Attack Spam အားလုံး ရပ်ရန်\n"
        "• အရှိန် <time>  - Spam speed သတ်မှတ်ရန် (0.001 အမြန်ဆုံး)\n"
        "    - 0.1s နဲ့အောက်ဆို Auto=1 ဖြစ်သွားပါမယ်\n\n"

        "2. Auto Reply System\n"
        "─────────────────────────\n"
        "• လွတ်အောင်ပြေး  - Auto Reply စတင် (Reply လုပ်ရမည်)\n"
        "• ပေးနားလိုက်  - Auto Reply ရပ်ရန် (Reply user အတွက်သာ)\n\n"

        "3. Troll System\n"
        "─────────────────────────\n"
        "• ရိုက်သတ်  - Troll Spam စတင် (Reply လုပ်ရမည်)\n"
        "• ခွင့်လွတ်လိုက်  - Troll Spam ရပ်ရန်\n\n"

        "4. Message Control\n"
        "─────────────────────────\n"
        "• စာဖျက်လိုက်  - Reply Message Delete\n"
        "• စာပေးရေးလိုက်  - Delete Function ရပ်ရန်\n\n"

        "5. Group Functions\n"
        "─────────────────────────\n"
        "• အကုန်ခေါ် <text>  - Group Members အားလုံး Mention\n"
        "• မခေါ်နဲ့တော့  - Mention Function ရပ်ရန်\n"

        "6. CTC Reply System\n"
        "─────────────────────────\n"
        "• စလိုက် <id1> <id2> - Reply & Mention Mode စတင်\n"
        "    → User1 reply → User2 ကို mention\n"
        "• တော်တော့ - Reply & Mention Mode ရပ်ရန်\n\n"

        "7. Moderation Commands\n"
        "─────────────────────────\n"
        "• /ban - Reply User Ban လုပ်ရန်\n"
        "• /unban - Reply User Unban လုပ်ရန်\n"
        "• /mute <time> - Reply User Mute (10m / 1h / 1d)\n"
        "• /unmute - Reply User Manual Unmute\n\n"

        "8. Filter System\n"
        "─────────────────────────\n"
        "• /filter <trigger> <reply> - Trigger message reply setup\n"
        "    → User message တူရင် Bot automatically reply\n\n"

        "9. Control System\n"
        "─────────────────────────\n"
        "• ထိန်းချုပ်လိုက်  - User စာရေးတိုင်း 10 စက္ကန့် Mute\n"
        "• လွတ်ပေးလိုက်  - 10 စက္ကန့် Mute System ရပ်ရန်\n\n"

        "10. Translation\n"
        "─────────────────────────\n"
        "• ဘာသာပြန်မယ်  - 120 languages အထိ ဘာသာပြန်နိုင်\n\n"
        "• /Report - ဘော့အသုံးပြသူရဲ့စည်ကမ်းမဲ့မှုအတွက်သတင်းပို့ရန်\n "

        "11. Info Commands\n"
        "─────────────────────────\n"
        "• သူ့စောက်ကြောင်း <id/user>  - User Info ကြည့်ရန်\n"
        "• groupid  - လက်ရှိ Group ID ကြည့်ရန်\n\n"

        "12. Extra Features\n"
        "─────────────────────────\n"
        "• Group Members Count Auto Show\n"
        "• Group Admin Count Auto Track\n"
        "• Speed Limit Protection ပါရှိ\n"
        "• Premium Emoji Support ပါရှိ\n\n"

        "════════════════════════\n"
        "( အကူအညီ ) ကို လူတိုင်း အသုံးပြုနိုင်ပါသည်\n"
        "</blockquote>"
    )

    await event.reply(help_text, parse_mode="html")

LANGUAGES = {
    "Afrikaans": "af",
    "Albanian": "sq",
    "Amharic": "am",
    "Arabic": "ar",
    "Armenian": "hy",
    "Azerbaijani": "az",
    "Basque": "eu",
    "Belarusian": "be",
    "Bengali": "bn",
    "Bosnian": "bs",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Cebuano": "ceb",
    "Chinese (Simplified)": "zh-cn",
    "Chinese (Traditional)": "zh-tw",
    "Corsican": "co",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Esperanto": "eo",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "Frisian": "fy",
    "Galician": "gl",
    "Georgian": "ka",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Haitian Creole": "ht",
    "Hausa": "ha",
    "Hawaiian": "haw",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hmong": "hmn",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Igbo": "ig",
    "Indonesian": "id",
    "Irish": "ga",
    "Italian": "it",
    "Japanese": "ja",
    "Javanese": "jw",
    "Kannada": "kn",
    "Kazakh": "kk",
    "Khmer": "km",
    "Korean": "ko",
    "Kurdish (Kurmanji)": "ku",
    "Kyrgyz": "ky",
    "Lao": "lo",
    "Latin": "la",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Luxembourgish": "lb",
    "Macedonian": "mk",
    "Malagasy": "mg",
    "Malay": "ms",
    "Malayalam": "ml",
    "Maltese": "mt",
    "Maori": "mi",
    "Marathi": "mr",
    "Mongolian": "mn",
    "Myanmar": "my",
    "Nepali": "ne",
    "Norwegian": "no",
    "Nyanja (Chichewa)": "ny",
    "Odia (Oriya)": "or",
    "Pashto": "ps",
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Punjabi": "pa",
    "Romanian": "ro",
    "Russian": "ru",
    "Samoan": "sm",
    "Scots Gaelic": "gd",
    "Serbian": "sr",
    "Sesotho": "st",
    "Shona": "sn",
    "Sindhi": "sd",
    "Sinhala (Sinhalese)": "si",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Somali": "so",
    "Spanish": "es",
    "Sundanese": "su",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tagalog (Filipino)": "tl",
    "Tajik": "tg",
    "Tamil": "ta",
    "Tatar": "tt",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Turkmen": "tk",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Uyghur": "ug",
    "Uzbek": "uz",
    "Vietnamese": "vi",
    "Welsh": "cy",
    "Xhosa": "xh",
    "Yiddish": "yi",
    "Yoruba": "yo",
    "Zulu": "zu"
}

# Session store for users
user_state = {}

# =========================
# /translate Command
# =========================
@bot.on(events.NewMessage(pattern=r'^ဘာသာပြန်မယ်$', incoming=True))
async def translate_cmd(event):
    if not event.is_reply:
        return await event.reply("Reply ထောက်ပြီး /translate သုံးပါ")

    reply_msg = await event.get_reply_message()
    if not reply_msg.text:
        return await event.reply("Text မရှိပါ")

    user_state[event.sender_id] = {
        "original": reply_msg.text,
        "waiting_language": True
    }

    await event.reply(
        "🌐 ဘာသာစကားနာမည် ရိုက်ပါ (ဥပမာ: English, Japanese, Myanmar (Burmese))"
    )

# =========================
# Language Input & Pagination
# =========================
@bot.on(events.NewMessage(incoming=True))
async def language_input(event):
    user_id = event.sender_id
    if user_id not in user_state:
        return
    if not user_state[user_id].get("waiting_language"):
        return

    lang_name = event.text.strip()
    if lang_name not in LANGUAGES:
        return await event.reply(
            "❌ Language မမှန်ပါ။ English / Japanese / Myanmar (Burmese) လို အပြည့်အစုံရိုက်ပါ"
        )

    lang_code = LANGUAGES[lang_name]
    original = user_state[user_id]["original"]
    translated = translator.translate(original, dest=lang_code).text

    # Store pages
    user_state[user_id]["waiting_language"] = False
    user_state[user_id]["pages"] = [
        f"<blockquote>Original Message:\n{original}</blockquote>",
        f"<blockquote>Translated ({lang_name}):\n{translated}</blockquote>"
    ]
    user_state[user_id]["current_page"] = 0

    # Send first page with buttons
    await event.reply(
        user_state[user_id]["pages"][0],
        parse_mode="html",
        buttons=[
            [Button.inline("Next ▶", data=f"next_{user_id}")]
        ]
    )

# =========================
# Button Callback Handler
# =========================
@bot.on(events.CallbackQuery)
async def page_callback(event):
    data = event.data.decode("utf-8")
    user_id = int(data.split("_")[-1])
    if user_id not in user_state:
        return await event.answer("Session expired ❌", alert=True)

    page_data = user_state[user_id]
    current = page_data["current_page"]

    if data.startswith("next"):
        next_page = current + 1
        if next_page >= len(page_data["pages"]):
            return await event.answer("End of pages ❌", alert=True)
        page_data["current_page"] = next_page

        if next_page == 1:
            buttons = [
                [Button.inline("◀ Previous", data=f"prev_{user_id}")]
            ]
        else:
            buttons = [
                [Button.inline("◀ Previous", data=f"prev_{user_id}"),
                 Button.inline("Next ▶", data=f"next_{user_id}")]
            ]

        await event.edit(
            page_data["pages"][next_page],
            parse_mode="html",
            buttons=buttons
        )

    elif data.startswith("prev"):
        prev_page = current - 1
        if prev_page < 0:
            return await event.answer("Start of pages ❌", alert=True)
        page_data["current_page"] = prev_page

        if prev_page == 0:
            buttons = [
                [Button.inline("Next ▶", data=f"next_{user_id}")]
            ]
        else:
            buttons = [
                [Button.inline("◀ Previous", data=f"prev_{user_id}"),
                 Button.inline("Next ▶", data=f"next_{user_id}")]
            ]

        await event.edit(
            page_data["pages"][prev_page],
            parse_mode="html",
            buttons=buttons
        )

# ==========================
# BAN / UNBAN / MUTE / UNMUTE
# ==========================

# Helper for time parsing
def parse_time(text):
    seconds = 0
    if text:
        match = re.match(r"(\d+)([mhd])", text.lower())
        if match:
            num, unit = match.groups()
            num = int(num)
            if unit == "m":
                seconds = num * 60
            elif unit == "h":
                seconds = num * 3600
            elif unit == "d":
                seconds = num * 86400
    else:
        seconds = 600  # default 10m
    return seconds

# ==========================
# /BAN
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/ban$"))
async def ban_user(event):

    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)):
        return await event.reply("❌ Admin only.")

    if not event.is_reply:
        return await event.reply("⚠️ Reply to the user you want to ban.")

    # -------- BOT PERMISSION CHECK --------
    perms = await bot.get_permissions(event.chat_id, "me")

    if not perms.is_admin:
        return await event.reply("⚠️ Bot က Admin မဟုတ်ပါ။")

    if not perms.ban_users:
        return await event.reply("⚠️ Bot မှာ Ban Permission မရှိပါ။")

    reply = await event.get_reply_message()
    target = reply.sender_id

    if is_owner(target):
        return await event.reply("⚠️ Owner cannot be banned.")

    try:
        await bot.edit_permissions(
            event.chat_id,
            target,
            view_messages=False
        )

        await event.reply("🚫 User banned successfully.")

    except:
        await event.reply("⚠️ Ban လုပ်လို့မရပါ။ Bot permission ကိုစစ်ပါ။")


# ==========================
# /UNBAN
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/unban$"))
async def unban_user(event):

    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)):
        return await event.reply("❌ Admin only.")

    if not event.is_reply:
        return await event.reply("⚠️ Reply to the user you want to unban.")

    # -------- BOT PERMISSION CHECK --------
    perms = await bot.get_permissions(event.chat_id, "me")

    if not perms.is_admin:
        return await event.reply("⚠️ Bot က Admin မဟုတ်ပါ။")

    if not perms.ban_users:
        return await event.reply("⚠️ Bot မှာ Unban Permission မရှိပါ။")

    reply = await event.get_reply_message()
    target = reply.sender_id

    try:
        await bot.edit_permissions(
            event.chat_id,
            target,
            view_messages=True,
            send_messages=True
        )

        await event.reply("✅ User unbanned successfully.")

    except:
        await event.reply("⚠️ Unban လုပ်လို့မရပါ။ Bot permission ကိုစစ်ပါ။")

# ==========================
# /MUTE (with optional time)
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/mute(?:\s+(.+))?$"))
async def mute_user(event):

    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)):
        return await event.reply("❌ Admin only.")

    if not event.is_reply:
        return await event.reply("⚠️ Reply to the user you want to mute.")

    # -------- BOT PERMISSION CHECK --------
    perms = await bot.get_permissions(event.chat_id, "me")

    if not perms.is_admin:
        return await event.reply("⚠️ Bot က Admin မဟုတ်ပါ။")

    if not perms.ban_users:
        return await event.reply("⚠️ Bot မှာ Mute Permission မရှိပါ။")

    reply = await event.get_reply_message()
    target = reply.sender_id

    if is_owner(target):
        return await event.reply("⚠️ Owner cannot be muted.")

    text = event.pattern_match.group(1)
    seconds = parse_time(text)

    try:
        await bot.edit_permissions(
            event.chat_id,
            target,
            send_messages=False
        )

        await event.reply(f"🔇 User muted for {text if text else '10m'}")

        if seconds > 0:
            await asyncio.sleep(seconds)

            await bot.edit_permissions(
                event.chat_id,
                target,
                send_messages=True
            )

            try:
                await event.reply(f"🔊 User auto unmuted after {text if text else '10m'}")
            except:
                pass

    except:
        await event.reply("⚠️ Mute လုပ်လို့မရပါ။ Bot permission ကိုစစ်ပါ။")


# ==========================
# /UNMUTE
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/unmute$"))
async def unmute_user(event):

    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)):
        return await event.reply("❌ Admin only.")

    if not event.is_reply:
        return await event.reply("⚠️ Reply to the user you want to unmute.")

    # -------- BOT PERMISSION CHECK --------
    perms = await bot.get_permissions(event.chat_id, "me")

    if not perms.is_admin:
        return await event.reply("⚠️ Bot က Admin မဟုတ်ပါ။")

    if not perms.ban_users:
        return await event.reply("⚠️ Bot မှာ Unmute Permission မရှိပါ။")

    reply = await event.get_reply_message()
    target = reply.sender_id

    try:
        await bot.edit_permissions(
            event.chat_id,
            target,
            send_messages=True
        )

        await event.reply("🔊 User manually unmuted")

    except:
        await event.reply("⚠️ Unmute လုပ်လို့မရပါ။ Bot permission ကိုစစ်ပါ။")

# ==========================
# /Filter
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/filter"))
async def add_filter(event):

    if not (is_owner(event.sender_id) or is_bot_admin(event.sender_id)):
        return await event.reply("❌ Admin only.")

    args = event.raw_text.split(maxsplit=2)

    if len(args) < 3:
        return await event.reply("Usage:\n/Filter trigger reply")

    trigger = args[1].lower()
    reply = args[2]

    cursor.execute(
        "INSERT INTO filters (chat_id, trigger, reply) VALUES (?, ?, ?)",
        (event.chat_id, trigger, reply)
    )
    conn.commit()

    await event.reply(f"✅ Filter added\nTrigger : {trigger}")

# ==========================
# FILTER LISTENER
# ==========================
@bot.on(events.NewMessage(incoming=True))
async def filter_reply(event):

    if event.raw_text is None:
        return

    text = event.raw_text.lower()

    cursor.execute(
        "SELECT trigger, reply FROM filters WHERE chat_id=?",
        (event.chat_id,)
    )

    rows = cursor.fetchall()

    for trigger, reply in rows:

        if text == trigger:
            await event.reply(reply)
            break

ban_tracker = {}
alert_lock = {}

BAN_THRESHOLD = 10  # Minimum group members to trigger

@bot.on(events.ChatAction)
async def auto_owner_alert(event):
    chat_id = event.chat_id

    # Initialize trackers
    if chat_id not in ban_tracker:
        ban_tracker[chat_id] = []
    if chat_id not in alert_lock:
        alert_lock[chat_id] = False

    # Detect Ban / Kick
    if event.user_kicked:
        banned_user = await event.get_user()
        banned_by = event.action_message.sender

        # Auto detect Owner
        participants = await bot.get_participants(chat_id, filter=ChannelParticipantsAdmins)
        owner = next((p for p in participants if getattr(p.participant, "creator", False)), None)
        if not owner:
            return
        OWNER_ID = owner.id
        OWNER_NAME = owner.first_name

        # Skip Bot / Owner self-action
        me = await bot.get_me()
        if banned_by.id in [me.id, OWNER_ID]:
            return

        # Track banner
        ban_tracker[chat_id].append(banned_by.first_name)

        # Check total members
        total_members = len(await bot.get_participants(chat_id))
        if total_members <= BAN_THRESHOLD:
            return

        # Throttle Alert: send only once per 1 second
        if not alert_lock[chat_id]:
            alert_lock[chat_id] = True
            banners_str = ", ".join(list(set(ban_tracker[chat_id])))
            alert_msg = (
                f"<blockquote>{OWNER_NAME} သတိပေးချက်\n\n"
                f"{banners_str} က Group Members တွေကို Ban လုပ်နေပါတယ်။\n"
                f"အထူးသတိပြုပါ။</blockquote>"
            )
            await bot.send_message(OWNER_ID, alert_msg, parse_mode="html")

            # Reset lock after 1 second
            await asyncio.sleep(1)
            alert_lock[chat_id] = False
            ban_tracker[chat_id] = []  # Clear tracker for next batch

# =============================
# Bot State
# =============================
ctc_active = False
user1_id = None
user2_id = None

# =============================
# /Ctc Command
# =============================
@bot.on(events.NewMessage(pattern=r'^စလိုက်'))
async def start_ctc(event):
    global ctc_active, user1_id, user2_id
    sender = event.sender_id

    if not (is_owner(sender) or is_admin(sender)):
        await event.reply("❌ You are not allowed to use this command.")
        return

    # Parse Command
    try:
        parts = event.raw_text.split()
        user1_id = int(parts[1])
        user2_id = int(parts[2])
    except:
        await event.reply("❌ Usage: စလိုက် <user1_id> <user2_id>")
        return

    ctc_active = True
    await event.reply(f" Trolling Mode Activated for {user1_id} & {user2_id}")

# =============================
# /Unctc Command
# =============================
@bot.on(events.NewMessage(pattern=r'^တော်တော့'))
async def stop_ctc(event):
    global ctc_active, user1_id, user2_id
    sender = event.sender_id

    if not (is_owner(sender) or is_admin(sender)):
        await event.reply("❌ You are not allowed to use this command.")
        return

    ctc_active = False
    user1_id = None
    user2_id = None
    await event.reply(" Trolling Mode Deactivated.")

# =============================
# Message Listener
# =============================
@bot.on(events.NewMessage(incoming=True))
async def handle_message(event):
    global user1_id, user2_id

    if not ctc_active:
        return

    sender = event.sender_id
    text = event.raw_text

    # Only react to user1 or user2
    if sender not in (user1_id, user2_id):
        return

    # Determine target
    target_id = user2_id if sender == user1_id else user1_id
    target_entity = await bot.get_entity(target_id)

    # Reply & mention with original message content
    await event.reply(f"{text} <a href='tg://user?id={target_entity.id}'>{target_entity.first_name}</a>", parse_mode="html")

# =========================
# Anti-Spam / Link Detection (Quote + Mention)
# =========================
@bot.on(events.NewMessage(incoming=True))
async def anti_spam(event):
    if event.is_private:
        return

    try:
        sender = await event.get_sender()
        if not sender:
            return

        # Skip admins / creator
        perms = await bot.get_permissions(event.chat_id, sender.id)
        if perms.is_creator or perms.is_admin:
            return

        text = (event.raw_text or "").lower()
        is_forward = bool(event.forward)
        is_link = any(word in text for word in LINK_WORDS)
        is_mention = bool(re.search(r'@\w+', text))

        if is_forward or is_link or is_mention:
            try:
                await event.delete()
            except errors.ChatAdminRequiredError:
                print("Bot needs delete permission")
                return

            chat = await event.get_chat()
            name_mention = f"<a href='tg://user?id={sender.id}'>{sender.first_name}</a>"
            chat_name = chat.title or "Group"

            msg_text = (
                f"<blockquote>{name_mention} ဟိတ် {chat_name} မာ စည်းကမ်းမရှိလာမလုပ်နဲ့\n"
                "မင်းစာကိုဖျက်ပလိုက်ပီ ❌</blockquote>"
            )

            await event.reply(msg_text, parse_mode="html")

    except Exception as e:
        print("AntiSpam Error:", e)

# ==========================
# AUTO WELCOME SYSTEM
# ==========================

WELCOME_TEXT = """
{mention_name} ကြိုဆိုပါတယ် လာလည်ရင်းစကားလေးတွေဝင်ပြောပီးလူလေးထည့်ပေးပေါ့။

Name - {mention_name}
Id - {user_id}
User - {user_name}
Groups - {group}

{groups_name} ကပျော်ဖို့ကောင်းပါတယ် Group ထဲမာနေရင်စည်းကမ်းလေးလိုက်နာပီးတော့ပျော်ပျော်ရွှင်ရွှင်နေပါနော။
"""

@bot.on(events.ChatAction)
async def auto_welcome(event):

    # အသစ်ဝင်လာတဲ့ User တွေကိုသာ စစ်ပါ
    if not (event.user_joined or event.user_added):
        return

    chat = await event.get_chat()
    users = await event.get_users()

    for user in users:

        # User Info
        name = user.first_name
        user_id = user.id
        user_mention = f"<a href='tg://user?id={user_id}'>{name}</a>"

        if user.username:
            user_name = "@" + user.username
        else:
            user_name = "None"

        group_name = chat.title

        text = WELCOME_TEXT
        text = text.replace("{mention_name}", user_mention)
        text = text.replace("{user_id}", str(user_id))
        text = text.replace("{user_name}", user_name)
        text = text.replace("{group}", group_name)
        text = text.replace("{groups_name}", group_name)

        # Message Send
        await bot.send_message(
            event.chat_id,
            f"<blockquote>{text}</blockquote>",
            parse_mode="html"
        )

# ==========================
# Goodbye System (Friendly)
# ==========================
@bot.on(events.ChatAction)
async def goodbye_user(event):
    # Detect user left / kicked
    if event.user_left or event.user_kicked:
        try:
            user = await bot.get_entity(event.user_id)
            name_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            chat = await event.get_chat()
            group_name = chat.title or "Group"

            msg_text = (
                f"<blockquote>{name_mention} အော်မင်းလဲ {group_name} ကနေနောက်ဆုံးတော့မင်းလဲထွက်သွားတာပါပဲ\n"
                "နောက်ကျရင်လဲ ပြန်လာလည်ဖို့ဖိတ်ခေါ်လိုက်ပါတယ် အမြဲကြိုဆိုနေပါတယ်။</blockquote>"
            )

            await event.reply(msg_text, parse_mode="html")
        except Exception:
            pass

# ==========================
# AniList Functions
# ==========================
def fetch_anime_title(anilist_id: int):
    """
    Fetch anime title from AniList by ID
    """
    query = """
    query ($id: Int) {
      Media (id: $id, type: ANIME) {
        title {
          romaji
          english
          native
        }
      }
    }
    """
    variables = {"id": anilist_id}
    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
            timeout=10
        )
        data = response.json()
        media = data["data"]["Media"]
        title = media["title"]["english"] or media["title"]["romaji"]
        return title
    except:
        return "Unknown"

def fetch_characters(anilist_id: int):
    """
    Fetch top 3 characters of the anime
    """
    query = """
    query ($id: Int) {
      Media (id: $id, type: ANIME) {
        characters(sort: ROLE) {
          edges {
            node {
              name {
                full
              }
            }
          }
        }
      }
    }
    """
    variables = {"id": anilist_id}
    try:
        response = requests.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
            timeout=10
        )
        data = response.json()
        edges = data["data"]["Media"]["characters"]["edges"]
        return [e["node"]["name"]["full"] for e in edges[:3]]  # top 3 characters
    except:
        return ["Unknown"]

# ==========================
# /Wa Command Handler
# ==========================
@bot.on(events.NewMessage(pattern=r"^နံမည်$"))
async def wa_handler(event):
    """
    Handles /Wa command: replies to photo/video and searches anime
    """
    if not event.is_reply:
        return await event.reply("❌ Reply to a Photo or Video.")

    reply = await event.get_reply_message()
    if not (reply.photo or reply.video):
        return await event.reply("❌ Reply must be a Photo or Video.")

    file_path = await reply.download_media()

    try:
        # Send image to trace.moe API
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("image", f)
                async with session.post(TRACE_API, data=data) as resp:
                    result = await resp.json()

        if not result.get("result"):
            return await event.reply("❌ No Anime Found.")

        results = result["result"]
        best = results[0]
        similarity = best["similarity"]

        # -------- EXACT MATCH (>=92%) --------
        if similarity >= 0.92:
            title = fetch_anime_title(best["anilist"])
            characters = fetch_characters(best["anilist"])
            text = (
                f"<blockquote>❝ 𝗔𝗡𝗜𝗠𝗘 𝗗𝗘𝗧𝗘𝗖𝗧𝗘𝗗 ❞\n\n"
                f"🎬 {title}\n"
                f"👤 Main Characters: {', '.join(characters)}\n"
                f"📺 Episode: {best.get('episode', 'Unknown')}\n"
                f"🎯 Accuracy: {round(similarity*100,2)}%</blockquote>"
            )
            await event.reply(text, parse_mode="html")

        # -------- CLOSE MATCH (TOP 5) --------
        else:
            text = "<blockquote>❝ 𝗣𝗢𝗦𝗦𝗜𝗕𝗟𝗘 𝗠𝗔𝗧𝗖𝗛𝗘𝗦 ❞\n\n"
            for i, item in enumerate(results[:5], 1):
                title = fetch_anime_title(item["anilist"])
                characters = fetch_characters(item["anilist"])
                sim = round(item["similarity"]*100,2)
                text += f"{i}. {title} | Characters: {', '.join(characters)} ({sim}%)\n"
            text += "</blockquote>"
            await event.reply(text, parse_mode="html")

    except Exception as e:
        await event.reply(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ==========================
# AUTO ANTI-SPAM VARIABLES
# 5 seconds / 4 messages → 20 seconds Mute
# ==========================
user_messages = defaultdict(list)

@bot.on(events.NewMessage)
async def auto_antispam(event):

    if event.is_private:
        return

    user_id = event.sender_id
    chat_id = event.chat_id
    now = time.time()

    # Bot Owner skip
    if user_id == BOT_OWNER_ID:
        return

    # User message log
    user_messages[user_id].append(now)

    # 5 စက္ကန့်အတွင်း Messages
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 5]

    # 4 messages ထက်ပိုရင် Spam
    if len(user_messages[user_id]) >= 4:

        try:
            # 20 စက္ကန့် Mute
            await bot.edit_permissions(
                chat_id,
                user_id,
                send_messages=False
            )

            # Quote Box Warning
            await event.reply(
                f"<blockquote>⚠️ သတိပေးချက်\n"
                f"<a href='tg://user?id={user_id}'>ဟိတ်</a>\n"
                f"5 စက္ကန့်အတွင်း စာ ၄ ကြောင်း ဆက်တိုက် Spam လုပ်သဖြင့် 20 စက္ကန့်စာရေးခွင့် ပိတ်ထားပါသည်။\n"
                f"Group စည်းကမ်းကိုလိုက်နာပါ။</blockquote>",
                parse_mode="html",
                reply_to=event.message.id
            )

            # 20 စက္ကန့်
            await asyncio.sleep(20)

            # Auto Unmute
            await bot.edit_permissions(
                chat_id,
                user_id,
                send_messages=True
            )

            await event.reply(
                f"<blockquote><a href='tg://user?id={user_id}'>ဟိတ်</a> 20 စက္ကန့်ပြည့်ပြီး စာရေးနိုင်ပါပြီ။</blockquote>",
                parse_mode="html",
                reply_to=event.message.id
            )

        except Exception as e:
            print(f"Anti-Spam Error: {e}")

        user_messages[user_id] = []
# ==========================
# OWNER_ID Only Report System
# ==========================

@bot.on(events.NewMessage(pattern=r"(?i)^/report(?: |$)(.*)"))
async def user_report(event):
    """
    Usage:
    Reply to a user's message with:
    /report <reason>
    Report will be sent ONLY to OWNER_ID
    """

    if not event.is_reply:
        await event.reply("Report လုပ်ချင်တဲ့ User ကို Reply လုပ်ပြီး /report <အကြောင်းပြချက်> ရိုက်ပါ။")
        return

    reported_user = await event.get_reply_message()
    reporter_id = event.sender_id
    reported_id = reported_user.sender_id
    reason = event.pattern_match.group(1).strip()
    if not reason:
        reason = "No reason provided"

    # Report message
    report_msg = (
        f"<b>User Report</b>\n"
        f"Reporter: <a href='tg://user?id={reporter_id}'>User</a>\n"
        f"Reported: <a href='tg://user?id={reported_id}'>User</a>\n"
        f"Reason: {reason}\n"
        f"Chat: {event.chat_id}\n"
    )

    try:
        # Send ONLY to OWNER_ID
        await bot.send_message(OWNER_ID, report_msg, parse_mode="html")
        await event.reply("Report လုပ်ပြီးပါပြီ။ Owner သို့ပို့ပြီးပါပြီ။")
    except Exception as e:
        await event.reply("Report ပို့မရနိုင်ပါ။ Owner ကိုစစ်ပါ။")
        print(f"Report Error: {e}")

# =====================
# MEMORY
# =====================

time_users = {}


# =====================
# /time COMMAND
# =====================

@bot.on(events.NewMessage(pattern=r'^အချိန် (\d+)([smhd])'))
async def set_time(event):

    if not event.is_reply:
        return await event.reply("❌ Reply user message")

    reply = await event.get_reply_message()
    user_id = reply.sender_id

    amount = int(event.pattern_match.group(1))
    unit = event.pattern_match.group(2)

    seconds = amount

    if unit == "s":
        seconds = amount
    elif unit == "m":
        seconds = amount * 60
    elif unit == "h":
        seconds = amount * 3600
    elif unit == "d":
        seconds = amount * 86400

    expire = time.time() + seconds
    time_users[user_id] = expire

    await event.reply(f"⏰ Time set for {amount}{unit}")


# =====================
# CHECK FUNCTION
# =====================

def has_time(user_id):

    if user_id in time_users:

        if time.time() < time_users[user_id]:
            return True

    return False

# ==========================
# BAN ALL (BOT + USER)
# ==========================
BAN_DELAY = 0.1  # seconds per member

@bot.on(events.NewMessage(pattern=r"(?i)^ဖျက်ချလိုက်$"))
async def ban_all(event):

    if event.sender_id != OWNER_ID:
        return await event.reply("Owner only command.")

    participants = []
    async for user in bot.iter_participants(event.chat_id):
        participants.append(user)

    total_members = len(participants)

    status = await event.reply(
        f"[❄️] ဖျက်သိမ်းခြင်းကိုစတင်လိုက်ပါပီ [❄️]\n\n"

        f"[👾] စုစုပေါင်းအရေအတွက်: {total_members}\n"

        f"[⚡️]အမြန်နှုန်း: {BAN_DELAY}s per member\n\n"

        f"Processing..."
    )

    rights = ChatBannedRights(
        until_date=None,
        view_messages=True
    )

    count = 0
    start_time = time.time()

    for user in participants:

        try:
            # Skip Bot Owner
            if user.id == OWNER_ID:
                continue

            # Check admin / owner status
            perms = await bot.get_permissions(event.chat_id, user.id)

            if perms.is_admin:
                continue  # Skip group owner & admins

            await bot(EditBannedRequest(
                event.chat_id,
                user.id,
                rights
            ))

            count += 1

            elapsed = time.time() - start_time
            remaining = (total_members - count) * BAN_DELAY
            remaining_min = round(remaining / 60, 2)

            await status.edit(
                f"[❄️] ဖျက်သိမ်းနေပါပီ [❄️]\n\n"

                f"[👾] စုစုပေါင်း : {total_members}\n"

                f"[⚡️] ဖျက်သိမ်းခြင်း : {count}\n"

                f"[⏳] ကြာချိန် : {remaining_min} min"
            )

            await asyncio.sleep(BAN_DELAY)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)

        except:
            continue

    await status.edit(
        f"[💠]ဖျက်သိမ်းခြင်းအောင်မြင်စွာပီးစီး[💠]\n\n"

        f"[☃️] စုစုပေါင်းအရေအတွက် : {total_members}\n"

        f"[🚫] ပိတ်ပင်ခံရသောအရေအတွက်  : {count}"
    )

notified_bots = {}  # {chat_id: set(bot_user_ids)}

@bot.on(events.ChatAction())
async def anti_bot_join(event):
    # Only check join events
    if not (event.user_added or event.user_joined):
        return

    user = await event.get_user()

    # Skip if user is not bot
    if not user.bot:
        return

    # Skip trusted bots
    if user.id in TRUSTED_BOTS:
        return

    chat = await event.get_chat()
    chat_id = chat.id

    # Initialize set if not exists
    if chat_id not in notified_bots:
        notified_bots[chat_id] = set()

    try:
        # Kick the bot
        await bot.kick_participant(chat_id, user.id)

        # ✅ Only notify once per bot per chat
        if user.id not in notified_bots[chat_id]:
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
            await event.reply(f"{user_mention} ငါရှိနေသရွှေ့ဘယ်လို Bot အစုတ်တွေမှ‌ခြေဖို့ကိုအိမ်မက်‌တောင်မမက်မိစေနဲ့ ⚡️", parse_mode="html")
            notified_bots[chat_id].add(user.id)

    except Exception as e:
        # Notify owner if bot can't kick (not admin)
        await bot.send_message(
            OWNER_ID,
            f"⚠ Failed to remove bot {user.first_name} in {chat.title}. Error: {e}"
        )

# ==========================
# SAFE COMMAND DECORATOR
# ==========================
def safe_command(func):
    async def wrapper(event):
        try:
            await func(event)
        except FloodWaitError as f:
            print(f"⚠️ FloodWaitError {f.seconds}s → Sleeping")
            await asyncio.sleep(f.seconds)
        except Exception as e:
            print(f"⚠️ Error in {func.__name__}: {e}")
            # Optional: notify owner
    return wrapper

# ==========================
# OWNER CHECK
# ==========================
def is_owner(user_id):
    return user_id == OWNER_ID

# ==========================
# EXAMPLE COMMAND
# ==========================
@bot.on(events.NewMessage(pattern=r"(?i)^/example"))
@safe_command
async def example_command(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Owner only")
    await event.reply("✅ Example command works safely!")

# ==========================
# GLOBAL ASYNCIO EXCEPTION HANDLER
# ==========================
def handle_exception(loop, context):
    print(f"⚠️ Unhandled exception: {context.get('message')}")
    # Bot keeps running regardless

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

load_rsave()

# =========================
# MAIN LOOP (Normal)
# =========================
async def main():
    print("Bot is running...")
    await bot.run_until_disconnected()

# =========================
# RUN BOT
# =========================
with bot:
    bot.loop.run_until_complete(main())



