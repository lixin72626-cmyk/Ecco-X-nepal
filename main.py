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
# ⚠️ Bot Token ၃ ခုလုံးကို ဒီမှာ အမှန်ပြင်ထည့်ပါ
TOKENS = [
    "8959700806:AAG4xuyDTIfOECe49BD0pcY94nI4ix9btVo", # Bot ၁
    "8638389490:AAEL9cCCZo0V2E7q5_3gpx1MvWz5yM9LmJk",                                # Bot ၂
    "8697695665:AAEvel5LGpyuk9EhB53pmYM3W4UZpAUyk0E"                                 # Bot ၃
]
OWNER_ID = 7681995468 

# { "bot_token": { "chat_id": task } } ပုံစံမျိုးနဲ့ ခွဲမှတ်ပြီး ရပ်လို့ရအောင် လုပ်ထားပါတယ်
running_spams = {token: {} for token in TOKENS}

# --- BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **ဆရာအီကို့ Bot မှ ကြိုဆိုပါတယ်!**", parse_mode=ParseMode.MARKDOWN)

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_token = context.application.bot.token  # ဘယ် Bot ထဲမှာ ရောက်နေလဲ သိအောင်လုပ်ခြင်း
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းကိုဆရာအီကိုကခွင့်မပြုထားဘူး။")
        return

    # လက်ရှိ Bot ရဲ့ chat ထဲမှာ run နေလား စစ်မယ်
    if chat_id in running_spams[current_token]:
        await update.message.reply_text("⚠️ ဒီ Bot က စပမ်းနေတုန်းပါ ဘရို။")
        return

    # --- Target (ပစ်မှတ်) ရှာဖွေခြင်း အဆင့်မြင့်ပြင်ဆင်ချက် ---
    target_mention = ""
    
    # ၁။ ရိုးရိုး Reply ပြန်ထားရင် ယူမယ့်ပုံစံ (Mention မလိုတော့ပါ)
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        if user.username:
            target_mention = f"@{user.username}"
        else:
            target_mention = f"[{user.first_name}](tg://user?id={user.id})"
            
    # ၂။ Argument ထည့်ထားရင် ယူမယ့်ပုံစံ (ဥပမာ- /spam @username သို့မဟုတ် /spam id)
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
    running_spams[current_token][chat_id] = task  # သက်ဆိုင်ရာ Bot ရဲ့ စာရင်းထဲပဲ ထည့်မှတ်မယ်

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_token = context.application.bot.token
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းအဆင့်နဲ့ဘာကိုရပ်ချင်တာလဲ။ အရှင်သခင်အီကိုပဲရပ်လို့ရတယ်။")
        return
    
    # သက်ဆိုင်ရာ Bot ရဲ့ စာရင်းထဲကနေပဲ ရှာပြီး ရပ်မယ်
    if chat_id in running_spams[current_token]:
        running_spams[current_token][chat_id].cancel()
        del running_spams[current_token][chat_id]
        await update.message.reply_text("✅ ဆရာအီကိုက ခွေးသေးလေးကို အနိုင်ကျင့်တာ ရပ်လိုက်ပြီ။")
    else:
        await update.message.reply_text("❌ လက်ရှိမှာ ဘာစပမ်းမှ မလုပ်နေပါဘူး ဘရို။")

# --- MAIN RUN ---
async def main():
    keep_alive()
    
    # Token တစ်ခုချင်းစီအတွက် Loop ပတ်ပြီး သီးသန့် အလုပ်လုပ်ခိုင်းမယ်
    for token in TOKENS:
        if token.startswith("TOKEN_"): # Token အမှန်မထည့်ရသေးရင် ကျော်သွားဖို့
            continue
            
        app_bot = ApplicationBuilder().token(token).build()
        
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("spam", start_spam))
        app_bot.add_handler(CommandHandler("stop", stop_spam))
        
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling()
        print(f"🚀 Bot - {token[:10]}... Started Successfully!")

    # Bot ၃ ကောင်လုံး ပြိုင်တူ သေဆုံးမသွားဘဲ စောင့်ကြည့်နေမယ့်နေရာ
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
