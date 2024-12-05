import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from subtitle_utils import burn_subtitles_with_font_and_size  # Import your subtitle-burning function
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Constants
WORK_DIR = "/content"
FONT_FILE = f"{WORK_DIR}/font.ttf"
OUTPUT_VIDEO = f"{WORK_DIR}/output.mp4"

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Change to DEBUG for more verbose output
)
logger = logging.getLogger(__name__)

# Setup Google Drive
def setup_google_drive():
    logger.info("Setting up Google Drive authentication...")
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Opens browser for authentication
    return GoogleDrive(gauth)

# Upload File to Google Drive
def upload_to_google_drive(file_path, drive):
    try:
        file_name = os.path.basename(file_path)
        logger.info(f"Uploading file '{file_name}' to Google Drive...")
        gfile = drive.CreateFile({'title': file_name})  # Create Google Drive file
        gfile.SetContentFile(file_path)
        gfile.Upload()

        # Make file sharable
        gfile.InsertPermission({
            'type': 'anyone',
            'value': 'anyone',
            'role': 'reader'
        })

        link = gfile['alternateLink']
        logger.info(f"File uploaded successfully. Public link: {link}")
        return link
    except Exception as e:
        logger.error(f"Failed to upload file to Google Drive: {e}")
        raise RuntimeError(f"Failed to upload file to Google Drive: {e}")

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot.")
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
            
            logger.info(f"Downloading video file: {update.message.document.file_name}")
            await update.message.reply_text("Downloading video... This may take some time.")
            await file.download_to_drive(video_path)

            context.user_data["video_path"] = video_path
            logger.info(f"Video downloaded successfully: {video_path}")
            await update.message.reply_text("Video uploaded successfully! Now send the subtitle file (.srt).")
        else:
            logger.warning("User attempted to send an invalid video file.")
            await update.message.reply_text("Please send a valid .mp4 video file as a document.")
    except Exception as e:
        logger.error(f"Error while handling video: {e}")
        await update.message.reply_text(f"An error occurred while handling the video: {e}")

async def handle_subtitles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if "subtitle_path" in context.user_data:
            await update.message.reply_text("Subtitle already uploaded. Now send the video file.")
            return

        if update.message.document and update.message.document.file_name.endswith(".srt"):
            file = await context.bot.get_file(update.message.document.file_id)
            subtitle_path = os.path.join(WORK_DIR, "subtitles.srt")
            
            logger.info(f"Downloading subtitle file: {update.message.document.file_name}")
            await file.download_to_drive(subtitle_path)
            context.user_data["subtitle_path"] = subtitle_path

            logger.info(f"Subtitle downloaded successfully: {subtitle_path}")
            await update.message.reply_text("Subtitle uploaded! Starting video processing...")
            await process_video(update, context)
        else:
            logger.warning("User attempted to send an invalid subtitle file.")
            await update.message.reply_text("Please send a valid .srt subtitle file.")
    except Exception as e:
        logger.error(f"Error while handling subtitles: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_path = context.user_data.get("video_path")
    subtitle_path = context.user_data.get("subtitle_path")

    if not video_path or not subtitle_path:
        await update.message.reply_text("Please send both the video (.mp4) and subtitle (.srt) files.")
        return

    try:
        logger.info(f"Starting video encoding for {video_path} with subtitles {subtitle_path}...")
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

        logger.info(f"Video encoding complete. Uploading result to Google Drive...")
        drive = setup_google_drive()
        gdrive_link = upload_to_google_drive(OUTPUT_VIDEO, drive)

        logger.info(f"Process complete. Sharing download link with user.")
        await update.message.reply_text(
            f"Encoding complete! You can download your video here: {gdrive_link}"
        )

        # Cleanup
        os.remove(video_path)
        os.remove(subtitle_path)
        os.remove(OUTPUT_VIDEO)
        logger.info(f"Temporary files cleaned up.")
    except Exception as e:
        logger.error(f"Error while processing video: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

# Main
def main():
    TOKEN = "7418323436:AAFHmUzK4S6mg6Eq038hhGm1KifJnw6TMwE"  # Replace with your bot's token
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("mp4"), handle_video))
    app.add_handler(MessageHandler(filters.Document.FileExtension("srt"), handle_subtitles))

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
