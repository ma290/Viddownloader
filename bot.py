import os
import json
import requests
import threading
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

# --- Config ---
BOT_TOKEN = "7286167945:AAG_FL_bJihubKbDVN7_ZxZBPnJmIwWLhsY"
OWNER_ID = 1442396009
OWNER_USERNAME = "mrvoidance"
ADMINS = [OWNER_ID, 6630039904]
REQUIRED_CHANNEL = "mybotskallu"
DATA_FILE = "users.json"
PING_URL = "https://female-carilyn-namezakikr-443d0943.koyeb.app/"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# --- DB Management ---
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

users = load_db()

# Ensure admins always present
for admin in ADMINS:
    uid = str(admin)
    if uid not in users:
        users[uid] = {"downloads": 9999, "premium": True}
save_db(users)

# --- Sub Check ---
def check_subscription(user_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{REQUIRED_CHANNEL}&user_id={user_id}"
        resp = requests.get(url).json()
        return resp['result']['status'] in ['member', 'administrator', 'creator']
    except:
        return False

# --- Bot Handlers ---
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = str(user.id)

    if uid not in users:
        users[uid] = {"downloads": 0, "ref": None, "premium": uid in ADMINS}
        save_db(users)

    if not check_subscription(user.id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")]
        ])
        update.message.reply_text("🔒 Please join our channel to use this bot!", reply_markup=btn)
        return

    args = context.args
    if args:
        ref = args[0]
        if ref != uid and ref in users:
            users[ref]["downloads"] += 5
            save_db(users)
            context.bot.send_message(chat_id=int(ref), text="🎁 You earned 5 downloads from a referral!")

    update.message.reply_text(f"👋 Welcome {user.first_name}! Send a video link to download.")

def help_cmd(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    count = users.get(uid, {}).get("downloads", 0)
    update.message.reply_text(
        f"📄 Commands:\n/start - Start bot\n/help - Show help\n/referral - Get your link\n/up - Admin upload DB\n🎬 Remaining downloads: {count}"
    )

def referral(update: Update, context: CallbackContext):
    uid = str(update.effective_user.id)
    update.message.reply_text(f"🔗 Your referral link:\nhttps://t.me/{context.bot.username}?start={uid}")

def upload_db(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMINS:
        return
    update.message.reply_document(InputFile(open(DATA_FILE, "rb")), caption="📂 User DB")

def admin_add(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMINS:
        return
    if context.args:
        uid = context.args[0]
        users[uid] = {"downloads": 9999, "premium": True}
        save_db(users)
        update.message.reply_text("✅ User added as premium")

def admin_rm(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMINS:
        return
    if context.args:
        uid = context.args[0]
        if uid in users:
            users[uid]["premium"] = False
            save_db(users)
            update.message.reply_text("❌ Premium removed")

def download(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = str(user.id)

    if uid not in users:
        users[uid] = {"downloads": 0, "ref": None, "premium": uid in ADMINS}
        save_db(users)

    if not check_subscription(uid):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")]
        ])
        update.message.reply_text("🔒 Please join our channel to use this bot!", reply_markup=btn)
        return

    user_data = users.get(uid)
    if not user_data.get("premium") and user_data["downloads"] <= 0:
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Refer & Earn", callback_data="ref")],
            [InlineKeyboardButton("💎 Buy Premium (50rs)", url=f"https://t.me/{OWNER_USERNAME}")]
        ])
        update.message.reply_text("🚫 Daily limit reached. Refer or buy premium!", reply_markup=btn)
        return

    url = update.message.text.strip()
    filename = f"video_{uid}.mp4"
    cmd = f"yt-dlp -f best -o {filename} {url}"
    os.system(cmd)

    if os.path.exists(filename):
        update.message.reply_document(InputFile(filename))
        os.remove(filename)
        if not user_data.get("premium"):
            user_data["downloads"] -= 1
            save_db(users)
    else:
        update.message.reply_text("❌ Failed to download video. Try another link.")

def callback(update: Update, context: CallbackContext):
    if update.callback_query.data == "ref":
        uid = str(update.effective_user.id)
        update.callback_query.message.reply_text(f"🔗 Your referral link:\nhttps://t.me/{context.bot.username}?start={uid}")

# --- HTTP Server ---
def start_http_server():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): return
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("🌐 HTTP Server running on port 8000")
    server.serve_forever()

def ping():
    try:
        requests.get(PING_URL)
        print(f"🔁 Pinging {PING_URL}")
    except Exception as e:
        print(f"⚠️ Ping failed: {e}")

# --- Main ---
if __name__ == "__main__":
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("referral", referral))
    dp.add_handler(CommandHandler("up", upload_db))
    dp.add_handler(CommandHandler("add", admin_add))
    dp.add_handler(CommandHandler("rm", admin_rm))
    dp.add_handler(CallbackQueryHandler(callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, download))

    # Run web server
    threading.Thread(target=start_http_server, daemon=True).start()

    # Run scheduler with timezone
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(ping, IntervalTrigger(minutes=5, timezone=TIMEZONE))
    scheduler.start()

    print("✅ Bot is running...")
    updater.start_polling()
    updater.idle()
