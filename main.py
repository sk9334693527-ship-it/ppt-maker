import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# token from Railway ENV
TOKEN = os.getenv("BOT_TOKEN")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    name = user.first_name
    username = user.username if user.username else "No Username"
    user_id = user.id

    message = f"""
👋 Hello {name}!

🆔 Your Telegram Info:
• Name: {name}
• Username: @{username}
• ID: {user_id}
"""

    await update.message.reply_text(message)

# app setup
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Bot running...")
app.run_polling()
