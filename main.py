import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest
import asyncio

# === बेसिक सेटअप ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- अपनी जानकारी यहाँ डालें ---

# 1. फोर्स सब्सक्राइब के लिए अपने चैनलों की जानकारी डालें
#    चैनल ID निकालने के लिए, चैनल से कोई मैसेज @userinfobot को फॉरवर्ड करें।
FORCE_SUB_CHANNELS = [
    {"chat_id": -1002599545967, "name": "Join 1", "invite_link": "https://t.me/+p2ErvvDmitZmYzdl"},
    {"chat_id": -1002391821078, "name": "Join 2", "invite_link": "https://t.me/+T4LO1ePja_I5NWQ1"}
]

# 2. अपनी फाइलों की जानकारी यहाँ डालें
FILE_DATA = {
    "Episode1": {"id": "FILE_ID_EPISODE_1", "caption": "<b>Episode 1</b>\nQuality: 720pHD"},
    "Episode2": {"id": "FILE_ID_EPISODE_2", "caption": "<b>Episode 2</b>\nQuality: 1080p"},
    # और फाइलें यहाँ जोड़ें
}

# 3. बॉट एडमिन की ID (आपकी अपनी टेलीग्राम यूजर ID)
ADMIN_IDS = [6056915535]  # अपनी यूजर ID @userinfobot से निकाल कर यहाँ डालें

# === कॉन्फ़िगरेशन ===
DELETE_DELAY = 1800  # 30 मिनट = 1800 सेकंड

# --- Keep-Alive सर्वर (Render + UptimeRobot के लिए) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- हेल्पर फंक्शन्स ---

user_requests = {}  # {user_id: "file_key"}

async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """चेक करता है कि यूजर सभी ज़रूरी चैनलों का मेंबर है या नहीं"""
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except BadRequest:
            logger.warning(f"Could not check membership for user {user_id} in channel {channel['chat_id']}. Maybe bot is not an admin?")
            return False
    return True

async def send_force_subscribe_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """यूजर को चैनल ज्वाइन करने का मैसेज भेजता है"""
    buttons = [[InlineKeyboardButton(ch["name"], url=ch["invite_link"])] for ch in FORCE_SUB_CHANNELS]
    buttons.append([InlineKeyboardButton("♻️ Try Again", callback_data=f"check_{context.user_data.get('file_key')}")])
    
    await update.message.reply_text(
        "Join both channels to access all features and download files.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def auto_delete_message(context: ContextTypes.DEFAULT_TYPE):
    """वीडियो और री-सेंड मैसेज को हैंडल करता है"""
    job = context.job
    chat_id = job.chat_id
    message_id_to_delete = job.data['message_id']
    file_key = job.data['file_key']
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        logger.info(f"Message {message_id_to_delete} deleted for user {chat_id}")
        
        # री-सेंड और क्लोज बटन भेजें
        keyboard = [
            [
                InlineKeyboardButton("♻️ Click Here", callback_data=f"resend_{file_key}"),
                InlineKeyboardButton("❌ Close ❌", callback_data="close_msg")
            ]
        ]
        text = (
            "Pʀᴇᴠɪᴏᴜs Mᴇssᴀɢᴇ ᴡᴀs Dᴇʟᴇᴛᴇᴅ 🗑\n"
            "Iғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ: [♻️ Cʟɪᴄᴋ Hᴇʀᴇ] ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴇʟsᴇ "
            "ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ. Bʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ᴄʟᴏsᴇ ʙᴜᴛᴛᴏɴ, ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ."
        )
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in auto_delete_message: {e}")

async def send_video_and_schedule_delete(user_id: int, file_key: str, context: ContextTypes.DEFAULT_TYPE):
    """वीडियो भेजता है और डिलीट का काम शेड्यूल करता है"""
    if file_key in FILE_DATA:
        file_info = FILE_DATA[file_key]
        
        sent_message = await context.bot.send_video(
            chat_id=user_id,
            video=file_info["id"],
            caption=file_info["caption"],
            parse_mode=ParseMode.HTML
        )
        
        warning_text = (
            "⚠️ Dᴜᴇ ᴛᴏ Cᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs....\n"
            "Yᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 30 Mɪɴᴜᴛᴇs. Sᴏ ᴘʟᴇᴀsᴇ ᴅᴏᴡɴʟᴏᴀᴅ ᴏʀ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ "
            "ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ."
        )
        await context.bot.send_message(chat_id=user_id, text=warning_text)
        
        context.job_queue.run_once(
            auto_delete_message, 
            DELETE_DELAY, 
            data={'message_id': sent_message.message_id, 'file_key': file_key}, 
            chat_id=user_id,
            name=f"delete_{user_id}_{sent_message.message_id}"
        )

# --- कमांड हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start कमांड को हैंडल करता है"""
    user = update.effective_user
    if context.args:
        file_key = context.args[0]
        context.user_data['file_key'] = file_key # फाइल की को याद रखें
        
        if await is_user_member(user.id, context):
            await send_video_and_schedule_delete(user.id, file_key, context)
        else:
            await send_force_subscribe_message(update, context)
    else:
        await update.message.reply_text("Welcome! Please use a link from our main channel to get files.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """बटनों के क्लिक को हैंडल करता है"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data
    
    if data.startswith("check_"):
        file_key = data.split("_")[1]
        if await is_user_member(user_id, context):
            await query.message.delete() # "Try Again" वाले मैसेज को डिलीट करें
            await send_video_and_schedule_delete(user_id, file_key, context)
        else:
            await query.answer("You haven't joined all channels yet. Please join and try again.", show_alert=True)
            
    elif data.startswith("resend_"):
        file_key = data.split("_")[1]
        await query.message.delete()
        await send_video_and_schedule_delete(user_id, file_key, context)
        
    elif data == "close_msg":
        await query.message.delete()

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """एडवांस्ड /id कमांड"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Sorry, this is an admin-only command.")
        return
        
    msg = update.message.reply_to_message
    if not msg:
        await update.message.reply_text("Please reply to a message to get its IDs.")
        return
        
    text = f"--- ℹ️ IDs Found ℹ️ ---\n\n"
    text += f"👤 **User ID:** `{msg.from_user.id}`\n"
    text += f"💬 **Chat ID:** `{msg.chat.id}`\n\n"
    
    file_id = None
    if msg.video: file_id = msg.video.file_id
    elif msg.document: file_id = msg.document.file_id
    elif msg.audio: file_id = msg.audio.file_id
    elif msg.photo: file_id = msg.photo[-1].file_id
        
    if file_id:
        text += f"📄 **File ID:**\n`{file_id}`"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

# --- मुख्य फंक्शन ---
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        logger.critical("Error: BOT_TOKEN not set in environment variables!")
        return

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("id", id_handler))

    keep_alive()
    logger.info("Keep-alive server started. Bot is ready!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
