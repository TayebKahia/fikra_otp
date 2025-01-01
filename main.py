from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import pyotp
import os
import time
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_KEY_PAIRS = os.getenv("SECRET_KEY_PAIRS", "")

# Parse secret keys
SECRET_KEYS = {
    pair.split(":")[0]: pair.split(":")[1]
    for pair in SECRET_KEY_PAIRS.split(",")
    if ":" in pair
}

# Define conversation states
EMAIL = range(1)


# Function to generate OTP and time remaining
def generate_otp_with_time(secret_key):
    totp = pyotp.TOTP(secret_key)
    otp = totp.now()
    time_remaining = totp.interval - (int(time.time()) % totp.interval)
    return otp, time_remaining


# Validate email format and domain
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@(gmail\.com|outlook\.com)$"
    return re.match(pattern, email)


# Start the /getotp process
async def getotp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "يرجى إدخال بريدك الإلكتروني (Gmail أو Outlook) للحصول على كلمة المرور لمرة واحدة. "
        "يمكنك كتابة /cancel لإلغاء العملية."
    )
    return EMAIL


# Process the email input
async def process_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    print(f"Received email: {email}")  # Debugging

    # Validate email
    if not is_valid_email(email):
        await update.message.reply_text(
            "يرجى إدخال بريد إلكتروني صحيح من Gmail أو Outlook."
        )
        return EMAIL

    # Find the secret key
    secret_key = SECRET_KEYS.get(email)
    if not secret_key:
        await update.message.reply_text(
            "هذا البريد الإلكتروني غير مسجل. يرجى التحقق والمحاولة مرة أخرى."
        )
        return EMAIL

    # Generate OTP
    otp, time_remaining = generate_otp_with_time(secret_key)
    if time_remaining < 5:
        await update.message.reply_text(
            f"تحذير: كلمة المرور الحالية ستنتهي صلاحيتها خلال {time_remaining} ثانية.\n"
            "يرجى الانتظار حتى يتم توليد كلمة مرور جديدة والمحاولة مرة أخرى."
        )
    else:
        await update.message.reply_text(
            f"كلمة المرور الحالية الخاصة بك هي: {otp}\n"
            f"الوقت المتبقي لانتهاء صلاحية كلمة المرور: {time_remaining} ثانية"
        )

    return EMAIL  # Keep the conversation active


# Cancel the process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية. شكراً لاستخدامك البوت!")
    return ConversationHandler.END


# Main function
def main():
    # Ensure bot token is configured
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set in the environment variables!")
        return

    # Initialize bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for /getotp
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("getotp", getotp_start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(
        CommandHandler(
            "start",
            lambda update, context: update.message.reply_text(
                "مرحبًا بك في بوت OTP! استخدم /getotp للحصول على كلمة المرور لمرة واحدة."
            ),
        )
    )
    application.add_handler(conversation_handler)

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
