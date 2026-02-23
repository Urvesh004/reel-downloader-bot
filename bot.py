import os
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
# LOAD ENV FILE SAFELY (PythonAnywhere fix)
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
    raise ValueError(
        "❌ BOT_TOKEN not set!\n"
        "Create .env file in project folder:\n"
        "BOT_TOKEN=your_token_here"
    )

# =========================
# INSTALOADER SETUP
# =========================

loader = instaloader.Instaloader(
    dirname_pattern="downloads",
    save_metadata=False,
    download_comments=False
)

DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Send Instagram Reel/Post link to download.\n\n"
        "Use /help for guidance."
    )

# =========================
# HELP COMMAND
# =========================

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 How to use:\n\n"
        "1️⃣ Send /start\n"
        "2️⃣ Paste Instagram Reel/Post link\n"
        "3️⃣ Bot downloads media\n\n"
        "Supported:\n"
        "✅ Reels\n"
        "✅ Posts"
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

        for file in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, file)

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
    await app.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("help", "Help guide"),
    ])
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

# =========================
# BOT SETUP
# =========================

app = ApplicationBuilder().token(TOKEN).post_init(set_commands).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram))

print("✅ Telegram bot running 24/7...")

app.run_polling()