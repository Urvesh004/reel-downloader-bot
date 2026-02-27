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
    while True:
        await asyncio.sleep(600)
        print("♻️ Restarting bot...")
        os.execv(sys.executable, [sys.executable] + sys.argv)


# =========================
# ENV SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not set")

PORT = int(os.environ.get("PORT", 10000))

# ✅ Auto detect Render URL
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL not set")

# =========================
# INSTALOADER
# =========================
loader = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    save_metadata=False,
    download_comments=False,
)

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nSend Instagram Reel/Post link to download."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Send Instagram Reel/Post link.\nBot downloads media automatically."
    )


# =========================
# SHORTCODE EXTRACT
# =========================
def extract_shortcode(url: str):
    url = url.split("?")[0].rstrip("/")
    parts = url.split("/")
    for part in parts:
        if part not in ["https:", "", "www.instagram.com", "instagram.com", "reel", "p", "tv"]:
            return part
    return None


# =========================
# DOWNLOAD FUNCTION
# =========================
async def download_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        return

    message = await update.message.reply_text("Downloading... ⏳")

    try:
        shortcode = extract_shortcode(url)
        if not shortcode:
            await update.message.reply_text("❌ Invalid Instagram link")
            return

        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Clear old files
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

                elif file.lower().endswith((".jpg", ".jpeg", ".png")):
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

        # DO NOT REMOVE (as requested)
        for f in os.listdir("downloads"):
            try:
                os.remove(os.path.join("downloads", f))
            except:
                pass


# =========================
# MENU + INIT
# =========================
async def set_commands(app):
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start bot"),
            BotCommand("help", "Help guide"),
        ]
    )
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def post_init(app):
    asyncio.create_task(auto_restart())
    await set_commands(app)


async def error_handler(update, context):
    print("Error:", context.error)


# =========================
# APP SETUP
# =========================
app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))
app.add_error_handler(error_handler)

print("✅ Telegram bot running on Render Web Service...")

# =========================
# RUN WEBHOOK (v22 FIX)
# =========================
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path="webhook",
    webhook_url=f"{WEBHOOK_URL}/webhook",
)