import os
import sys
import asyncio
import instaloader
from telegram import Update, BotCommand, MenuButtonCommands
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# =========================
# AUTO RESTART EVERY 10 MINUTES
# =========================


async def auto_restart():
    await asyncio.sleep(600)
    print("♻️ Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


# =========================
# LOAD ENV FILE SAFELY
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)

# =========================
# TOKEN SETUP
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set!")

# =========================
# RENDER PORT + WEBHOOK URL
# =========================

PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# example → https://your-app-name.onrender.com

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL not set in Render environment variables")

# =========================
# INSTALOADER SETUP
# =========================

DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

loader = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR, save_metadata=False, download_comments=False
)

# =========================
# START COMMAND
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n" "Send Instagram Reel/Post link to download."
    )


# =========================
# HELP COMMAND
# =========================


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Send Instagram Reel/Post link.\n" "Bot downloads media automatically."
    )


# =========================
# DOWNLOAD FUNCTION
# =========================


async def download_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        return

    message = await update.message.reply_text("Downloading... ⏳")

    try:
        url = url.split("?")[0].rstrip("/")
        shortcode = url.split("/")[-1]

        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # clear old files
        for f in os.listdir(DOWNLOAD_DIR):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except:
                pass

        loader.download_post(post, target=DOWNLOAD_DIR)

        sent = False

        for root, dirs, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                path = os.path.join(root, file)

                if file.endswith(".mp4"):
                    with open(path, "rb") as video:
                        await update.message.reply_video(video=video)
                    sent = True

                elif file.endswith((".jpg", ".jpeg", ".png")):
                    with open(path, "rb") as photo:
                        await update.message.reply_photo(photo=photo)
                    sent = True

                os.remove(path)

        if not sent:
            await update.message.reply_text("⚠️ Media not found")

    except Exception as e:
        print("Download error:", e)
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


# =========================
# TELEGRAM MENU BUTTON
# =========================


async def set_commands(app):
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start bot"),
            BotCommand("help", "Help guide"),
        ]
    )
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


# =========================
# POST INIT
# =========================


async def post_init(app):
    asyncio.create_task(auto_restart())
    await set_commands(app)


# =========================
# ERROR HANDLER
# =========================


async def error_handler(update, context):
    print("Error:", context.error)


# =========================
# BOT SETUP
# =========================

app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))
app.add_error_handler(error_handler)

print("✅ Telegram bot running on Render Web Service...")

# =========================
# RUN WEBHOOK (RENDER FIX)
# =========================

app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
