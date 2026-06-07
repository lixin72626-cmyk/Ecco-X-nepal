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
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import FloodWaitError
from telethon.utils import get_display_name
from datetime import datetime
from telethon.tl.types import UpdateChatParticipantAdd
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.custom.message import Message
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import ChannelParticipantsSearch
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
# Config (UPDATED FOR BOT 1)
# ==========================
API_ID = 34166212
API_HASH = "753aae555e6d5901145fc8685d47bffe"
BOT_TOKEN = "8959700806:AAF774P3QFqBbiBID2UnqLu6A_QXeCR1xu0"

OWNER_ID = 7681995468
BOT_OWNER_ID = 7681995468
DB_FILE = "bot_data_1.db"

# ==========================
# MAIN BOT DATABASE
# ==========================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# ==========================
# TABLES SETUP
# ==========================
cursor.execute("CREATE TABLE IF NOT EXISTS asave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS rsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS tsave (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_groups (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, reply TEXT)")
conn.commit()

protected_conn = sqlite3.connect("protected_1.db", check_same_thread=False)
protected_cursor = protected_conn.cursor()
protected_cursor.execute("CREATE TABLE IF NOT EXISTS protected_users (user_id INTEGER PRIMARY KEY)")
protected_conn.commit()

protected_cursor.execute("SELECT user_id FROM protected_users")
protected_users = set(row[0] for row in protected_cursor.fetchall())

# ==========================
# TELETHON CLIENT
# ==========================
bot = TelegramClient("Bot_Session_1", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("✅ Bot 1: Databases created and verified successfully!")

async def remember_group(chat_id):
    cursor.execute("INSERT OR IGNORE INTO active_groups (chat_id) VALUES (?)", (chat_id,))
    conn.commit()

def get_active_groups():
    rows = cursor.execute("SELECT chat_id FROM active_groups").fetchall()
    return [r[0] for r in rows]

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

GROUPS = set()

@bot.on(events.ChatAction)
async def save_group(event):
    if event.is_group:
       GROUPS.add(event.chat_id)

@bot.on(events.Raw)
async def raw_handler(event):
    if isinstance(event, UpdateChatParticipantAdd):
        print("User joined")

def has_permission(user_id):
    return is_owner(user_id) or is_admin(user_id)

RSAVE_FILE = "rsave_data_1.json"
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

troll_targets = {}
delete_targets = {}
att_targets = {}
attack_speed = 1
translator = Translator()
TRUSTED_BOTS = [OWNER_ID]
calling_task = None
stop_calling = False
reply_task_started = False
REPLY_DURATION = 86400
REPLY_INTERVAL = 1
reply_targets = {}
bot_id = None
current_index = 0
LINK_WORDS = ["@", "bio", "ဘိုင်O", "ဘိုင်အို", "http://", "https://", "t.me/", "telegram.me"]

@bot.on(events.NewMessage(pattern=r"(?i)^/start$"))
async def start_command(event):
    user = await bot.get_entity(event.sender_id)
    username = f"@{user.username}" if user.username else "No Username"
    msg = f"👋 မင်္ဂလာပါ {user.first_name}!\n\nUsername: {username}\nဒီ bot နဲ့ သုံးနိုင်တဲ့ commands အားလုံးကို (အကူအညီ) စမ်းကြည့်နိုင်ပါတယ်:\n"
    await event.reply(msg)

group_speeds = {}
attack_tasks = {}

@bot.on(events.NewMessage(pattern=r"(?i)^အရှိန် (.+)"))
async def set_speed(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်အီကို ကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    chat_id = event.chat_id
    try:
        speed = float(event.pattern_match.group(1))
        if speed < 0:
            speed = 0
        group_speeds[chat_id] = speed
        await event.reply(f"အမြန်နှုန်းကို {speed} စက္ကန့်သို့ချိန်ညှိလိုက်ပါပီ (ဒီ Group အတွက်ပဲ)")
    except:
        await event.reply("Invalid number.")

@bot.on(events.NewMessage(pattern=r"(?i)^သတ်ပလိုက်(?:\s|$)"))
async def attack_user(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်အီကို ကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    chat_id = event.chat_id
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
    else:
        args = event.message.text.split()
        if len(args) < 2:
            return await event.reply("မျိုးမစစ်တွေကိုနှိမ်နှင်းစေချင်ရင်အမိန့်ကို မှန်ကန်စွာအသုံးပြုပါ (သတ်ပလိုက်) (Reply)")
        try:
            entity = await bot.get_entity(args[1])
            target_id = entity.id
        except:
            return await event.reply("မင်းပြောတဲ့ခွေးမျိုးလေးကိုရှာမတွေ့သေးပါ Try.")

    if is_owner(target_id):
        return await event.reply("သခင်အီကိုအားဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")

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
                if target_id not in attack_tasks.get(chat_id, {}):
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
    await event.reply("ဆရာနင်းခိုင်းလိုက်တဲ့ဖာသယ်မသား ဒီကမ္ဘာမှာငြိမ်းချမ်းမှုဆိုတာသူ့အတွက်မရှိစေရဘူး")

@bot.on(events.NewMessage(pattern=r"(?i)^ရပ်တော့"))
async def stop_attack(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("သခင်အီကိုဆီက ခွင့်ပြုချက်မရထားပါ")
    chat_id = event.chat_id
    if chat_id in attack_tasks:
        for task in attack_tasks[chat_id].values():
            task.cancel()
        attack_tasks[chat_id].clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")
PAGE_SIZE = 50

@bot.on(events.NewMessage(pattern=r"(?i)^/rsave (.+)"))
async def save_r(event):
    if not is_owner(event.sender_id):
        return
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
    if not is_owner(event.sender_id):
        return
    if not rsave_list:
        await event.reply("<blockquote>⚠️ Rsave list is empty.</blockquote>", parse_mode="html", reply_to=event.message.id)
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

@bot.on(events.NewMessage(pattern=r"(?i)^ပေးနားလိုက်"))
async def unset_reply(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return
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
    if bot_id is None:
        bot_id = (await bot.get_me()).id
    if event.sender_id == bot_id:
        return
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
        if not data:
            break
        if not rsave_list:
            await asyncio.sleep(2)
            continue
        try:
            text = rsave_list[current_index]
            msg = await bot.send_message(data["chat_id"], text, reply_to=data["base_msg_id"])
            data["last_bot_msg"] = msg.id
            current_index += 1
            if current_index >= len(rsave_list):
                current_index = 0
        except:
            pass
        await asyncio.sleep(REPLY_INTERVAL)

@bot.on(events.MessageDeleted)
async def track_delete(event):
    for uid, data in reply_targets.items():
        if data["base_msg_id"] in event.deleted_ids:
            data["base_msg_id"] = None
            data["mode"] = "mention"

@bot.on(events.NewMessage(pattern=r"(?i)^ရိုက်သတ်"))
async def set_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("မင်းကသခင်အီကို ကိုမလေးမစားလုပ်ထားပီးသုံးချင်တာလားစောက်ခွေး")
    if not event.is_reply:
        return await event.reply("❌အသုံးပြုပုံမှားယွင်းနေပါတယ် (ရိုက်သတ်) <reply_user> .....။")
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    if is_owner(target_id):
        return await event.reply("သခင်အီကိုအားဘယ်လိုနည်းလမ်းမျိုးနဲ့မှ တိုက်ခိုက်လို့မရပါဘူး လေးစားမှုဆိုတာရှိစမ်း")
    troll_targets[target_id] = {"index": 0}
    await event.reply("တိုက်ခိုက်မှုကိုစတင်လိုက်ပါပီ ရပ်တန့်လိုပါက (ခွင့်လွတ်လိုက်) <reply> ....။")

@bot.on(events.NewMessage(pattern=r"(?i)^ခွင့်လွတ်လိုက်"))
async def unset_troll(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")
    troll_targets.clear()
    await event.reply("ဖာသယ်မသားအပေါင်း ငါလက်အောက်ကနေငြိမ်းချမ်းစေသား")
@bot.on(events.NewMessage(incoming=True))
async def monitor_messages(event):
    if event.sender_id is None or is_owner(event.sender_id):
        return
    if event.sender_id in reply_targets:
        texts = cursor.execute("SELECT text FROM rsave ORDER BY id ASC").fetchall()
        if texts:
            data = reply_targets[event.sender_id]
            if time.time() > data.get("expire", 0):
                del reply_targets[event.sender_id]
                return
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1
            mention = f"<a href='tg://user?id={event.sender_id}'>User</a>"
            message = f"{mention}\n{text}"
            reply_mode = True
            if data.get("last_bot_msg"):
                try:
                    await bot.get_messages(event.chat_id, ids=data["last_bot_msg"])
                except:
                    reply_mode = False
            try:
                if reply_mode:
                    msg = await event.reply(message, parse_mode="html")
                else:
                    msg = await bot.send_message(event.chat_id, message, parse_mode="html")
                data["last_bot_msg"] = msg.id
            except:
                pass
            await asyncio.sleep(attack_speed)

    if event.sender_id in troll_targets:
        texts = cursor.execute("SELECT text FROM tsave ORDER BY id ASC").fetchall()
        if texts:
            data = troll_targets[event.sender_id]
            text = texts[data["index"] % len(texts)][0]
            data["index"] += 1
            try:
                await event.reply(text)
            except:
                pass
            await asyncio.sleep(attack_speed)

@bot.on(events.NewMessage(pattern=r"(?i)^စာဖျက်လိုက်"))
async def set_delete(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied.")
    if not event.is_reply:
        return await event.reply("⚠️ Reply to target user to activate delete mode.")
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    if is_owner(target_id):
        return await event.reply("⚠️ Cannot target the owner.")
    delete_targets[target_id] = event.chat_id
    await event.reply("✅ Delete mode activated for this user.")

@bot.on(events.NewMessage(pattern=r"(?i)^စာပေးရေးလိုက်(?:\s+(\d+|all))?"))
async def unset_delete(event):
    if not (is_owner(event.sender_id) or is_admin(event.sender_id)):
        return await event.reply("❌ Permission denied.")
    target_id = None
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg:
            target_id = reply_msg.sender_id
    else:
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

@bot.on(events.NewMessage(incoming=True))
async def auto_delete_monitor(event):
    if event.sender_id is None or is_owner(event.sender_id):
        return
    chat_id = event.chat_id
    target_ids = list(delete_targets.keys())
    async for user in bot.iter_participants(chat_id):
        if user.bot:
            target_ids.append(user.id)
    if event.sender_id in target_ids:
        try:
            await bot.delete_messages(chat_id, event.id)
        except Exception as e:
            print(f"Failed to delete message: {e}")
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.sender_id in delete_targets:
            try:
                await bot.delete_messages(chat_id, event.id)
            except Exception as e:
                print(f"Failed to delete reply: {e}")

@bot.on(events.NewMessage(pattern=r"(?i)^ထိန်းချုပ်လိုက်$"))
async def set_att(event):
    try:
        if not is_bot_admin(event.sender_id) and not is_owner(event.sender_id):
            return await event.reply("❌ သင် BOT ADMIN / OWNER မဟုတ်ပါ။")
        if not event.is_reply:
            return await event.reply("⚠️ Target User ကို Reply လုပ်ပါ။")
        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
        if is_owner(target_id):
            return await event.reply("⚠️ Owner ကို mute / control လုပ်လို့မရပါ။")
        att_targets[target_id] = event.chat_id
        await event.reply("✅ User ကို 10s Auto Mute System ထဲထည့်လိုက်ပါပြီ။")
    except Exception as e:
        print("ATT / ERROR:", e)
        await event.reply("⚠️ Bot မှာ တစ်စုံတစ်ရာ အမှားဖြစ်နေပါတယ်။ Admin ကို contact လုပ်ပါ။")

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

@bot.on(events.NewMessage(incoming=True))
async def monitor_att(event):
    try:
        user_id = event.sender_id
        chat_id = event.chat_id
        if user_id not in att_targets or att_targets[user_id] != chat_id:
            return
        await bot.edit_permissions(chat_id, user_id, send_messages=False)
        await asyncio.sleep(10)
        if user_id in att_targets:
            await bot.edit_permissions(chat_id, user_id, send_messages=True)
    except Exception as e:
        print("AUTO CONTROL ERROR:", e)

calling_tasks = {}
stop_flags = {}

@bot.on(events.NewMessage(pattern=r"(?i)^အကုန်ခေါ်(?:@\w+)? (.+)"))
async def start_calling(event):
    chat_id = event.chat_id
    text = event.pattern_match.group(1)
    if not has_permission(event.sender_id):
        return await event.reply("❌ Permission denied")
    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        return await event.reply("⚠️ Calling already running in this group.")
    stop_flags[chat_id] = False
    calling_tasks[chat_id] = asyncio.create_task(calling_engine(chat_id, text))
    await event.reply("🔊🔊‌ခေါ်ဆိုမှုကိုစတင်လိုက်ပါပီ (မခေါ်နဲ့တော့) ဖြင့်ရပ်တန့်လို့ရသည်....။")

@bot.on(events.NewMessage(pattern=r"မခေါ်နဲ့တော့$"))
async def stop_call(event):
    chat_id = event.chat_id
    if not has_permission(event.sender_id):
        return await event.reply("❌ Permission denied")
    if chat_id in calling_tasks and not calling_tasks[chat_id].done():
        stop_flags[chat_id] = True
        await calling_tasks[chat_id]
        await event.reply("🔇🔇ခေါ်ဆိုမှုကိုရပ်တန့်လိုက်ပါပီ...။")
    else:
        await event.reply("⚠️ No calling task running in this group.")

async def calling_engine(chat_id, text):
    members = []
    async for user in bot.iter_participants(chat_id):
        members.append(user)
    batch_size = 5
    delay_seconds = 2
    total_members = len(members)
    for i in range(0, total_members, batch_size):
        if stop_flags.get(chat_id):
            break
        batch = members[i:i + batch_size]
        mentions = [f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" for user in batch]
        message = " ".join(mentions) + "\n\n" + text
        try:
            await bot.send_message(chat_id, message, parse_mode="html")
        except Exception as e:
            print(f"Error sending batch in chat {chat_id}: {e}")
        await asyncio.sleep(delay_seconds)
    stop_flags[chat_id] = False
    calling_tasks.pop(chat_id, None)

permitted_users = set()

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

@bot.on(events.NewMessage(pattern=r"/Asave (.+)"))
async def save_attack(event):
    if event.sender_id == OWNER_ID:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Attack text saved (owner)")
    if event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO asave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Attack text saved (permission used)")
    await event.reply("❌ Permission denied")

@bot.on(events.NewMessage(pattern=r"/Tsave (.+)"))
async def save_troll(event):
    if event.sender_id == OWNER_ID:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Troll text saved (owner)")
    if event.sender_id in permitted_users:
        text = event.pattern_match.group(1)
        cursor.execute("INSERT INTO tsave(text) VALUES(?)", (text,))
        conn.commit()
        return await event.reply("✅ Troll text saved (permission used)")
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
    if page > 0:
        buttons.append(Button.inline("Previous", data=f"{title_prefix}_prev_{page-1}".encode()))
    if end < len(rows):
        buttons.append(Button.inline("Next", data=f"{title_prefix}_next_{page+1}".encode()))
    await event.reply(msg_text, buttons=buttons, parse_mode="html")

@bot.on(events.NewMessage(pattern=r"/Alist"))
async def list_attack(event):
    rows = cursor.execute("SELECT id, text FROM asave").fetchall()
    if not rows:
        await event.reply("<blockquote>No attack texts saved.</blockquote>", parse_mode="html")
        return
    await show_page(event, rows, 0, "Attack List")

@bot.on(events.NewMessage(pattern=r"/Tlist"))
async def list_troll(event):
    rows = cursor.execute("SELECT id, text FROM tsave").fetchall()
    if not rows:
        await event.reply("<blockquote>No troll texts saved.</blockquote>", parse_mode="html")
        return
    await show_page(event, rows, 0, "Troll List")

@bot.on(events.CallbackQuery(pattern=b"(Attack List|Troll List)_(prev|next)_(\\d+)"))
async def paginate(event):
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
    cursor.execute("SELECT chat_id FROM active_groups")
    groups = [row[0] for row in cursor.fetchall()]
    for group_id in groups:
        try:
            await bot.forward_messages(group_id, reply_msg)
            shared_count += 1
            await asyncio.sleep(1)
        except:
            failed_count += 1
            continue
        await status_msg.edit(f"📤 Forwarding...\n✅ Success: {shared_count}\n❌ Failed: {failed_count}")
    await status_msg.edit(f"✅ Forwarding completed!\n📦 Groups: {shared_count}\n❌ Failed: {failed_count}")

@bot.on(events.NewMessage)
async def track_groups(event):
    chat = await event.get_chat()
    chat_id = chat.id
    if not getattr(chat, "megagroup", False) and not getattr(chat, "gigagroup", False) and not getattr(chat, "broadcast", False):
        return
    cursor.execute("SELECT chat_id FROM active_groups WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO active_groups(chat_id) VALUES(?)", (chat_id,))
        conn.commit()

@bot.on(events.NewMessage(pattern=r"(?i)^groupid"))
async def chat_info(event):
    chat = await event.get_chat()
    admins = await bot.get_participants(chat, filter=ChannelParticipantsAdmins)
    admin_text = "".join([f"{i}. {a.first_name}\n   {a.id}\n" for i, a in enumerate(admins, start=1)])
    group_id_display = f"-100{chat.id}" if getattr(chat, 'megagroup', False) or getattr(chat, 'broadcast', False) else str(chat.id)
    msg = f"<blockquote>Group Name: {chat.title}\nGroup ID: {group_id_display}\n\nAdmins:\n{admin_text}</blockquote>"
    await event.reply(msg, parse_mode="html")

@bot.on(events.NewMessage(pattern=r"^သူ့စောက်ကြောင်း(?: (.+))?$"))
async def user_id(event):
    arg = event.pattern_match.group(1)
    try:
        if event.is_reply:
            reply = await event.get_reply_message()
            user = await bot.get_entity(reply.sender_id)
        elif arg:
            user = await bot.get_entity(arg)
        else:
            user = await bot.get_entity(event.sender_id)
        username = f"@{user.username}" if user.username else "No Username"
        msg = f"<blockquote>Name : {user.first_name}\nUser ID : {user.id}\nUsername : {username}</blockquote>"
        await event.reply(msg, parse_mode="html")
    except:
        await event.reply("User ရှာမတွေ့ပါ။")

@bot.on(events.NewMessage(pattern=r"/Botadmlist"))
async def list_admins(event):
    rows = cursor.execute("SELECT user_id FROM bot_admins").fetchall()
    if not rows:
        await event.reply("<blockquote>⚠️ No Bot Admins assigned.</blockquote>", parse_mode="html")
        return
    msg_lines = []
    for r in rows:
        try:
            user = await bot.get_entity(r[0])
            msg_lines.append(f"{user.first_name or 'Unknown'} — {user.id}")
        except:
            msg_lines.append(f"Unknown — {r[0]}")
    await event.reply("<blockquote>👮 Bot Admins:\n\n" + "\n".join(msg_lines) + "</blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^မှတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def add_admin(event):
    if not is_owner(event.sender_id):
        return
    uid = event.pattern_match.group(2)
    if event.is_reply:
        reply = await event.get_reply_message()
        uid = reply.sender_id
    elif uid:
        uid = int(uid)
    else:
        return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")
    cursor.execute("INSERT OR IGNORE INTO bot_admins(user_id) VALUES(?)", (uid,))
    conn.commit()
    await event.reply(f"✅ User `{uid}` ကို Bot Admin အဖြစ်ထည့်လိုက်ပါပြီ")

@bot.on(events.NewMessage(pattern=r"(?i)^ဖြုတ်လိုက်(?:@(\w+))?(?: (\d+))?$"))
async def remove_admin(event):
    if not is_owner(event.sender_id):
        return
    uid = event.pattern_match.group(2)
    if event.is_reply:
        reply = await event.get_reply_message()
        uid = reply.sender_id
    elif uid:
        uid = int(uid)
    else:
        return await event.reply("Reply user သို့မဟုတ် User ID ထည့်ပါ။")
    cursor.execute("DELETE FROM bot_admins WHERE user_id=?", (uid,))
    conn.commit()
    await event.reply(f"❌ User `{uid}` ကို Bot Admin မှ ဖယ်ရှားလိုက်ပါပြီ")

@bot.on(events.ChatAction)
async def bot_added(event):
    if event.user_added:
        me = await bot.get_me()
        if event.user_id == me.id and event.action_message:
            adder = await bot.get_entity(event.action_message.from_id)
            await event.reply(f"<blockquote>ကောင်းကင်စီးနှင်းသူလို့လူသိများတဲ့ {me.first_name} ရောက်ရှိလာပါပီ <a href='tg://user?id={adder.id}'>{adder.first_name}</a> တေးသံလိုညိမ့်‌ညောင်းတဲ့တိုက်ခိုက်မှုကိုစတင်ရန် (သတ်ပလိုက်) ကိုအသုံးပြုပါ.....။ </blockquote>", parse_mode="html")

@bot.on(events.NewMessage(pattern=r"(?i)^အကူအညီ$"))
async def helps_command(event):
    help_text = (
        "<blockquote>BOT COMMANDS GUIDE (မြန်မာလို)\n"
        "════════════════════════\n\n"
        "• သတ်ပလိုက် / ရပ်တော့ / အရှိန် <time>\n"
        "• လွတ်အောင်ပြေး / ပေးနားလိုက်\n"
        "• ရိုက်သတ် / ခွင့်လွတ်လိုက်\n"
        "• စာဖျက်လိုက် / စာပေးရေးလိုက်\n"
        "• အကုန်ခေါ် / မခေါ်နဲ့တော့\n"
        "• ထိန်းချုပ်လိုက် / လွတ်ပေးလိုက်\n"
        "• ဘာသာပြန်မယ် / သူ့စောက်ကြောင်း / groupid\n"
        "• /filter <trigger> <reply></blockquote>"
    )
    await event.reply(help_text, parse_mode="html")

def handle_exception(loop, context): pass
loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
load_rsave()

async def main():
    await bot.run_until_disconnected()

with bot:
    bot.loop.run_until_complete(main())
