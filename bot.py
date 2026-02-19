import os
import threading
import instaloader
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ✅ TOKEN SETUP

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not set! Add it in Render Environment Variables.")

# ✅ ACTIVE USER CONTROL

active_users = set()

# ✅ INSTALOADER SETUP

loader = instaloader.Instaloader(
    dirname_pattern="downloads", save_metadata=False, download_comments=False
)

os.makedirs("downloads", exist_ok=True)

# ✅ DUMMY WEB SERVER (Render Free Plan)

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Telegram Bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


# ✅ MENU KEYBOARD


def get_menu():
    keyboard = [["📥 Download"], ["❓ Help", "❌ Exit"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ✅ START COMMAND


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_users.add(user_id)

    await update.message.reply_text(
        "👋 Welcome!\n\nSend Instagram Reel/Post link to download.",
        reply_markup=get_menu(),
    )


# ✅ EXIT COMMAND (stop for user only)


async def exit_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    active_users.discard(user_id)

    await update.message.reply_text(
        "👋 Bot stopped for you.\nSend /start to use again."
    )


# ✅ MENU BUTTON HANDLER


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if "help" in text:
        await update.message.reply_text("📌 Send Instagram reel/post link to download.")

    elif "exit" in text:
        await exit_bot(update, context)

    elif "download" in text:
        await update.message.reply_text("Send Instagram link.")


# ✅ DOWNLOAD FUNCTION


async def download_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ignore if user exited
    if user_id not in active_users:
        return

    url = update.message.text.strip()

    if "instagram.com" not in url:
        return

    message = await update.message.reply_text("Downloading... ⏳")

    try:
        # remove query parameters (?...)
        url = url.split("?")[0]

        # remove trailing slash
        url = url.rstrip("/")

        # extract shortcode
        parts = url.split("/")
        shortcode = parts[-1]

        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # clear old files
        for f in os.listdir("downloads"):
            os.remove(os.path.join("downloads", f))

        loader.download_post(post, target="downloads")

        sent = False

        for file in os.listdir("downloads"):
            path = os.path.join("downloads", file)

            if file.endswith(".mp4"):
                await update.message.reply_video(video=open(path, "rb"))
                sent = True

            elif file.endswith((".jpg", ".jpeg", ".png")):
                await update.message.reply_photo(photo=open(path, "rb"))
                sent = True

            os.remove(path)

        if not sent:
            await update.message.reply_text("⚠️ Media not found")

    except Exception as e:
        print(e)
        await update.message.reply_text("❌ Failed to download")

    finally:
        try:
            await message.delete()
        except:
            pass

        for f in os.listdir("downloads"):
            try:
                os.remove(os.path.join("downloads", f))
            except:
                pass


# ✅ TELEGRAM BOT SETUP

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("exit", exit_bot))
app.add_handler(
    MessageHandler(filters.Regex("^(📥 Download|❓ Help|❌ Exit)$"), menu_handler)
)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))

print("✅ Bot running...")

# run web server for Render
threading.Thread(target=run_web, daemon=True).start()

# run telegram bot
app.run_polling()
