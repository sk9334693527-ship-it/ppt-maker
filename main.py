import os
import json
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

DATA_FILE = "data.json"

admin_state = {}

# ===== LOAD DATA =====
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# ===== SAVE DATA =====
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()

    if str(user.id) not in data:
        data[str(user.id)] = {
            "name": user.first_name,
            "credit": 0,
            "expiry": 0
        }
        save_data(data)

    u = data[str(user.id)]

    await update.message.reply_text(
        f"👋 Hello {u['name']}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Credit: {u['credit']}\n"
        f"⏳ Days Left: {int((u['expiry'] - time.time())/86400) if u['expiry'] else 0}"
    )

# ===== /admin =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    admin_state[update.effective_user.id] = "password"
    await update.message.reply_text("🔐 Enter password:")

# ===== /add =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if admin_state.get(update.effective_user.id) != "logged":
        await update.message.reply_text("Login first /admin")
        return

    admin_state[update.effective_user.id] = "ask_user"
    await update.message.reply_text("Enter user ID:")

# ===== MESSAGE HANDLER =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    data = load_data()

    # LOGIN
    if admin_state.get(uid) == "password":
        if text == ADMIN_PASSWORD:
            admin_state[uid] = "logged"
            await update.message.reply_text("✅ Admin logged in")
        else:
            await update.message.reply_text("❌ Wrong password")

    # ASK USER
    elif admin_state.get(uid) == "ask_user":
        admin_state[uid] = {"step": "choose", "target": text}
        await update.message.reply_text("Type: credit or day")

    # CHOOSE TYPE
    elif isinstance(admin_state.get(uid), dict):

        state = admin_state[uid]

        if state["step"] == "choose":
            if text == "credit":
                state["step"] = "credit_add"
                await update.message.reply_text("Enter credit amount")

            elif text == "day":
                state["step"] = "day_add"
                await update.message.reply_text("Enter days")

        elif state["step"] == "credit_add":
            target = state["target"]
            data[target]["credit"] += int(text)
            save_data(data)

            admin_state[uid] = "logged"
            await update.message.reply_text("✅ Credit added")

        elif state["step"] == "day_add":
            target = state["target"]
            data[target]["expiry"] = time.time() + (int(text)*86400)
            save_data(data)

            admin_state[uid] = "logged"
            await update.message.reply_text("✅ Days added")

# ===== APP =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
