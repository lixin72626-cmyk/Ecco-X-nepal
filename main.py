import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- WEB SERVER ---
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
# Bot Token ၃ ခုကို ဒီမှာ ထည့်ပါ
TOKENS = [
    "8959700806:AAHjIVA5NdDbLtS2WW2j95HJyTktElW4jXE", # Bot 1
    "8638389490:AAGK9d1J_Vx3y3JYpbQ5ajCRM3Mk4r8jYkk",                                # Bot 2
    "8697695665:AAFYHE7Vn8OARWR6CN2SnYdp_lVen3O35Ng"                                 # Bot 3
]
OWNER_ID = 7681995468 
running_spams = {}

# --- BOT FUNCTIONS (မပြောင်းလဲပါ) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **ဆရာအီကို့ Bot မှ ကြိုဆိုပါတယ်!**", parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းကိုဆရာအီကိုကခွင့်မပြုထားဘူး။ဆရာအီကို ၅ ခါခေါ်ရင်ပေးသုံးမယ်")
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
        await update.message.reply_text("❌ ပစ်မှတ်ထည့်ပါ။")
        return

    messages = ["ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံး နော် ငကြောင်မင်းကိုကြည့်မရလို့ဆဲနေတာ ပုကျိပုကျိစာကလေး လို့အော်ပြရင် ရပ်ပေးမယ်မင်းအမေစောက်ဖုတ်ကိုငါလီးနဲ့ထိုးသွင်းပီး တစ်ဇွတ်ထိုးဖြဲလိုး ​အထှာကျတဲ့ငကြောင်ရဲ့စတိုင်နဲ့ လီးကိုမှီချင်ရင်တော့ ဘုရားသခင်ချီကောင်းချီသာတောင်းပီး တစ်နေကုန်သာဆုတောင်းနေတော့ဟေး😈👈", "ဘာပြောပြောငါကဆဲမှာပဲ မင်းအမေလာတောင်းပန်ရင်တောင် ငါကခွင့်လွတ် မှာမဟုတ်ဘူး မင်းထက်အထာကျလို့ သခင်အီကိုဆိုပြီး ဆရာကြီးဖြစ်နေတာ လက်နက်ချပြီးအရှုံးပေးလိုက်တော့😜🤞", "မင်းအမေနဲ့ငါလိုးတုန်းကလည်းမင်းအမေအော်ခဲ့တာပဲ မင်းအော်တာလောက်ကတော့ငါကရင်တောင်မခုန်ဘူး မင်းရဲ့အော်သံတွေက မင်းအမေငိုသံတွေနဲ့တူသလို ပဲ ဘာ​ဖြစ်ဖြစ်မင်းကငါ့ကျွန်ဆိုတာ မင်းမမေ့ဖို့လို တယ် 😎👈", "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ် မယုံရင်ကောင်းကင်ကြီးကို လည်ပင်းညစ်ပီး ​ပြေးထိုးမေးလိုက် ရလဒ်ကတော့ အီကိုကမင်းအဖေဖြစ်တယ်ဆိုတာ ပိုသေချာသွားတာပေါ့ ချစ်သား🤪👈", "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ် မယုံရင်ကောင်းကင်ကြီးကို လည်ပင်းညစ်ပီး ​ပြေးထိုးမေးလိုက် ရလဒ်ကတော့ အီကိုကမင်းအဖေဖြစ်တယ်ဆိုတာ ပိုသေချာသွားတာပေါ့ ချစ်သား🤪👈"] # စာသားအပြည့်အစုံ ပြန်ထည့်ပါ

    async def spam_loop():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"{target_mention} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.6)
                    except:
                        await asyncio.sleep(5)
                        continue
        except asyncio.CancelledError: pass

    task = asyncio.create_task(spam_loop())
    running_spams[chat_id] = task

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    chat_id = update.effective_chat.id
    if chat_id in running_spams:
        running_spams[chat_id].cancel()
        del running_spams[chat_id]
        await update.message.reply_text("✅ ရပ်လိုက်ပြီ။")

# --- MAIN RUN (MULTI-BOT LOGIC) ---
async def main():
    keep_alive()
    
    # Bot အားလုံးကို သိမ်းမယ့် list
    apps = []
    
    for token in TOKENS:
        # Bot တစ်ခုချင်းစီအတွက် application ဆောက်မယ်
        builder = ApplicationBuilder().token(token).build()
        
        # Handler တွေ ထည့်မယ်
        builder.add_handler(CommandHandler("start", start))
        builder.add_handler(CommandHandler("spam", start_spam))
        builder.add_handler(CommandHandler("stop", stop_spam))
        
        # Bot ကို Initialize လုပ်မယ်
        await builder.initialize()
        await builder.start()
        await builder.updater.start_polling()
        apps.append(builder)
        print(f"🚀 Bot with token {token[:10]}... started!")

    # Bot တွေ အားလုံး အမြဲတမ်း Run နေအောင် လုပ်ထားမယ်
    while True:
        await asyncio.sleep(1000)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
