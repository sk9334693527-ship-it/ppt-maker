from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    name = user.first_name
    username = user.username
    user_id = user.id

    message = f"""
👋 Hello {name}!

🆔 Your Telegram Info:
• Name: {name}
• Username: @{username}
• ID: {user_id}
"""

    await update.message.reply_text(message)

# main function
async def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
