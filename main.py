import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging setup to see errors and other info
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- अपनी File IDs और Captions यहाँ डालें ---
FILE_DATA = {
    "Episode1": {
        "id": "BAACAgUAAxkBAAMXaGpSqvDgq-0fAszJ6iItqfYpI7wAAroTAALdcVBXt_ZT-2d9Lno2BA",
        "caption": "Yeh rahi aapki file, **Episode 1**! 🍿\n\nEnjoy the show!"
    },
    "Episode2": {
        "id": "BAACAgUAAxkBAAMKaGpLylL2eBYyfy9tX8wqGoVV12gAAv0VAALdcVBXBhEhvub79Q02BA",
        "caption": "Episode 2 aapke liye hazir hai. 🔥"
    },
    "Episode3": {
        "id": "BAACAgUAAyEFAAShOSZMAAMMaGpfS9qYzH5wqaRPNDsJ0ciP20oAAiwaAALcllFXDd-uaCejjP42BA",
        "caption": "Episode 3 kaisa laga harur bataye hai. 🔥"
    },
    "Episode4": {
        "id": "BAACAgUAAyEFAAShOSZMAAMNaGptb-AV1IS4pMYZnu0w8CE2ifcAAkUaAALcllFXV_eBJdoJfRI2BA",
        "caption": "Episode 4 kaisa laga harur bataye hai. 🔥"
    },
    "Episode5": {
        "id": "BAACAgUAAyEFAAShOSZMAAMOaGrMd7AfX7lSlMjp2j9eno1S-boAAr0aAALcllFXE2YkRJy7b8E2BA",
        "caption": "Episode 5 kaisa laga harur bataye hai. 🔥"
    },
    # आप और भी फाइलें ऐसे ही जोड़ सकते हैं
}

DELETE_DELAY = 1800

# --- UptimeRobot के लिए Keep-Alive सर्वर ---
app = Flask('')
@app.route('/')
def home():
    return "I'm alive and running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- बॉट के फंक्शन्स ---

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    message_id = job.data['message_id']
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Message {message_id} deleted from chat {chat_id}")
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Telegram policy ke kaaran mujhe yeh video delete karna pada. Umeed hai aapne ise save/download kar liya hoga. 🙏"
        )
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    if context.args:
        file_key = context.args[0]
        if file_key in FILE_DATA:
            file_info = FILE_DATA[file_key]
            file_id, video_caption = file_info["id"], file_info["caption"]
            try:
                # --- यहाँ सिंटैक्स ठीक किया गया है ---
                keyboard = [
                    [InlineKeyboardButton("🚀 Join Our Main Channel 🚀", url="https://t.me/Primium_Links")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                sent_message = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=video_caption, 
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="⚠️ Yeh file 30 minute mein automatically delete ho jayegi.\nPlease ise jaldi download ya save kar lein."
                )
                context.job_queue.run_once(delete_message, DELETE_DELAY, chat_id=chat_id, data={'message_id': sent_message.message_id})
            
            except Exception as e:
                logger.error(f"Failed to send video for key {file_key}: {e}")
                await update.message.reply_text("Sorry, is file ko bhejne mein kuch problem aa gayi hai.")
        else:
            await update.message.reply_text(f"Hello {user.first_name}! Lagta hai aapne jo link use kiya hai woh galat hai.")
    else:
        await update.message.reply_text(f"Hello {user.first_name}! File paane ke liye, please hamare main channel se diye gaye link ka use karein.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_to_check = update.message.reply_to_message
    if not message_to_check:
        await update.message.reply_text("Please kisi file par reply karke /id command use karein.")
        return

    file_id = None
    if message_to_check.video:
        file_id = message_to_check.video.file_id
    elif message_to_check.document:
        file_id = message_to_check.document.file_id
    
    if file_id:
        await update.message.reply_text(file_id)
    else:
        await update.message.reply_text("Is message mein koi supported file nahi mili. Please video ya document par reply karein.")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("CRITICAL ERROR: TELEGRAM_TOKEN not set in Secrets! Bot cannot start.")
        return

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", get_id))

    keep_alive()
    logger.info("Keep-alive server started. Bot is ready!")
    
    logger.info("Bot polling started...")
    application.run_polling()

if __name__ == '__main__':
    main()
