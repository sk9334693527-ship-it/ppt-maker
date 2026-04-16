import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

users = {}
admin_state = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in users:
        users[user_id] = {"credit": 0, "expiry": 0}

    credit = users[user_id]["credit"]
    expiry = users[user_id]["expiry"]

    remaining_days = 0
    if expiry > time.time():
        remaining_days = int((expiry - time.time()) / 86400)

    await update.message.reply_text(
        f"👋 Hello {user.first_name}\n\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Credit: {credit}\n"
        f"⏳ Days Left: {remaining_days}"
    )

# /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    admin_state[user_id] = "password"
    await update.message.reply_text("🔐 Enter Admin Password:")

# /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if admin_state.get(user_id) != "logged_in":
        await update.message.reply_text("❌ Login first using /admin")
        return

    admin_state[user_id] = "ask_user"
    await update.message.reply_text("Enter User ID:")

# handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # password check
    if admin_state.get(user_id) == "password":
        if text == ADMIN_PASSWORD:
            admin_state[user_id] = "logged_in"
            await update.message.reply_text("✅ Welcome Admin")
        else:
            await update.message.reply_text("❌ Wrong Password")

    # ask user id
    elif admin_state.get(user_id) == "ask_user":
        admin_state[user_id] = {"step": "choose_type", "target": int(text)}
        await update.message.reply_text("Type 'credit' or 'day'")

    # choose type
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "choose_type":
        if text.lower() == "credit":
            admin_state[user_id]["step"] = "add_credit"
            await update.message.reply_text("Enter credit amount:")
        elif text.lower() == "day":
            admin_state[user_id]["step"] = "add_day"
            await update.message.reply_text("Enter days:")
        else:
            await update.message.reply_text("Type 'credit' or 'day'")

    # add credit
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "add_credit":
        amount = int(text)
        target = admin_state[user_id]["target"]

        if target not in users:
            users[target] = {"credit": 0, "expiry": 0}

        users[target]["credit"] += amount
        admin_state[user_id] = "logged_in"

        await update.message.reply_text(f"✅ {amount} credit added to {target}")

    # add day
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "add_day":
        days = int(text)
        target = admin_state[user_id]["target"]

        if target not in users:
            users[target] = {"credit": 0, "expiry": 0}

        users[target]["expiry"] = time.time() + (days * 86400)
        admin_state[user_id] = "logged_in"

        await update.message.reply_text(f"✅ {days} days added to {target}")

# app
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling()
