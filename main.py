import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# Error Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIG ---
TOKEN = "8959700806:AAEXzhnkmw6sY9w1xJqOVrmcjHG_VLFgzEk"
OWNER_ID = 7681995468  # ဘရိုရဲ့ User ID

running_spams = {}

# --- BOT FUNCTIONS ---
async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # ၁။ ဘရို (Owner) ဟုတ်မဟုတ် အရင်စစ်မယ်
    if user_id != OWNER_ID:
        # ဘရိုမဟုတ်ရင် ဘာမှပြန်မပြောဘဲ Ignore လုပ်ထားမယ်
        return

    # ၂။ Spamming လုပ်နေရင် ထပ်မလုပ်ဖို့
    if chat_id in running_spams:
        await update.message.reply_text("⚠️ စပမ်းနေတုန်းပါ ဘရို။ ရပ်ချင်ရင် /stop နှိပ်ပါ။")
        return

    target_mention = ""

    # Target ရှာဖွေခြင်း
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
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=f"{target_mention} {msg}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # မြန်နှုန်းမြင့် (၀.၃ စက္ကန့်)
                    await asyncio.sleep(0.3)
        except Exception as e:
            logging.error(f"Error: {e}")

    task = asyncio.create_task(spam_loop())
    running_spams[chat_id] = task

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    chat_id = update.effective_chat.id
    if chat_id in running_spams:
        running_spams[chat_id].cancel()
        del running_spams[chat_id]
        await update.message.reply_text("ဆရာအီကိုကခွေး​သေး​လေးကိုအနိုင်ကျင့်တာရပ်လိုက်ပြီ။")
    else:
        await update.message.reply_text("❌ ဘာမှ လုပ်မနေပါ ဘရို။")

# --- MAIN RUN ---
if __name__ == "__main__":
    keep_alive()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("spam", start_spam))
    app_bot.add_handler(CommandHandler("stop", stop_spam))
    
    print("🚀 Bot is running for Owner ONLY across all groups!")
    app_bot.run_polling()
