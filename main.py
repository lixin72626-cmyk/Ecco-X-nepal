import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "All 4 Bots are Alive and Running!"

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

# --- SPAM LOGIC (မင်းပေးထားတဲ့အတိုင်း) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **ဆရာအီကို့ Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        "🚀 `/spam` [reply သို့မဟုတ် id] - စပမ်းရန်\n"
        "🛑 `/stop` - ရပ်တန့်ရန်",
        parse_mode=ParseMode.MARKDOWN
    )

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းကိုဆရာအီကိုကခွင့်မပြုထားဘူး။ ဆရာအီကိုလို့ ၅ ခါခေါ်ရင်ခွင့်ပေးမယ်။")
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
                        await asyncio.sleep(0.6) 
                    except Exception as e:
                        logging.warning(f"Error: {e}")
                        await asyncio.sleep(5)
                        continue
        except asyncio.CancelledError:
            logging.info(f"Spam stopped in chat {chat_id}")

    task = asyncio.create_task(spam_loop())
    running_spams[chat_id] = task

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id != OWNER_ID:
        await update.message.reply_text("❌ မင်းအဆင့်နဲ့ဘာကိုရပ်ချင်တာလဲ။ အရှင်သခင်အီကိုပဲရပ်လို့ရတယ်။")
        return

    if chat_id in running_spams:
        running_spams[chat_id].cancel()
        del running_spams[chat_id]
        await update.message.reply_text("✅ ဆရာအီကိုက ခွေးသေးလေးကို အနိုင်ကျင့်တာ ရပ်လိုက်ပြီ။")
    else:
        await update.message.reply_text("❌ လက်ရှိမှာ ဘာစပမ်းမှ မလုပ်နေပါဘူး ဘရို။")

# --- BOT RUNNER FOR MULTIPLE BOTS ---

async def run_bot_instance(token, bot_name):
    """Bot တစ်ခုချင်းစီကို သီးခြားစီ run ပေးမည့် function"""
    application = ApplicationBuilder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("spam", start_spam))
    application.add_handler(CommandHandler("stop", stop_spam))
    
    await application.initialize()
    await application.start_polling()
    print(f"🚀 {bot_name} is running!")
    
    # Bot အမြဲတမ်း နိုးနေစေရန်
    while True:
        await asyncio.sleep(3600)

async def main():
    # မင်းပေးထားတဲ့ Token ၄ ခုလုံးကို ဒီမှာ စုစည်းထားပါတယ်
    tokens = [
        ("8959700806:AAEXzhnkmw6sY9w1xJqOVrmcjHG_VLFgzEk", "Main_Bot"),
        ("8638389490:AAGK9d1J_Vx3y3JYpbQ5ajCRM3Mk4r8jYkk", "Bot_1"),
        ("8697695665:AAFwasTJ_9AZZN92gkBOWbhAPKqWFhhbVlM", "Bot_2"),
        ("8605823225:AAHx4K9G8In5m2hjxonDX6-I3g9wVfgSCiw", "Bot_3")
    ]
    
    # Tasks အားလုံးကို တစ်ပြိုင်တည်း run ခိုင်းခြင်း
    tasks = [run_bot_instance(t, n) for t, n in tokens]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    keep_alive() # Web server စတင်ခြင်း
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
