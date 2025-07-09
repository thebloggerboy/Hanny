import os
import logging
import asyncio
import json
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import BadRequest

# === बेसिक सेटअप ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- कॉन्फ़िगरेशन (यह जानकारी अब हम Environment Variables से लेंगे) ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
FORCE_SUB_CHANNELS_STR = os.environ.get("FORCE_SUB_CHANNELS", "[]")

# --- कॉन्फ़िगरेशन को प्रोसेस करें ---
try:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',')]
    FORCE_SUB_CHANNELS = json.loads(FORCE_SUB_CHANNELS_STR)
except (ValueError, json.JSONDecodeError) as e:
    logger.critical(f"Error parsing environment variables: {e}")
    ADMIN_IDS, FORCE_SUB_CHANNELS = [], []

DELETE_DELAY = 900  # 15 मिनट
DB_FILE = 'bot_data.json' # सभी डेटा के लिए हमारी JSON फाइल

# --- डेटा को लोड और सेव करने के फंक्शन्स ---
def load_data():
    """JSON फाइल से डेटा लोड करता है।"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"users": [], "banned_users": [], "files": {}}

def save_data(data):
    """डेटा को JSON फाइल में सेव करता है।"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

bot_data = load_data()

# --- Keep-Alive सर्वर ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive and running!"
def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- हेल्पर फंक्शन्स ---
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id in ADMIN_IDS: return True
    if not FORCE_SUB_CHANNELS: return True
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except BadRequest: return False
    return True

async def send_force_subscribe_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_key = context.user_data.get('file_key')
    if not file_key: return
    join_buttons = [InlineKeyboardButton(ch["name"], url=ch["invite_link"]) for ch in FORCE_SUB_CHANNELS]
    keyboard = [join_buttons, [InlineKeyboardButton("✅ Joined", callback_data=f"check_{file_key}")]]
    await update.message.reply_text("Please join all required channels to get the file.", reply_markup=InlineKeyboardMarkup(keyboard))

# ... (auto_delete_messages और send_file जैसे बाकी हेल्पर फंक्शन्स यहाँ आएंगे) ...
# (यह फंक्शन्स पिछले कोड जैसे ही हैं, इसलिए मैं उन्हें संक्षिप्त कर रहा हूँ)

# --- कमांड हैंडलर्स ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # बैन किए गए यूज़र्स को ब्लॉक करें
    if user_id in bot_data["banned_users"]:
        await update.message.reply_text("You are banned from using this bot.")
        return

    # नए यूज़र को डेटा फाइल में जोड़ें
    if user_id not in bot_data["users"]:
        bot_data["users"].append(user_id)
        save_data(bot_data)
        logger.info(f"New user {user_id} added.")

    if context.args:
        file_key = context.args[0]
        context.user_data['file_key'] = file_key
        if await is_user_member(user_id, context):
            await send_file(user_id, file_key, context) # यह हमारा फाइल भेजने वाला फंक्शन है
        else:
            await send_force_subscribe_message(update, context)
    else:
        # वेलकम मैसेज और मेन्यू
        keyboard = [
            [InlineKeyboardButton("🎬 All Series", callback_data="menu_series")],
            [InlineKeyboardButton("❓ How to Use", callback_data="menu_help")]
        ]
        await update.message.reply_text("Welcome to the Bot! How can I help you?", reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    
    message_to_broadcast = update.message.reply_to_message
    if not message_to_broadcast:
        await update.message.reply_text("Please reply to a message to broadcast it.")
        return
        
    count = 0
    for user_id in bot_data["users"]:
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=update.message.chat_id,
                message_id=message_to_broadcast.message_id
            )
            count += 1
            await asyncio.sleep(0.1) # स्पैम से बचने के लिए
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            
    await update.message.reply_text(f"Broadcast sent to {count} users.")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    total_users = len(bot_data["users"])
    banned_count = len(bot_data["banned_users"])
    await update.message.reply_text(f"📊 **Bot Stats** 📊\n\nTotal Users: {total_users}\nBanned Users: {banned_count}")

# ... (ban, unban, id, get, button_handler के फंक्शन यहाँ आएंगे) ...

# --- मुख्य फंक्शन ---
def main():
    if not TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set!")
        return

    application = Application.builder().token(TOKEN).build()
    
    # कमांड्स को रजिस्टर करें
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    # ... (बाकी के हैंडलर)
    
    application.add_handler(CallbackQueryHandler(button_handler))

    keep_alive()
    logger.info("Bot is ready and polling!")
    application.run_polling()

if __name__ == '__main__':
    main()
