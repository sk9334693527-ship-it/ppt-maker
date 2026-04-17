import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- TOKEN (Railway ENV) ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN missing in Railway Variables")

# ---------------- LOCAL DATABASE ----------------
DB_FILE = "data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(data, user_id, name):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "name": name,
            "credit": 0
        }
    return data[user_id]

# ---------------- START COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_db()
    user = update.effective_user

    u = get_user(data, user.id, user.first_name)
    save_db(data)

    await update.message.reply_text(
        f"👋 Welcome {u['name']}\n\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Credit: {u['credit']}"
    )

# ---------------- INFO COMMAND ----------------
async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_db()
    user = update.effective_user

    u = get_user(data, user.id, user.first_name)
    save_db(data)

    await update.message.reply_text(
        f"📊 USER INFO\n\n"
        f"👤 Name: {u['name']}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Credit: {u['credit']}"
    )

# ---------------- ADD CREDIT (ADMIN) ----------------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_db()

    try:
        target_id = context.args[0]
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Use: /add user_id amount")
        return

    if target_id not in data:
        data[target_id] = {"name": "User", "credit": 0}

    data[target_id]["credit"] += amount
    save_db(data)

    await update.message.reply_text(
        f"✅ Added {amount} credit\n"
        f"🆔 User: {target_id}\n"
        f"💰 Total: {data[target_id]['credit']}"
    )

# ---------------- MESSAGE HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_db()
    user = update.effective_user
    text = update.message.text

    u = get_user(data, user.id, user.first_name)

    # number = credit add
    if text.isdigit():
        u["credit"] += int(text)
        save_db(data)

        await update.message.reply_text(
            f"✅ Credit Added!\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Credit: {u['credit']}"
        )
    else:
        await update.message.reply_text(
            f"👤 {u['name']}\n"
            f"🆔 {user.id}\n"
            f"💰 Credit: {u['credit']}"
        )

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
