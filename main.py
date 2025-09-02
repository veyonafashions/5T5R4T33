import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- yt-dlp format presets ---
FORMATS = {
    "mp3": {"format": "bestaudio", "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "320",
    }]},
    "m4a": {"format": "bestaudio[ext=m4a]/bestaudio"},
    "360p": {"format": "bestvideo[height<=360]+bestaudio/best[height<=360]"},
    "720p": {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]"},
    "1080p": {"format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"},
    "4k": {"format": "bestvideo[height<=2160]+bestaudio/best[height<=2160]"},
}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video URL, and I’ll let you pick format/quality.")

async def ask_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ Please send a valid video URL.")
        return

    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎵 MP3 (320kbps)", callback_data="mp3"),
         InlineKeyboardButton("🎵 M4A", callback_data="m4a")],
        [InlineKeyboardButton("📹 360p", callback_data="360p"),
         InlineKeyboardButton("📹 720p", callback_data="720p")],
        [InlineKeyboardButton("📹 1080p", callback_data="1080p"),
         InlineKeyboardButton("📹 4K", callback_data="4k")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🔽 Choose format:", reply_markup=reply_markup)

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    fmt = query.data
    url = context.user_data.get("url")

    await query.edit_message_text(f"📥 Downloading {fmt.upper()}... please wait.")

    loop = asyncio.get_event_loop()
    try:
        def run_dl():
            opts = {
                "outtmpl": "%(title)s.%(ext)s",
                "merge_output_format": "mp4",
                "quiet": True,
                "ffmpeg_location": "/usr/bin/ffmpeg"
            }
            opts.update(FORMATS[fmt])
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await loop.run_in_executor(None, run_dl)

        if fmt in ["mp3", "m4a"]:
            await query.message.reply_audio(audio=open(filename, "rb"))
        else:
            await query.message.reply_video(video=open(filename, "rb"))

        os.remove(filename)

    except Exception as e:
        await query.message.reply_text(f"⚠️ Error: {e}")

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_format))
    app.add_handler(CallbackQueryHandler(download))
    app.run_polling()

if __name__ == "__main__":
    main()
