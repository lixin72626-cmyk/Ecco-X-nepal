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
def home(): return "Multi-Bots are Alive & Updated!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION (UPDATED TOKENS) ---
TOKENS = [
    "8959700806:AAGSxeg0gY7U300DlFfXblg2fIkYV5MB1mE", 
    "8638389490:AAHUiHT5IdPxFbqKQGwdNwoimeApJ9xClds",                                
    "8697695665:AAFTLZ3VG3kMtQ84Al72J-jKyBPO_dqO9QE"                                 
]
OWNER_ID = 7681995468 
MY_LINK = "https://t.me/eccolism"

# Spamming Status ကို Track လုပ်ဖို့ Dictionary
running_spams = {token: {} for token in TOKENS}

# --- BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_msg = (
        f"အရှင်သခင်အီကို့ Bot ကိုသုံးချင်နေပြီလား\n\n"
        f"ဒီ Bot ကိုသုံးချင်ရင် အောက်က Channel ကိုအရင် Join တပဲ့ -\n"
        f"{MY_LINK}\n\n"
        f"Link မြင်ရဲ့သားနဲ့မ Join ရင်မင်းအမေငါလိုး Bot Owner - @Ecco2k5"
    )
    await update.message.reply_text(join_msg, parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    token = context.application.bot.token
    
    if user_id != OWNER_ID:
        await update.message.reply_text(f"❌ ဆရာအီကိုပဲ သုံးခွင့်ရှိတယ်။\nJoin: {MY_LINK}")
        return

    if chat_id in running_spams[token] and running_spams[token][chat_id]:
        await update.message.reply_text("⚠️ ဒီ Bot က အလုပ်လုပ်နေတုန်းပဲ ဆရာ!")
        return

    # Target ရှာဖွေခြင်း
    target = ""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        target = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    elif context.args:
        target = context.args[0]
    else:
        await update.message.reply_text("❌ ဘယ်ကောင်ကို ဆဲရမလဲ ပြောဦးလေ။")
        return

    messages = [
        "ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံးနော် အီကိုမင်းကိုကြည့်မရလို့ဆဲနေတာ ပုကျိပုကျိလို့ စာကလေးလိုအော်ပြရင် ရပ်ပေးမယ်မင်းအမေစောက်ဖုတ်ကိုငါလီးနဲ့ထိုးသွင်းပီး တစ်ဇွတ်ထိုးဖြဲလိုးတဲ့ အထာကျတဲ့​အီကို့ရဲ့ လီးကိုမှီချင်ရင်တော့ ဘုရားသခင်ဆီကိုတစ်နေကုန်သာဆုတောင်းနေတော့ဟေး😈👈", 
        "ဘာပြောပြောငါကဆဲမှာပဲ မင်းအမေလာတောင်းပန်ရင်တောင် ငါကခွင့်လွတ်မှာမဟုတ်ဘူး မင်းထက်အထာကျလို့ သခင်အီကိုဆိုပြီး ဆရာကြီးဖြစ်နေတာ လက်နက်ချပြီးအရှုံးပေးလိုက်တော့😜🤞", 
        "မင်းအမေနဲ့ငါလိုးတုန်းကလည်းမင်းအမေအော်ခဲ့တာပဲ မင်းအော်တာလောက်ကတော့ငါကရင်တောင်မခုန်ဘူး မင်းရဲ့အော်သံတွေက မင်းအမေငိုသံတွေနဲ့တူသလို ပဲ ဘာ​ဖြစ်ဖြစ်မင်းကငါ့ကျွန်ဆိုတာ မင်းမမေ့ဖို့လိုတယ် 😎👈", 
        "ကြောက်ရွံမှုဆိုတာရဲ့အထက်မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ် မယုံရင်ကောင်းကင်ကြီးကို အော်ပြီးမေးကြည့် ရလဒ်ကတော့ အီကိုကမင်းအဖေဖြစ်တယ်ဆိုတာ မသိရကောင်းလားဆိုပြီး မိုးကျိုးပစ်ပြီးဆုံးမပေးလိမ့်မယ်🤪👈", 
        "မင်းအမေစောက်ဖုတ်ကိုဂျွမ်းပြစ်လိုးလိုက်ရ ကမ္ဘာ့အပြင်ဘက်ကိုရောက်ရုံတောင်မက Alien တွေနဲ့ပါမိတ်လိုက်ပြီးလျှပ်စီးတွေပါလတ်ကုန်မယ် ကောင်းကင်မှာ လျှပ်စီးလတ်နေရင် မင်းအမေနဲ့ Alien လိုးနေတယ်လို့သာမှတ်ထားလိုက် 😳👈"
    ]
    
    running_spams[token][chat_id] = True
    await update.message.reply_text(f" {target} ဒီစောက်တောသားကို အရှင်သခင်အီကို အနိုင်ကျင့်နေပြီ...", parse_mode=ParseMode.MARKDOWN)

    try:
        while running_spams[token].get(chat_id, False):
            for msg in messages:
                if not running_spams[token].get(chat_id, False): break 
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"{target} {msg}", parse_mode=ParseMode.MARKDOWN)
                    await asyncio.sleep(0.8)
                except Exception:
                    await asyncio.sleep(3)
    except Exception as e:
        logging.error(f"Spam Loop Error: {e}")

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    token = context.application.bot.token
    
    if user_id != OWNER_ID:
        return
    
    if chat_id in running_spams[token]:
        running_spams[token][chat_id] = False # Flag ကို ပိတ်လိုက်ခြင်းဖြင့် Loop ကို ရပ်စေသည်
        await update.message.reply_text("ဆရာအီကိုက ခွေးသေးသေးလေးကို အနိုင်ကျင့်တာ ရပ်လိုက်ပြီ😪")
    else:
        await update.message.reply_text("မရပ်တော့ဘူးဆရာ ဒီတောသားကိုအရမ်းဆဲချင်နေပြီ🤪")

# --- MAIN RUN ---
async def main():
    keep_alive()
    
    for token in TOKENS:
        try:
            app_bot = ApplicationBuilder().token(token).build()
            app_bot.add_handler(CommandHandler("start", start))
            app_bot.add_handler(CommandHandler("spam", start_spam))
            app_bot.add_handler(CommandHandler("stun", stop_spam))
            
            await app_bot.initialize()
            await app_bot.start()
            await app_bot.updater.start_polling()
            print(f"🚀 Bot - {token[:10]}... Online!")
        except Exception as e:
            print(f"❌ Token error {token[:10]}: {e}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
