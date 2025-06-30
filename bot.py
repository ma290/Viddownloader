import os
import json
import logging
from datetime import date
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from yt_dlp import YoutubeDL

# ---------- CONFIG ----------
BOT_TOKEN = "7286167945:AAG_FL_bJihubKbDVN7_ZxZBPnJmIwWLhsY"
OWNER_ID = 1442396009
OWNER_USERNAME = "mrvoidance"
ADMINS = [OWNER_ID, "6630039904"]  # usernames or user IDs
REQUIRED_CHANNEL = "mybotskallu"  # without @
DAILY_LIMIT = 5
DATA_FILE = "bot_state.json"
DOWNLOAD_DIR = "downloads"
# ---------------------------

logging.basicConfig(level=logging.INFO)

def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(uid):
    uid = str(uid)
    db = load_db()
    today = str(date.today())
    if uid not in db:
        db[uid] = {"quota": DAILY_LIMIT, "premium": False, "referrals": 0, "last_reset": today}
    elif db[uid]["last_reset"] != today and not db[uid]["premium"]:
        db[uid]["quota"] = DAILY_LIMIT
        db[uid]["last_reset"] = today
    save_db(db)
    return db[uid]

def update_user(uid, changes):
    uid = str(uid)
    db = load_db()
    user = get_user(uid)
    user.update(changes)
    db[uid] = user
    save_db(db)

def consume(uid):
    user = get_user(uid)
    if not user["premium"]:
        user["quota"] -= 1
        update_user(uid, user)

def add_referral(uid):
    user = get_user(uid)
    user["referrals"] += 1
    user["quota"] += 5
    update_user(uid, user)

def add_premium(uid): update_user(uid, {"premium": True, "quota": 999})
def remove_premium(uid): update_user(uid, {"premium": False, "quota": DAILY_LIMIT})
def is_admin(user): return str(user.id) in map(str, ADMINS) or user.username in ADMINS or user.username == OWNER_USERNAME

def check_subscription(bot: Bot, user_id):
    try:
        member = bot.get_chat_member(f"@{REQUIRED_CHANNEL}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def force_sub_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL}"),
            InlineKeyboardButton("✅ I've Subscribed", callback_data="subscribed")
        ]
    ])

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = str(user.id)
    if not check_subscription(context.bot, user.id):
        update.message.reply_text("🔒 Please subscribe to continue:", reply_markup=force_sub_buttons())
        return

    args = context.args
    if args and args[0].startswith("ref_"):
        ref = args[0].split("_")[1]
        if ref != uid:
            add_referral(ref)

    info = get_user(uid)
    ref_link = f"https://t.me/{context.bot.username}?start=ref_{uid}"
    text = f"👋 Welcome!\nYou have {info['quota']} downloads left today.\nPremium: {'✅' if info['premium'] else '❌'}\nReferrals: {info['referrals']}\n\n👥 Invite: {ref_link}"
    buttons = [[InlineKeyboardButton("🎁 Buy Premium ₹50", callback_data="buy")],
               [InlineKeyboardButton("👥 Invite Friends", url=ref_link)]]
    update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

def help_cmd(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user = get_user(uid)
    update.message.reply_text(f"""🆘 Bot Help\n\nSend a video/web link and I'll try to download it.\n\n🎯 Limits:\n- 5 downloads/day (free)\n- +5/downloads per referral\n- ₹50/month = Unlimited\n\n📊 You have {user['quota']} downloads left today.\n\nAdmin Commands:\n/add <uid>\n/rm <uid>\n/up""")

def admin_add(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user): return
    if context.args:
        uid = context.args[0]
        add_premium(uid)
        update.message.reply_text(f"✅ Premium added to {uid}")

def admin_rm(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user): return
    if context.args:
        uid = context.args[0]
        remove_premium(uid)
        update.message.reply_text(f"❌ Premium removed from {uid}")

def upload_db(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user): return
    update.message.reply_document(InputFile(DATA_FILE), caption="📂 User DB")

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    if query.data == "buy":
        context.bot.send_message(OWNER_ID, f"💰 @{user.username} wants Premium. Use /add {user.id}")
        query.edit_message_text("💡 Owner notified. Please wait.")
    elif query.data == "subscribed":
        if check_subscription(context.bot, user.id):
            query.edit_message_text("✅ Thank you! You may now use the bot.")
        else:
            query.answer("❌ You haven't subscribed yet.", show_alert=True)
    query.answer()

def download(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    if not check_subscription(context.bot, uid):
        update.message.reply_text("🔒 Please subscribe to continue:", reply_markup=force_sub_buttons())
        return

    info = get_user(uid)
    if info["quota"] <= 0 and not info["premium"]:
        btns = [[InlineKeyboardButton("🎁 Buy Premium ₹50", callback_data="buy")]]
        update.message.reply_text("❌ Daily limit used.", reply_markup=InlineKeyboardMarkup(btns))
        return

    url = update.message.text.strip()
    update.message.reply_text("⏬ Downloading...")
    opts = {
        "format": "bv*+ba/best",
        "merge_output_format": "mp4",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }
    try:
        with YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url)
            path = ydl.prepare_filename(data)
        update.message.reply_document(InputFile(path), caption=data.get("title", "🎬 Your file"))
        os.remove(path)
        consume(uid)
    except Exception as e:
        logging.error(e)
        update.message.reply_text("❗ Failed to download this link.")

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("add", admin_add))
    dp.add_handler(CommandHandler("rm", admin_rm))
    dp.add_handler(CommandHandler("up", upload_db))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, download))

    print("✅ Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
  
