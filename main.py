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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION (သင်ပေးထားသော Token အသစ်များ) ---
TOKENS = [
    "8959700806:AAF774P3QFqBbiBID2UnqLu6A_QXeCR1xu0", 
    "8638389490:AAF-nxGjx33831If2qmVrsyNHI8JBXjNvz0",                                
    "8697695665:AAFo-0E4WjbiOUBGLYWRv0aUBS7cGwy8vEw"                                 
]

# သုံးခွင့်ရှိမယ့် User ID များ (ဒီစာရင်းထဲကို ID အသစ်တွေ ကော်မာခံပြီး ထည့်နိုင်ပါတယ်)
AUTHORIZED_USERS = [7681995468] 

MY_LINK = "https://t.me/eccolism"

# 🚀 စနစ်တကျ ခွဲခြားရပ်နားနိုင်ရန် Task များကို သိမ်းဆည်းမည့် Global Dictionary
# ပုံစံ - { bot_id: { chat_id: task_object } }
all_running_tasks = {}

# --- ACCESS CONTROL HELPER ---
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

# --- BOT FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return await update.message.reply_text(
            f"❌ **မင်းကိုအရှင်အခင်အီကိုပေးမသုံးသေးဘူး။**\n\nဒီ Link ကိုအရင် Join လိုက်၊ ပြီးရင် အီကို့ဆီမှာအသနားသွားခံ -\n🔗 {MY_LINK}\n\n⚠️ (ပြီးရင် Dm မှာပါမစ်လာယူ @Ecco2k5)",
            disable_web_page_preview=False
        )
    await update.message.reply_text("✅ **အရှင်သခင်အီကို လိုအပ်ရာခိုင်းစေဖို့ အဆင်သင့်ပါပဲ!**")

async def start_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot_id = context.bot.id
    
    # ခွင့်ပြုချက် စစ်ဆေးခြင်း
    if not is_authorized(user_id):
        return await update.message.reply_text(f"❌ အရှင်သခင်အီကိုက ပေးမသုံးသေးဘူး။ အရင် Join ပါ: {MY_LINK}")

    # လက်ရှိ Bot ရဲ့ ဒီ Chat ထဲမှာ အဟောင်း Run နေတာရှိရင် အရင် Cancel လုပ်မယ်
    if bot_id in all_running_tasks and chat_id in all_running_tasks[bot_id]:
        all_running_tasks[bot_id][chat_id].cancel()

    # Target (ပစ်မှတ်) သတ်မှတ်ခြင်း
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

    # Spam Looping စနစ် (၀.၈ စက္ကန့်တစ်ကြိမ်)
    async def spam_worker():
        try:
            while True:
                for msg in messages:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"{target} {msg}", parse_mode=ParseMode.MARKDOWN)
                        await asyncio.sleep(0.8)
                    except Exception:
                        await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(spam_worker())
    if bot_id not in all_running_tasks:
        all_running_tasks[bot_id] = {}
    all_running_tasks[bot_id][chat_id] = task
    await update.message.reply_text(f"🔥 {target} ကို နှိပ်စက်ခြင်း စတင်ပါပြီ!")

# 1️⃣ /stop သို့မဟုတ် /stop @botusername (သက်ဆိုင်ရာ Bot တစ်ကောင်တည်းကိုပဲ လက်ရှိ Group မှာ ရပ်ခြင်း)
async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_bot_id = context.bot.id
    current_bot_username = context.bot.username
    
    if not is_authorized(user_id): return

    # @botusername ပါရင် စစ်ဆေးပြီး သက်ဆိုင်ရာကောင်ပဲ ရပ်မယ်
    if context.args:
        input_username = context.args[0].replace("@", "").strip()
        if current_bot_username and input_username.lower() != current_bot_username.lower():
            return 

    if current_bot_id in all_running_tasks and chat_id in all_running_tasks[current_bot_id]:
        all_running_tasks[current_bot_id][chat_id].cancel()
        del all_running_tasks[current_bot_id][chat_id]
        await update.message.reply_text(f"✅ @{current_bot_username} ကို ဒီ Group ထဲမှာ ရပ်နားလိုက်ပါပြီ!")
    else:
        await update.message.reply_text(f"❌ ဒီ Bot က ဒီ Group ထဲမှာ Spam မလုပ်နေပါဘူး။")

# 2️⃣ /3stun (ဘော့ (၃) ကောင်လုံးကို လက်ရှိ Group ထဲမှာတင် တစ်ပြိုင်နက်တည်း ရပ်တန့်ခြင်း)
async def stun_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not is_authorized(user_id): return

    stopped_count = 0
    for bot_id in list(all_running_tasks.keys()):
        if chat_id in all_running_tasks[bot_id]:
            all_running_tasks[bot_id][chat_id].cancel()
            del all_running_tasks[bot_id][chat_id]
            stopped_count += 1

    if stopped_count > 0:
        await update.message.reply_text(f"⚡ **/3stun အမိန့်အရ** ဘော့အားလုံးကို ဒီ Group ထဲမှာ အကုန်ရပ်လိုက်ပါပြီ!")
    else:
        await update.message.reply_text("❌ ဒီ Group ထဲမှာ Spam နေတဲ့ ဘော့ မရှိပါဘူး။")

# 3️⃣ /Reset (ဘယ် Group မှာမဆို ရှိသမျှ Bot တွေရဲ့ Spam Task အားလုံးကို တစ်ကမ္ဘာလုံးအတိုင်းအတာနဲ့ Force Kill လုပ်ခြင်း)
async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return

    total_killed = 0
    for bot_id in list(all_running_tasks.keys()):
        for chat_id in list(all_running_tasks[bot_id].keys()):
            all_running_tasks[bot_id][chat_id].cancel()
            total_killed += 1
            
    all_running_tasks.clear()
    await update.message.reply_text(f"🚨 **/Reset စနစ်ဖြင့်** ရှိသမျှ Group ပေါင်းစုံက Spam Task ({total_killed}) ခုလုံးကို လုံးဝ Clear လုပ်လိုက်ပါပြီ!")

# --- MAIN RUNNER ---
async def main():
    keep_alive()
    
    for token in TOKENS:
        try:
            app = ApplicationBuilder().token(token).build()
            
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("spam", start_spam))
            app.add_handler(CommandHandler("stop", stop_spam))
            app.add_handler(CommandHandler("3stun", stun_all))
            app.add_handler(CommandHandler("reset", reset_all))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            print(f"🚀 Bot Ready: {token.split(':')[0]}")
        except Exception as e:
            print(f"❌ Error starting bot: {e}")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
