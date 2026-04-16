import os
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ===== ENV VARIABLES =====
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
WEB_URL = os.getenv("WEB_URL")  # Google Apps Script URL

admin_state = {}

# ===== SAVE FUNCTION =====
def save_user(user_id, name, credit, expiry):
    data = {
        "user_id": str(user_id),
        "name": name,
        "credit": credit,
        "expiry": expiry
    }

    try:
        requests.post(WEB_URL, json=data)
    except:
        pass

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(user.id, user.first_name, 0, 0)

    await update.message.reply_text(
        f"👋 Hello {user.first_name}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Credit: 0\n"
        f"⏳ Days: 0"
    )

# ===== /admin =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    admin_state[user_id] = "password"
    await update.message.reply_text("🔐 Enter Admin Password:")

# ===== /add =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if admin_state.get(user_id) != "logged_in":
        await update.message.reply_text("❌ Login first using /admin")
        return

    admin_state[user_id] = "ask_user"
    await update.message.reply_text("Enter User ID:")

# ===== MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # LOGIN PASSWORD
    if admin_state.get(user_id) == "password":
        if text == ADMIN_PASSWORD:
            admin_state[user_id] = "logged_in"
            await update.message.reply_text("✅ Welcome Admin")
        else:
            await update.message.reply_text("❌ Wrong Password")

    # ASK USER ID
    elif admin_state.get(user_id) == "ask_user":
        admin_state[user_id] = {"step": "choose", "target": text}
        await update.message.reply_text("Type: credit or day")

    # CHOOSE TYPE
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "choose":
        if text.lower() == "credit":
            admin_state[user_id]["step"] = "credit_add"
            await update.message.reply_text("Enter credit amount:")

        elif text.lower() == "day":
            admin_state[user_id]["step"] = "day_add"
            await update.message.reply_text("Enter days:")

    # ADD CREDIT
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "credit_add":
        amount = int(text)
        target = admin_state[user_id]["target"]

        save_user(target, "User", amount, 0)

        admin_state[user_id] = "logged_in"
        await update.message.reply_text(f"✅ {amount} credit added")

    # ADD DAYS
    elif isinstance(admin_state.get(user_id), dict) and admin_state[user_id]["step"] == "day_add":
        days = int(text)
        target = admin_state[user_id]["target"]

        expiry = int(time.time()) + (days * 86400)

        save_user(target, "User", 0, expiry)

        admin_state[user_id] = "logged_in"
        await update.message.reply_text(f"✅ {days} days added")

# ===== APP START =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling()
