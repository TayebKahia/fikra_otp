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


# Function to fetch OTP from email
def fetch_email_otp(email_address, app_password, secret_word):
    try:
        if "gmail.com" in email_address:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
        elif "outlook.com" in email_address:
            mail = imaplib.IMAP4_SSL("outlook.office365.com")
        else:
            return "هذا البريد الإلكتروني غير مدعوم."

        mail.login(email_address, app_password)
        print("[DEBUG] Logged into email successfully.")

        # Select the inbox
        mail.select("inbox")

        # Search for all messages (replace "ALL" with "UNSEEN" for unread emails only)
        status, messages = mail.search(None, "ALL")

        if status != "OK" or not messages[0]:
            return "لم يتم العثور على رسائل جديدة."

        # Get all message IDs in reverse order (most recent first)
        message_ids = messages[0].split()[::-1]

        # Flag to track if any email was processed successfully
        found_valid_email = False

        # Process each email
        for msg_id in message_ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Get the email content
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                print(f"[DEBUG] Plain Text Body: ")
                                break
                            elif content_type == "text/html":
                                html_body = part.get_payload(decode=True).decode()
                                body = re.sub("<[^<]+?>", "", html_body)
                                print(f"[DEBUG] HTML Body (Stripped): ")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # Check for the secret word and 6-digit OTP
                    if secret_word.lower() in body.lower():
                        print(f"[DEBUG] Secret word '{secret_word}' found in body.")
                        otp_match = re.search(r"\b\d{6}\b", body)
                        if otp_match:
                            print(f"[DEBUG] Found OTP: {otp_match.group()}")
                            mail.logout()
                            return otp_match.group()
                    else:
                        print("[DEBUG] Secret word not found in this email.")

        mail.logout()

        # Return appropriate message if no valid OTP was found
        if not found_valid_email:
            return "لم يتم العثور على رسائل تحتوي على الكلمة السرية وكود التحقق."
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {str(e)}")
        return f"خطأ أثناء الوصول إلى البريد الإلكتروني: {str(e)}"


# Function to generate OTP and time remaining
def generate_otp_with_time(secret_key):
    totp = pyotp.TOTP(secret_key)
    otp = totp.now()
    time_remaining = totp.interval - (int(time.time()) % totp.interval)
    return otp, time_remaining


# Command: /getemailotp
async def getemailotp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "يرجى إدخال بريدك الإلكتروني للحصول على رمز التحقق من البريد الإلكتروني. يمكنك كتابة /cancel لإلغاء العملية."
    )
    return EMAIL_OTP


# Process email for /getemailotp
async def process_email_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_address = update.message.text.strip()
    if not is_valid_email(email_address):
        await update.message.reply_text(
            "يرجى إدخال بريد إلكتروني صحيح من Gmail أو Outlook."
        )
        return EMAIL_OTP

    # Get app password for the email
    app_password = EMAIL_ACCOUNTS.get(email_address)
    if not app_password:
        await update.message.reply_text(
            "هذا البريد الإلكتروني غير مسجل. يرجى التحقق والمحاولة مرة أخرى."
        )
        return EMAIL_OTP

    # Fetch OTP from email
    secret_word = SECRET_WORD  # Define your secret word
    otp = fetch_email_otp(email_address, app_password, secret_word)
    if otp.startswith("لم يتم العثور"):
        await update.message.reply_text(otp)
    else:
        await update.message.reply_text(f"رمز التحقق من البريد الإلكتروني هو: {otp}")

    return EMAIL_OTP


# Command: /getotp
async def getotp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "يرجى إدخال بريدك الإلكتروني للحصول على كلمة المرور لمرة واحدة. يمكنك كتابة /cancel لإلغاء العملية."
    )
    return AUTH_OTP


# Process email for /getotp
async def process_email_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_address = update.message.text.strip()
    if not is_valid_email(email_address):
        await update.message.reply_text(
            "يرجى إدخال بريد إلكتروني صحيح من Gmail أو Outlook."
        )
        return AUTH_OTP

    # Get secret key for the email
    secret_key = SECRET_KEYS.get(email_address)
    if not secret_key:
        await update.message.reply_text(
            "هذا البريد الإلكتروني غير مسجل. يرجى التحقق والمحاولة مرة أخرى."
        )
        return AUTH_OTP

    # Generate OTP
    otp, time_remaining = generate_otp_with_time(secret_key)

    # Notify user if time remaining is less than 5 seconds
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

    return AUTH_OTP


# Command: /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية. شكراً لاستخدامك البوت!")
    return ConversationHandler.END


# Main function
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

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
