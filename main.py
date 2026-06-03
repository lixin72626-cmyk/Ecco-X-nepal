import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- WEB SERVER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Multi-Bots System is Online & Fully Fixed!"

def run():
    # Render သို့မဟုတ် အခြား Hosting တွေအတွက် Port 8080 ကို သုံးပါတယ်
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION (သေချာစစ်ဆေးပြီးသား Token များ) ---
TOKENS = [
    "8959700806:AAEmQkfrDB38_gbyxIEBYYjyfzWwM_1vYDM", 
    "8638389490:AAGmHdnp5p1PJpScyYpKZ593uP4N_Gq6kCE",                                
    "8697695665:AAHCzpDOG8fKVCQ42qUM7hr7MWDCbhNUjwY"                                 
]

# သုံးခွင့်ရှိမယ့် User ID များ (ဒီစာရင်းထဲကို ID အသစ်တွေ ကော်မာခံပြီး ထည့်နိုင်ပါတယ်)
AUTHORIZED_USERS = [7681995468] 

MY_LINK = "https://t.me/kai_iz_mad51"

# --- ACCESS CONTROL HELPER ---
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

# --- BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return await update.message.reply_text(
            f"❌ **မင်းမှာ သုံးပိုင်ခွင့်မရှိဘူး။**\n\nဒီ Link ကို အရင် Join ပါ -\n🔗 {MY_LINK}\n\n⚠️ (မ Join ရင် ရည်းစားမရပါစေနဲ့နော်)",
            disable_web_page_preview=False
        )
    await update.message.reply_text("✅ **အရှင်သခင်အီကို ခိုင်းစေဖို့ အဆင်သင့်ပါပဲ!**")

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # ၁။ ခွင့်ပြုချက် စစ်ဆေးခြင်း
    if not is_authorized(user_id):
        return await update.message.reply_text(f"❌ သုံးခွင့်မရှိဘူး။ အရင် Join ပါ: {MY_LINK}")

    # ၂။ အရင် run နေတဲ့ Task ရှိရင် ချက်ချင်း ရပ်ပစ်ခြင်း (Stop logic ပိုသေချာစေရန်)
    if 'current_task' in context.chat_data:
        context.chat_data['current_task'].cancel()

    # ၃။ Target (ပစ်မှတ်) သတ်မှတ်ခြင်း
    target = ""
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        target = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    elif context.args:
        target = context.args[0]
    else:
        return await update.message.reply_text("❌ ဘယ်သူ့ကို ဆဲရမလဲ (Reply ပြန်ပါ သို့မဟုတ် ID/Username ထည့်ပါ)")

    messages = [
        "ဟိတ် တအားအဆဲခံနေရလို့ဂုဏ်ယူမနေနဲ့အုံး နော် ငကြောင်မင်းကိုကြည့်မရလို့ဆဲနေတာ ပုကျိပုကျိစာကလေး လို့အော်ပြရင် ရပ်ပေးမယ်မင်းအမေစောက်ဖုတ်ကိုငါလီးနဲ့ထိုးသွင်းပီး တစ်ဇွတ်ထိုးဖြဲလိုး ​အထှာကျတဲ့ငကြောင်ရဲ့စတိုင်နဲ့ လီးကိုမှီချင်ရင်တော့ ဘုရားသခင်ချီကောင်းချီသာတောင်းပီး တစ်နေကုန်သာဆုတောင်းနေတော့ဟေး😈👈", 
        "ဘာပြောပြောငါကဆဲမှာပဲ မင်းအမေလာတောင်းပန်ရင်တောင် ငါကခွင့်လွတ် မှာမဟုတ်ဘူး မင်းထက်အထာကျလို့ သခင်အီကိုဆိုပြီး ဆရာကြီးဖြစ်နေတာ လက်နက်ချပြီးအရှုံးပေးလိုက်တော့😜🤞", 
        "မင်းအမေနဲ့ငါလိုးတုန်းကလည်းမင်းအမေအော်ခဲ့တာပဲ မင်းအော်တာလောက်ကတော့ငါကရင်တောင်မခုန်ဘူး မင်းရဲ့အော်သံတွေက မင်းအမေငိုသံတွေနဲ့တူသလို ပဲ ဘာ​ဖြစ်ဖြစ်မင်းကငါ့ကျွန်ဆိုတာ မင်းမမေ့ဖို့လို တယ် 😎👈", 
        "ကြောက်ရွံ မှုတွေရဲ့အထက်မှု မှာမင်းရဲ့အဖေ အီကိုပဲရှိတယ် မယုံရင်ကောင်းကင်ကြီးကို လည်ပင်းညစ်ပီး ​ပြေးထိုးမေးလိုက် ရလဒ်ကတော့ အီကိုကမင်းအဖေဖြစ်တယ်ဆိုတာ ပိုသေချာသွားတာပေါ့ ချစ်သား🤪👈", 
        "မင်းအမေစောက်ဖုတ်ကိုဂျွမ်းပြစ်လိုး လိုက်ရ ကမ္ဘာ့အပြင်ဘက်ကိုရောက်ရုံတောင်မက ဂြိုလ်သားတွေနဲ့ မိတ်လိုက်ပြီးလျှပ်စစ်တွေ လျှက်ကုန်မယ် ကောင်းကင်မှာ လျှပ်စစ်လျက်ရင် မင်းအမေနဲ့ဂြိုလ်သားလိုးနေတယ်လို့သာမှတ်ထားလိုက် 😳👈"
    ]

    # ၄။ Spam Worker (Looping စနစ်)
    async def spam_worker():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"{target} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.8) # ၀.၈ စက္ကန့် တစ်ကြိမ်
                    except Exception:
                        await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass # ရပ်လိုက်တဲ့အခါ တိတ်တဆိတ် ထွက်သွားမယ်

    # Task ကို စာရင်းသွင်းပြီး စတင်မယ်
    task = asyncio.create_task(spam_worker())
    context.chat_data['current_task'] = task
    await update.message.reply_text(f"🔥 {target} ကို နှိပ်စက်ခြင်း စတင်ပါပြီ!")

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    # ၅။ Task ကို ပြတ်ပြတ်သားသား ရပ်ပစ်ခြင်း
    if 'current_task' in context.chat_data:
        context.chat_data['current_task'].cancel()
        del context.chat_data['current_task']
        await update.message.reply_text("✅ **အရှင်သခင်အီကို့အမိန့်အရ ရပ်လိုက်ပြီ!**")
    else:
        await update.message.reply_text("❌ ရပ်စရာ Spamming မရှိပါဘူး။")

# --- MAIN RUNNER ---
async def main():
    keep_alive() # Web server စတင်ခြင်း
    
    for token in TOKENS:
        try:
            app = ApplicationBuilder().token(token).build()
            
            # Commands များ ထည့်သွင်းခြင်း
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("spam", start_spam))
            app.add_handler(CommandHandler("stop", stop_spam))
            
            # Bot တစ်ကောင်ချင်းစီကို Initialize လုပ်ခြင်း
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            print(f"🚀 Bot {token.split(':')[0]} is Ready!")
        except Exception as e:
            print(f"❌ Token Error {token[:10]}: {e}")

    # Bot တွေ အားလုံး မပိတ်သွားအောင် စောင့်ကြည့်နေခြင်း
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
