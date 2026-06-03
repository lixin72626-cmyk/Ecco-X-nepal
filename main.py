import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask('')
@app.route('/')
def home(): return "Multi-Bots Fixed & Ready!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIG ---
TOKENS = [
    "8959700806:AAGSxeg0gY7U300DlFfXblg2fIkYV5MB1mE", 
    "8638389490:AAHUiHT5IdPxFbqKQGwdNwoimeApJ9xClds",                                
    "8697695665:AAFTLZ3VG3kMtQ84Al72J-jKyBPO_dqO9QE"                                 
]
OWNER_ID = 7681995468 
MY_LINK = "https://t.me/kai_iz_mad51"

# 🔥 အရေးကြီးဆုံးအပိုင်း- Bot တစ်ကောင်ချင်းစီအတွက် Task တွေကို သီးသန့်ခွဲမှတ်မယ်
bot_task_manager = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"👋 **ဆရာအီကို့ Bot!**\n\nJoin: {MY_LINK}\n(မ Join ရင် ရည်းစားမရပါစေနဲ့)"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot_id = context.bot.id # လက်ရှိ Bot ရဲ့ ID ကို ယူမယ်
    
    if user_id != OWNER_ID:
        return

    # ဒီ Bot ရဲ့ ဒီ Chat ထဲမှာ Run နေတာရှိရင် အရင်ရပ်မယ်
    if bot_id in bot_task_manager and chat_id in bot_task_manager[bot_id]:
        bot_task_manager[bot_id][chat_id].cancel()

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

    async def worker():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"{target} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.8) # Rate limit မမိအောင် ၀.၈ စက္ကန့် ထားထားပါတယ်
                    except Exception:
                        await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass # ရပ်လိုက်တဲ့အခါ ဘာမှထပ်မလုပ်ခိုင်းတော့ဘူး

    # Task ကို စာရင်းသွင်းမယ်
    task = asyncio.create_task(worker())
    if bot_id not in bot_task_manager:
        bot_task_manager[bot_id] = {}
    bot_task_manager[bot_id][chat_id] = task
    
    await update.message.reply_text(f"🔥 {target} ကို စတင်နှိပ်စက်နေပါပြီ...")

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot_id = context.bot.id
    
    if user_id != OWNER_ID: return
    
    # ဒီ Bot ရဲ့ Task Manager ထဲမှာ ဒီ Chat ရှိလား စစ်မယ်
    if bot_id in bot_task_manager and chat_id in bot_task_manager[bot_id]:
        bot_task_manager[bot_id][chat_id].cancel() # အသေသတ်လိုက်ပြီ
        del bot_task_manager[bot_id][chat_id]
        await update.message.reply_text("✅ **ဆရာအီကို့အမိန့်အရ ရပ်လိုက်ပြီ!**")
    else:
        await update.message.reply_text("❌ ရပ်စရာ Spam မရှိဘူး။ (ဒီ Bot အတွက်)")

async def main():
    keep_alive()
    tasks = []
    for token in TOKENS:
        try:
            app = ApplicationBuilder().token(token).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("spam", start_spam))
            app.add_handler(CommandHandler("stop", stop_spam))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            print(f"🚀 Bot ID: {token.split(':')[0]} Online!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
