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
def home(): return "Multi-Bots are Alive!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION ---
TOKENS = [
    "8959700806:AAGSxeg0gY7U300DlFfXblg2fIkYV5MB1mE", 
    "8638389490:AAHUiHT5IdPxFbqKQGwdNwoimeApJ9xClds",                                
    "8697695665:AAFTLZ3VG3kMtQ84Al72J-jKyBPO_dqO9QE"                                 
]
OWNER_ID = 7681995468 
MY_LINK = "https://t.me/kai_iz_mad51"

# Task Management
running_spams = {token: {} for token in TOKENS}

# --- BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # မူရင်း Link များကို ဖယ်ရှားပြီး ကိုယ်ပိုင် Link ဖြင့် အစားထိုးခြင်း
    join_msg = (
        f"👋 **အရှင်သခင်အီကို့ Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        f"🚀 ဒီ Bot ကို သုံးချင်ရင် အောက်က Channel ကို အရင် Join ပေးပါ -\n"
        f"🔗 {MY_LINK}\n\n"
        f"⚠️ **သတိပေးချက်:** အရှင်သခင်အီကိုရဲ့ Link ကိုမင်းကို Join ဖို့အမိန့်ပေးတယ်။"
    )
    await update.message.reply_text(join_msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_token = context.application.bot.token
    
    if user_id != OWNER_ID:
        await update.message.reply_text(f"❌ မင်းကို အရှင်သခင်အီကိုက ခွင့်မပြုထားဘူး။\nJoin ထားမှသုံးခွင့်ပေးမယ်။: {MY_LINK}")
        return

    if chat_id in running_spams[current_token]:
        await update.message.reply_text("⚠️ ကျနော်က စပမ်းနေတုန်းပါ ဆရာ။")
        return

    target_mention = ""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        target_mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    elif context.args:
        arg = context.args[0]
        target_mention = arg if arg.startswith("@") else f"[User](tg://user?id={arg})"
    else:
        await update.message.reply_text("❌ စပမ်းမယ့်လူကို Reply ပြန်ပါ သို့မဟုတ် Username/ID ထည့်ပါ။")
        return

    messages = [
        "ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံး နော် ငကြောင်မင်းကိုကြည့်မရလို့ဆဲနေတာ ပုကျိပုကျိစာကလေး လို့အော်ပြရင် ရပ်ပေးမယ်မင်းအမေစောက်ဖုတ်ကိုငါလီးနဲ့ထိုးသွင်းပီး တစ်ဇွတ်ထိုးဖြဲလိုး ​အထှာကျတဲ့ငကြောင်ရဲ့စတိုင်နဲ့ လီးကိုမှီချင်ရင်တော့ ဘုရားသခင်ချီကောင်းချီသာတောင်းပီး တစ်နေကုန်သာဆုတောင်းနေတော့ဟေး😈👈", 
        "ဘာပြောပြောငါကဆဲမှာပဲ မင်းအမေလာတောင်းပန်ရင်တောင် ငါကခွင့်လွတ် မှာမဟုတ်ဘူး မင်းထက်အထာကျလို့ သခင်အီကိုဆိုပြီး ဆရာကြီးဖြစ်နေတာ လက်နက်ချပြီးအရှုံးပေးလိုက်တော့😜🤞", 
        "မင်းအမေနဲ့ငါလိုးတုန်းကလည်းမင်းအမေအော်ခဲ့တာပဲ မင်းအော်တာလောက်ကတော့ငါကရင်တောင်မခုန်ဘူး မင်းရဲ့အော်သံတွေက မင်းအမေငိုသံတွေနဲ့တူသလို ပဲ ဘာ​ဖြစ်ဖြစ်မင်းကငါ့ကျွန်ဆိုတာ မင်းမမေ့ဖို့လို တယ် 😎👈", 
        "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ် မယုံရင်ကောင်းကင်ကြီးကို လည်ပင်းညစ်ပီး ​ပြေးထိုးမေးလိုက် ရလဒ်ကတော့ အီကိုကမင်းအဖေဖြစ်တယ်ဆိုတာ ပိုသေချာသွားတာပေါ့ ချစ်သား🤪👈", 
        "မင်းအမေစောက်ဖုတ်ကိုဂျွမ်းပြစ်လိုး လိုက်ရ ကမ္ဘာ့အပြင်ဘက်ကိုရောက်ရုံတောင်မက ဂြိုလ်သားတွေနဲ့ မိတ်လိုက်ပြီးလျှပ်စစ်တွေ လျှက်ကုန်မယ် ကောင်းကင်မှာ လျှပ်စစ်လျက်ရင် မင်းအမေနဲ့ဂြိုလ်သားလိုးနေတယ်လို့သာမှတ်ထားလိုက် 😳👈"
    ]
    
    await update.message.reply_text(f"🔥 {target_mention} ဒီစောက်တောသားကို အရှင်သခင်အီကို အနိုင်ကျင့်ပြီ...", parse_mode=ParseMode.MARKDOWN)

    async def spam_loop():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"{target_mention} {msg}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        await asyncio.sleep(0.8)
                    except Exception as e:
                        logging.warning(f"Error: {e}")
                        await asyncio.sleep(5)
                        continue
        except asyncio.CancelledError:
            logging.info(f"Spam stopped in {chat_id}")

    task = asyncio.create_task(spam_loop())
    running_spams[current_token][chat_id] = task 

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_token = context.application.bot.token
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းအဆင့်နဲ့ဘာကိုရပ်ချင်တာလဲ။ အရှင်သခင်အီကိုပဲရပ်လို့ရတယ်။")
        return
    
    if chat_id in running_spams[current_token]:
        running_spams[current_token][chat_id].cancel()
        del running_spams[current_token][chat_id]
        await update.message.reply_text("✅ ဆရာအီကိုက ခွေးသေးလေးကို အနိုင်ကျင့်တာ ရပ်လိုက်ပြီ။")
    else:
        await update.message.reply_text("❌ လက်ရှိမှာ ဘာစပမ်းမှ မလုပ်နေပါဘူး။")

# --- MAIN RUN ---
async def main():
    keep_alive()
    
    for token in TOKENS:
        try:
            app_bot = ApplicationBuilder().token(token).build()
            
            app_bot.add_handler(CommandHandler("start", start))
            app_bot.add_handler(CommandHandler("spam", start_spam))
            app_bot.add_handler(CommandHandler("stop", stop_spam))
            
            await app_bot.initialize()
            await app_bot.start()
            await app_bot.updater.start_polling()
            print(f"🚀 Bot - {token[:10]}... Started!")
        except Exception as e:
            print(f"❌ Error starting bot {token[:10]}: {e}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
