import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from subtitle_utils import burn_subtitles_with_font_and_size  # Import your subtitle-burning function
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Constants
WORK_DIR = "/content"
FONT_FILE = f"{WORK_DIR}/font.ttf"
OUTPUT_VIDEO = f"{WORK_DIR}/output.mp4"

# Setup Google Drive
def setup_google_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Opens browser for authentication
    return GoogleDrive(gauth)

# Upload File to Google Drive
def upload_to_google_drive(file_path, drive):
    file_name = os.path.basename(file_path)
    gfile = drive.CreateFile({'title': file_name})  # Create Google Drive file
    gfile.SetContentFile(file_path)
    gfile.Upload()

    # Make file sharable
    gfile.InsertPermission({
        'type': 'anyone',
        'value': 'anyone',
        'role': 'reader'
    })

    return gfile['alternateLink']

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a video file (.mp4) and a subtitle file (.srt) to burn subtitles.\n"
        "Note: Videos must be less than 2GB."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if "video_path" in context.user_data:
            await update.message.reply_text("Video already uploaded. Now send the subtitle file.")
            return

        if update.message.document and update.message.document.file_name.endswith(".mp4"):
            file = await context.bot.get_file(update.message.document.file_id)
            video_path = os.path.join(WORK_DIR, "input_video.mp4")
            await file.download_to_drive(video_path)

            context.user_data["video_path"] = video_path
            await update.message.reply_text("Video uploaded! Now send the subtitle file (.srt).")
        else:
            await update.message.reply_text("Please send a valid .mp4 video file.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

async def handle_subtitles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if "subtitle_path" in context.user_data:
            await update.message.reply_text("Subtitle already uploaded. Now send the video file.")
            return

        if update.message.document and update.message.document.file_name.endswith(".srt"):
            file = await context.bot.get_file(update.message.document.file_id)
            subtitle_path = os.path.join(WORK_DIR, "subtitles.srt")
            await file.download_to_drive(subtitle_path)
            context.user_data["subtitle_path"] = subtitle_path

            await update.message.reply_text("Subtitle uploaded! Starting video processing...")
            await process_video(update, context)
        else:
            await update.message.reply_text("Please send a valid .srt subtitle file.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_file_id = context.user_data.get("video_file_id")
    subtitle_path = context.user_data.get("subtitle_path")

    if not video_file_id or not subtitle_path:
        await update.message.reply_text("Please send both the video (.mp4) and subtitle (.srt) files.")
        return

    try:
        # Step 1: Download the video
        await update.message.reply_text("Downloading the video...")
        video_file = await context.bot.get_file(video_file_id)
        video_path = os.path.join(WORK_DIR, "input_video.mp4")
        await video_file.download_to_drive(video_path)

        # Step 2: Encode the video
        await update.message.reply_text("Encoding the video with subtitles. This may take some time...")
        burn_subtitles_with_font_and_size(
            input_video=video_path,
            subtitle_file=subtitle_path,
            output_video=OUTPUT_VIDEO,
            font_path=FONT_FILE,
            font_size=24,
            alignment=2,
            margin_vertical=35,
        )

        # Step 3: Upload to Google Drive
        await update.message.reply_text("Uploading the encoded video to Google Drive...")
        drive = setup_google_drive()
        gdrive_link = upload_to_google_drive(OUTPUT_VIDEO, drive)

        # Step 4: Send the download link
        await update.message.reply_text(
            f"Encoding complete! You can download your video here: {gdrive_link}"
        )

        # Cleanup temporary files
        os.remove(video_path)
        os.remove(subtitle_path)
        os.remove(OUTPUT_VIDEO)

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Main
def main():
    # Your Telegram bot token
    TOKEN = "7418323436:AAFHmUzK4S6mg6Eq038hhGm1KifJnw6TMwE"  # Replace with your bot's token

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.FileExtension("srt"), handle_subtitles))

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
