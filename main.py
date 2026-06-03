import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Multi-Bots Fixed & Running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- UPDATED TOKENS ---
TOKENS = [
    "8959700806:AAGSxeg0gY7U300DlFfXblg2fIkYV5MB1mE", 
    "8638389490:AAHUiHT5IdPxFbqKQGwdNwoimeApJ9xClds",                                
    "8697695665:AAFTLZ3VG3kMtQ84Al72J-jKyBPO_dqO9QE"                                 
]
OWNER_ID = 7681995468 
MY_LINK = "https://t.me/kai_iz_mad51"

# Task တွေကို သိမ်းထားဖို့ (အသေချာ ရပ်ပစ်ဖို့အတွက်)
active_tasks = {token: {} for token in TOKENS}

# --- FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"👋 **ဆရာအီကို့ Bot!**\n\nJoin: {MY_LINK}\n(မ Join ရင် ရည်းစားမရပါစေနဲ့)"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    token = context.application.bot.token
    
    if user_id != OWNER_ID:
        return

    # အဟောင်းရှိရင် အရင်သတ်မယ်
    if chat_id in active_tasks[token]:
        active_tasks[token][chat_id].cancel()

    target = ""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        target = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    elif context.args:
        target = context.args[0]
    else:
        await update.message.reply_text("❌ ဘယ်သူ့ကို ဆဲရမလဲ?")
        return

    messages = [
        "ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံး...", 
        "ဘာပြောပြောငါကဆဲမှာပဲ...", 
        "မင်းအမေနဲ့ငါလိုးတုန်းကလည်း...", 
        "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာ...", 
        "မင်းအမေစောက်ဖုတ်ကိုဂျွမ်းပြစ်လိုး..."
    ]

    async def spam_worker():
        try:
            while True:
                for msg in messages:
                    try:
                        # စာပို့တာကို တိုက်ရိုက်လုပ်မယ်
                        await context.bot.send_message(chat_id=chat_id, text=f"{target} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.7) # Speed နည်းနည်းလျှော့တာက ပိုရပ်ရလွယ်စေပါတယ်
                    except Exception:
                        await asyncio.sleep(5)
        except asyncio.CancelledError:
            logging.info(f"Task Cancelled in {chat_id}")

    # Task အသစ်ကို စပြီး မှတ်ထားမယ်
    task = asyncio.create_task(spam_worker())
    active_tasks[token][chat_id] = task
    await update.message.reply_text(f"🔥 {target} ကို စတင်နှိပ်စက်နေပါပြီ...")

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    token = context.application.bot.token
    
    if user_id != OWNER_ID: return
    
    if chat_id in active_tasks[token]:
        # Task ကို ချက်ချင်း ရပ်ပစ် (Kill) တာပါ
        active_tasks[token][chat_id].cancel()
        del active_tasks[token][chat_id]
        await update.message.reply_text("✅ **ပြတ်ပြတ်သားသား ရပ်လိုက်ပြီ ဆရာကြီး!**")
    else:
        await update.message.reply_text("❌ ရပ်စရာ Spam မရှိဘူး။")

async def main():
    keep_alive()
    for token in TOKENS:
        try:
            app = ApplicationBuilder().token(token).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("spam", start_spam))
            app.add_handler(CommandHandler("stop", stop_spam))
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            print(f"🚀 Bot {token[:10]}... Online!")
        except: pass
    
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
