import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "data.json"

# ---------------- DATA FUNCTIONS ----------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def ensure_user(user):
    uid = str(user.id)

    if uid not in data:
        data[uid] = {
            "name": user.full_name,
            "credit": 0
        }
        save_data(data)

# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)

    await update.message.reply_text(
        f"👋 Welcome {user.full_name}\nUse /balance to check credit"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)

    uid = str(user.id)
    credit = data[uid]["credit"]

    await update.message.reply_text(
        f"👤 Name: {data[uid]['name']}\n💰 Credit: {credit}"
    )

# ADMIN ADD CREDIT
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # format: /add user_id amount
    try:
        user_id = context.args[0]
        amount = int(context.args[1])

        if user_id not in data:
            data[user_id] = {"name": "Unknown", "credit": 0}

        data[user_id]["credit"] += amount
        save_data(data)

        await update.message.reply_text("✅ Credit Added!")

    except:
        await update.message.reply_text("Usage: /add user_id amount")

# ---------------- APP ----------------

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("add", add))

app.run_polling()
