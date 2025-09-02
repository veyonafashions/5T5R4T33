import os
from telegram.ext import Application, CommandHandler
from telegram import Update
from flask import Flask, request
import threading
import yt_dlp
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

# Flask app for webhook endpoint
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running with polling!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)


# Telegram bot app
app = Application.builder().token(BOT_TOKEN).build()

# ---------- Helper function ----------
def download_media(url, mode):
    """
    mode options:
      mp3_320  -> MP3 320kbps
      m4a      -> Best M4A audio
      bestaudio-> Best audio available
      mp4      -> Best MP4 video
      4k       -> Best video up to 4K
    """
    ydl_opts = {"outtmpl": "/tmp/%(title)s.%(ext)s"}

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
        ydl_opts.update({"format": "bestaudio[ext=m4a]/bestaudio"})
    elif mode == "bestaudio":
        ydl_opts.update({"format": "bestaudio"})
    elif mode == "mp4":
        ydl_opts.update({"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"})
    elif mode == "4k":
        ydl_opts.update({"format": "bestvideo[height<=2160]+bestaudio/best"})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ---------- Handlers ----------
async def start(update: Update, context):
    msg = (
        "🎵 *Audio Options:*\n"
        " - /download <url> mp3_320 → MP3 320kbps\n"
        " - /download <url> m4a → M4A\n"
        " - /download <url> bestaudio → Best available audio\n\n"
        "🎬 *Video Options:*\n"
        " - /download <url> mp4 → MP4 (best)\n"
        " - /download <url> 4k → Up to 4K\n"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def download(update: Update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /download <url> <mode>")
        return

    url, mode = context.args[0], context.args[1]
    await update.message.reply_text(f"⬇️ Downloading in {mode}...")

    loop = asyncio.get_event_loop()
    try:
        file_path = await loop.run_in_executor(None, download_media, url, mode)
        await update.message.reply_document(document=open(file_path, "rb"))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Register handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("download", download))

# ---------- Webhook ----------
@flask_app.post(f"/{BOT_TOKEN}")
def webhook():
    data = request.get_json(force=True)
    app.update_queue.put_nowait(data)
    return "ok"

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    import asyncio
    async def run():
        await app.initialize()
        await app.start()
        print("Bot is running with polling...")
        await app.updater.start_polling()
        await app.updater.idle()

    asyncio.run(run())
