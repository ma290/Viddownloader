import os
import json
import requests
import threading
import time
import pytz
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler

BOT_TOKEN = "7286167945:AAG_FL_bJihubKbDVN7_ZxZBPnJmIwWLhsY"
OWNER_ID = 1442396009
OWNER_USERNAME = "mrvoidance"
ADMINS = [OWNER_ID, 6630039904]
REQUIRED_CHANNEL = "mybotskallu"
DATA_FILE = "users.json"
PING_URL = "https://female-carilyn-namezakikr-443d0943.koyeb.app/"

# ------------------ USER DB -------------------
def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

users = load_db()

# ------------------ FORCE SUB ------------------
def check_subscription(user_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{REQUIRED_CHANNEL}&user_id={user_id}"
        resp = requests.get(url).json()
        return resp['result']['status'] in ['member', 'administrator', 'creator']
    except:
        return False

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    if uid not in users:
        users[uid] = {"downloads": 0, "ref": None, "premium": uid in ADMINS}
        save_db(users)

    if not check_subscription(uid):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")]
        ])
        await update.message.reply_text("🔒 Please join our channel to use this bot!", reply_markup=btn)
        return

    ref = context.args[0] if context.args else None
    if ref and ref != uid and users.get(ref):
        users[ref]["downloads"] += 5
        save_db(users)
        await context.bot.send_message(ref, f"🎁 You earned 5 downloads from a referral!")

    await update.message.reply_text(f"👋 Welcome {user.first_name}! Send a video link to download.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    count = users.get(uid, {}).get("downloads", 0)
    await update.message.reply_text(f"📄 Commands:\n/start - Start bot\n/help - Show help\n/referral - Get your link\n/up - Admin upload DB\n🎬 Remaining downloads: {count}")

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    await update.message.reply_text(f"🔗 Your referral link:\nhttps://t.me/{context.bot.username}?start={uid}")

async def upload_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    await update.message.reply_document(InputFile(open(DATA_FILE, "rb")), caption="📂 User DB")

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if context.args:
        users[context.args[0]] = {"downloads": 9999, "premium": True}
        save_db(users)
        await update.message.reply_text("✅ User added as premium")

async def admin_rm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if context.args and context.args[0] in users:
        users[context.args[0]]["premium"] = False
        save_db(users)
        await update.message.reply_text("❌ Premium removed")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if not check_subscription(uid):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}")]
        ])
        await update.message.reply_text("🔒 Please join our channel to use this bot!", reply_markup=btn)
        return

    if not users.get(uid, {}).get("premium") and users[uid]["downloads"] <= 0:
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Refer & Earn", callback_data="ref")],
            [InlineKeyboardButton("💎 Buy Premium (50rs)", url=f"https://t.me/{OWNER_USERNAME}")]
        ])
        await update.message.reply_text("🚫 Daily limit reached. Refer or buy premium!", reply_markup=btn)
        return

    url = update.message.text.strip()
    filename = f"video_{uid}.mp4"
    cmd = f"yt-dlp -f best -o {filename} {url}"
    os.system(cmd)

    if os.path.exists(filename):
        await context.bot.send_document(chat_id=uid, document=InputFile(filename))
        os.remove(filename)
        if not users[uid].get("premium"):
            users[uid]["downloads"] -= 1
            save_db(users)
    else:
        await update.message.reply_text("❌ Failed to download video. Try another link.")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "ref":
        uid = str(update.effective_user.id)
        await update.callback_query.message.reply_text(f"🔗 Your referral link:\nhttps://t.me/{context.bot.username}?start={uid}")

# ------------------ HTTP SERVER ------------------
def start_http_server():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("🌐 HTTP Server running on port 8000")
    server.serve_forever()

def ping():
    try:
        requests.get(PING_URL)
        print(f"🔁 Pinging {PING_URL}")
    except Exception as e:
        print(f"⚠️ Ping failed: {e}")

# ------------------ MAIN ------------------
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("up", upload_db))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CommandHandler("rm", admin_rm))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download))

    threading.Thread(target=start_http_server, daemon=True).start()

    # ✅ timezone fixed
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    scheduler.add_job(ping, "interval", minutes=5)
    scheduler.start()

    print("✅ Bot is running...")
    app.run_polling()
