import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import yt_dlp

# ------------------ Config ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
DOWNLOAD_DIR = "/tmp"
WEBHOOK_URL = f"https://your-render-url-here.onrender.com/{BOT_TOKEN}"

# Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------ Flask ------------------
flask_app = Flask(__name__)

# ------------------ Telegram Bot ------------------
app = Application.builder().token(BOT_TOKEN).build()

# ------------------ Helper Function ------------------
# (Your download_media function remains unchanged)
def download_media(url: str, mode: str) -> str:
    """
    Download media using yt_dlp based on mode.
    Returns the file path.
    """
    ydl_opts = {"outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s"}

    if mode == "mp3_320":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
        })
    elif mode == "m4a":
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio"
    elif mode == "bestaudio":
        ydl_opts["format"] = "bestaudio"
    elif mode == "mp4":
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"
    elif mode == "4k":
        ydl_opts["format"] = "bestvideo[height<=2160]+bestaudio/best"
    else:
        raise ValueError("Invalid mode provided")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


# ------------------ Handlers ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    msg = (
        "🎵 *Audio Options:*\n"
        " - /download <url> mp3_320 → MP3 320kbps\n"
        " - /download <url> m4a → M4A\n"
        " - /download <url> bestaudio → Best available audio\n\n"
        "🎬 *Video Options:*\n"
        " - /download <url> mp4 → MP4 (best)\n"
        " - /download <url> 4k → Up to 4K\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download requested media"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /download <url> <mode>")
        return

    url, mode = context.args[0], context.args[1]
    await update.message.reply_text(f"⬇️ Downloading in `{mode}`...", parse_mode="Markdown")

    try:
        # download_media is a synchronous function, so we run it in a thread pool executor.
        file_path = await asyncio.to_thread(download_media, url, mode)

        file_size = os.path.getsize(file_path)
        if file_size > 49 * 1024 * 1024:
            await update.message.reply_text("⚠️ File too large for Telegram upload.")
            os.remove(file_path) # Clean up the file
            return

        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f)

        os.remove(file_path) # Clean up the file after sending
    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("download", download))


# ------------------ Flask Endpoints ------------------
@flask_app.get("/")
def home():
    return "Bot is running!", 200

# This is the endpoint that receives updates from Telegram
@flask_app.post(f"/{BOT_TOKEN}")
async def webhook():
    await app.update_queue.put(Update.de_json(request.json, app.bot))
    return "ok", 200


# ------------------ Main ------------------
if __name__ == "__main__":
    logger.info("Starting Flask server...")
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )
