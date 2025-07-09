import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

# === बेसिक सेटअप ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- आपकी जानकारी यहाँ पहले से डाल दी गई है ---

# 1. फोर्स सब्सक्राइब के लिए चैनल
FORCE_SUB_CHANNELS = [
    {
        "chat_id": -1002599545967, 
        "name": "Join 1", 
        "invite_link": "https://t.me/+p2ErvvDmitZmYzdl"
    },
    {
        "chat_id": -1002391821078, 
        "name": "Join 2", 
        "invite_link": "https://t.me/+T4LO1ePja_I5NWQ1"
    }
]

# 2. आपकी फाइलें
FILE_DATA = {
    "Episode1": {
        "id": "BAACAgUAAxkBAAMXaGpSqvDgq-0fAszJ6iItqfYpI7wAAroTAALdcVBXt_ZT-2d9Lno2BA", 
        "caption": "<b>Episode 1</b>\nQuality: 720pHD"
    },
    "Episode2": {
        "id": "BAACAgUAAxkBAAMKaGpLylL2eBYyfy9tX8wqGoVV12gAAv0VAALdcVBXBhEhvub79Q02BA", 
        "caption": "<b>Episode 2</b>\nQuality: 1080p"
    },
    "Episode6": {
        "id": "BAACAgUAAxkBAAMZaG68Tzi21IIlqaOU6FXRhEgUI6UAAmYWAALclllXrHLTroekKok2BA", 
        "caption": "<b>Episode 2</b>\nQuality: 1080p"
    },
    # और फाइलें यहाँ जोड़ें
}

# 3. आपकी एडमिन ID
ADMIN_IDS = [6056915535]

# === कॉन्फ़िगरेशन ===
DELETE_DELAY = 1800  # 30 मिनट

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
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except BadRequest: return False
    return True

async def send_force_subscribe_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[InlineKeyboardButton(ch["name"], url=ch["invite_link"])] for ch in FORCE_SUB_CHANNELS]
    buttons.append([InlineKeyboardButton("✅ Joined", callback_data=f"check_{context.user_data.get('file_key')}")])
    await update.message.reply_text("Join both channels to access all features and download files.", reply_markup=InlineKeyboardMarkup(buttons))

async def auto_delete_messages(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id, message_ids_to_delete, file_key = job.chat_id, job.data['message_ids'], job.data['file_key']
    try:
        for msg_id in message_ids_to_delete:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        keyboard = [[InlineKeyboardButton("♻️ Click Here", callback_data=f"resend_{file_key}"), InlineKeyboardButton("❌ Close ❌", callback_data="close_msg")]]
        text = "Pʀᴇᴠɪᴏᴜs Mᴇssᴀɢᴇ ᴡᴀs Dᴇʟᴇᴛᴇᴅ 🗑\nIғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ: [♻️ Cʟɪᴄᴋ Hᴇʀᴇ] ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴇʟsᴇ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ. Bʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ᴄʟᴏsᴇ ʙᴜᴛᴛᴏɴ, ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ."
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in auto_delete_messages: {e}")

async def send_video_and_schedule_delete(user_id: int, file_key: str, context: ContextTypes.DEFAULT_TYPE):
    if file_key in FILE_DATA:
        file_info = FILE_DATA[file_key]
        video_message = await context.bot.send_video(chat_id=user_id, video=file_info["id"], caption=file_info["caption"], parse_mode='HTML')
        warning_text = "⚠️ Dᴜᴇ ᴛᴏ Cᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs....\nYᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 30 Mɪɴᴜᴛᴇs. Sᴏ ᴘʟᴇᴀsᴇ ᴅᴏᴡɴʟᴏᴀᴅ ᴏʀ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ."
        warning_message = await context.bot.send_message(chat_id=user_id, text=warning_text)
        context.job_queue.run_once(auto_delete_messages, DELETE_DELAY, data={'message_ids': [video_message.message_id, warning_message.message_id], 'file_key': file_key}, chat_id=user_id)

# --- कमांड हैंडलर्स ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.args:
        file_key = context.args[0]
        context.user_data['file_key'] = file_key
        if await is_user_member(user.id, context):
            await send_video_and_schedule_delete(user.id, file_key, context)
        else:
            await send_force_subscribe_message(update, context)
    else:
        await update.message.reply_text("Welcome! Please use a link from our main channel to get files.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    if data.startswith("check_"):
        await query.answer()
        file_key = data.split("_", 1)[1]
        if await is_user_member(user_id, context):
            await query.message.delete()
            await send_video_and_schedule_delete(user_id, file_key, context)
        else:
            await query.answer("You haven't joined all channels yet. Please join and try again.", show_alert=True)
    elif data.startswith("resend_"):
        await query.answer()
        file_key = data.split("_", 1)[1]
        await query.message.delete()
        await send_video_and_schedule_delete(user_id, file_key, context)
    elif data == "close_msg":
        await query.message.delete()

async def get_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    msg = update.message.reply_to_message
    if not msg:
        await update.message.reply_text("Please reply to a message to get its IDs.")
        return
    text = f"--- ℹ️ IDs Found ℹ️ ---\n\n👤 User ID: {msg.from_user.id}\n💬 Chat ID: {msg.chat.id}\n\n"
    file_id = None
    if msg.video: file_id = msg.video.file_id
    elif msg.document: file_id = msg.document.file_id
    if file_id: text += f"📄 File ID:\n{file_id}"
    await update.message.reply_text(text)

async def get_forward_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    msg = update.message.reply_to_message
    if not msg or not msg.forward_origin:
        await update.message.reply_text("Please reply to a FORWARDED message from a channel.")
        return
    origin = msg.forward_origin
    text = f"--- ℹ️ Forwarded Message IDs ℹ️ ---\n\n📢 Original Channel ID: {origin.chat.id}\n\n"
    file_id = None
    if msg.video: file_id = msg.video.file_id
    elif msg.document: file_id = msg.document.file_id
    if file_id: text += f"📄 File ID:\n{file_id}"
    await update.message.reply_text(text)

# --- मुख्य फंक्शन ---
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        logger.critical("Error: BOT_TOKEN not set!")
        return

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("id", get_id_handler))
    application.add_handler(CommandHandler("get", get_forward_id_handler))

    keep_alive()
    logger.info("Keep-alive server started. Bot is ready!")
    application.run_polling()

if __name__ == '__main__':
    main()
