from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from subtitle_utils import burn_subtitles_with_font_and_size  # Import from subtitle_utils
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORK_DIR = "/content"
FONT_FILE = f"{WORK_DIR}/font.ttf"
OUTPUT_VIDEO = f"{WORK_DIR}/output.mp4"

def get_bot_token():
    try:
        with open("config.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError("Bot token file 'config.txt' not found.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video file (.mp4) and a subtitle file (.srt) to burn subtitles.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "video_path" in context.user_data:
        await update.message.reply_text("Video already uploaded. Now send the subtitle file.")
        return

    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        local_filename = f"{WORK_DIR}/{update.message.document.file_id}.mp4"
        await file.download_to_drive(local_filename)

        context.user_data["video_path"] = local_filename
        await update.message.reply_text("Video uploaded! Now send the subtitle file (.srt).")
    else:
        await update.message.reply_text("Please send a valid .mp4 video file.")

async def handle_subtitles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "subtitle_path" in context.user_data:
        await update.message.reply_text("Subtitle already uploaded. Now send the video file.")
        return

    if update.message.document and update.message.document.file_name.endswith(".srt"):
        file = await context.bot.get_file(update.message.document.file_id)
        subtitle_path = os.path.join(WORK_DIR, "subtitles.srt")
        await file.download_to_drive(subtitle_path)

        context.user_data["subtitle_path"] = subtitle_path
        await update.message.reply_text("Subtitle uploaded! Now send the video file (.mp4).")
        await process_video(update, context)
    else:
        await update.message.reply_text("Please send a valid .srt subtitle file.")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_path = context.user_data.get("video_path")
    subtitle_path = context.user_data.get("subtitle_path")

    if not video_path or not subtitle_path:
        await update.message.reply_text("Please send both the video (.mp4) and subtitle (.srt) files.")
        return

    try:
        burn_subtitles_with_font_and_size(
            input_video=video_path,
            subtitle_file=subtitle_path,
            output_video=OUTPUT_VIDEO,
            font_path=FONT_FILE,
            font_size=24,
            alignment=2,
            margin_vertical=35,
        )

        await update.message.reply_text("Encoding complete! Sending the video...")
        with open(OUTPUT_VIDEO, "rb") as video:
            await update.message.reply_video(video)

        # Cleanup
        os.remove(video_path)
        os.remove(subtitle_path)
        os.remove(OUTPUT_VIDEO)
    except Exception as e:
        logger.error(f"Error while processing video: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

def main():
    TOKEN = get_bot_token()  # Fetch token from config file

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("mp4"), handle_video))
    app.add_handler(MessageHandler(filters.Document.FileExtension("srt"), handle_subtitles))

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
