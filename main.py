from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import os
import re
import imaplib
import email
from dotenv import load_dotenv
import pyotp
import time

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_KEY_PAIRS = os.getenv("SECRET_KEY_PAIRS", "")
EMAIL_CREDENTIALS = os.getenv("EMAIL_CREDENTIALS", "")
SECRET_WORD = os.getenv("SECRET_WORD")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your Render-provided public URL

# Parse secret keys and email credentials
SECRET_KEYS = {
    pair.split(":")[0]: pair.split(":")[1]
    for pair in SECRET_KEY_PAIRS.split(",")
    if ":" in pair
}
EMAIL_ACCOUNTS = {
    pair.split(":")[0]: pair.split(":")[1]
    for pair in EMAIL_CREDENTIALS.split(",")
    if ":" in pair
}

# Define conversation states
EMAIL_OTP = range(1)
AUTH_OTP = range(1)

# Validate email format and domain
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@(gmail\.com|outlook\.com)$"
    return re.match(pattern, email)

# Other functions (fetch_email_otp, generate_otp_with_time, etc.) remain unchanged...

# Main function for webhook
def main():
    # Initialize bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers for /getemailotp
    email_otp_handler = ConversationHandler(
        entry_points=[CommandHandler("getemailotp", getemailotp_start)],
        states={
            EMAIL_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_otp)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Handlers for /getotp
    auth_otp_handler = ConversationHandler(
        entry_points=[CommandHandler("getotp", getotp_start)],
        states={
            AUTH_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_auth)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(
        CommandHandler(
            "start",
            lambda update, context: update.message.reply_text(
                "مرحبًا بك في البوت! استخدم /getemailotp للحصول على رمز التحقق من البريد الإلكتروني، أو /getotp للحصول على كلمة المرور لمرة واحدة."
            ),
        )
    )
    application.add_handler(email_otp_handler)
    application.add_handler(auth_otp_handler)

    # Webhook setup
    PORT = int(os.environ.get("PORT", 8443))  # Default port is 8443 if not provided
    application.run_webhook(
        listen="0.0.0.0",  # Listen on all network interfaces
        port=PORT,  # Port specified by Render
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",  # Render-provided URL
    )

if __name__ == "__main__":
    main()
