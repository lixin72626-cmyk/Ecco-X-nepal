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

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "All 4 Bots are Active!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION ---
OWNER_ID = 7681995468 
running_spams = {}

# --- SPAM FUNCTIONS (မပြောင်းလဲပါ) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **ဆရာအီကို့ Bot မှ ကြိုဆိုပါတယ်!**", parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းကိုဆရာအီကိုကခွင့်မပြုထားဘူး။")
        return
    if chat_id in running_spams:
        await update.message.reply_text("⚠️ စပမ်းနေတုန်းပါ ဘရို။")
        return

    target_mention = ""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        target_mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    elif context.args:
        arg = context.args[0]
        target_mention = arg if arg.startswith("@") else f"[User](tg://user?id={arg})"
    else:
        await update.message.reply_text("❌ Target ထည့်ပါ။")
        return

    messages = ["ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံး", "ဘာပြောပြောငါကဆဲမှာပဲ", "မင်းအမေနဲ့ငါလိုးတုန်းကလည်းမင်းအမေအော်ခဲ့တာပဲ", "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ်", "မင်းအမေစောက်ဖုတ်ကိုဂျွမ်းပြစ်လိုး လိုက်ရ"]
    
    await update.message.reply_text(f"🔥 {target_mention} ကို အနိုင်ကျင့်ပြီ...", parse_mode=ParseMode.MARKDOWN)

    async def spam_loop():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"{target_mention} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.6) 
                    except: await asyncio.sleep(5); continue
        except asyncio.CancelledError: pass

    task = asyncio.create_task(spam_loop())
    running_spams[chat_id] = task

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_user.id == OWNER_ID and chat_id in running_spams:
        running_spams[chat_id].cancel()
        del running_spams[chat_id]
        await update.message.reply_text("✅ ရပ်တန့်လိုက်ပြီ။")

# --- MULTI-BOT RUNNER (FIXED) ---

async def setup_bot(token, name):
    """Bot တစ်ခုချင်းစီကို သီးခြားစီ Setup လုပ်ခြင်း"""
    print(f"⚙️ Setting up {name}...")
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spam", start_spam))
    application.add_handler(CommandHandler("stop", stop_spam))
    
    await application.initialize()
    await application.start_polling()
    print(f"✅ {name} is Polling!")

async def main():
    tokens = [
        ("8959700806:AAEXzhnkmw6sY9w1xJqOVrmcjHG_VLFgzEk", "Main_Bot"),
        ("8638389490:AAGK9d1J_Vx3y3JYpbQ5ajCRM3Mk4r8jYkk", "Bot_1"),
        ("8697695665:AAFwasTJ_9AZZN92gkBOWbhAPKqWFhhbVlM", "Bot_2"),
        ("8605823225:AAHx4K9G8In5m2hjxonDX6-I3g9wVfgSCiw", "Bot_3")
    ]
    
    # ၄ ကောင်လုံးကို background task အဖြစ် တပြိုင်တည်း ပစ်ထုတ်လိုက်မယ်
    for token, name in tokens:
        asyncio.create_task(setup_bot(token, name))

    # Bot တွေ အလုပ်လုပ်နေချိန်မှာ Main Loop ကို မပိတ်သွားအောင် စောင့်ခိုင်းထားမယ်
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    keep_alive()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
