import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ====== ENV ======
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

DATA_FILE = "data.json"

# ====== DATA ======
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ====== ADMIN SESSION ======
admin_state = {}

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in data:
        data[uid] = {
            "credit": 0,
            "days": 0,
            "name": user.first_name
        }
        save_data(data)

    u = data[uid]

    await update.message.reply_text(
        f"👋 Welcome {user.first_name}\n\n"
        f"💰 Credit: {u['credit']}\n"
        f"📅 Days: {u['days']}"
    )

# ====== ADMIN ======
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    await update.message.reply_text("🔐 Enter Admin Password:")
    admin_state[uid] = "waiting_password"

# ====== MESSAGE HANDLER ======
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text

    # ===== ADMIN LOGIN =====
    if uid in admin_state and admin_state[uid] == "waiting_password":
        if text == ADMIN_PASSWORD:
            admin_state[uid] = "logged_in"
            await update.message.reply_text("✅ Welcome Admin\n\nUse /add")
        else:
            await update.message.reply_text("❌ Wrong password")
        return

    # ===== ADD COMMAND FLOW =====
    if uid in admin_state and admin_state[uid] == "add_target":
        admin_state[uid] = {"step": "type", "target": text}
        await update.message.reply_text("👉 Type: credit or day")
        return

    if isinstance(admin_state.get(uid), dict):
        state = admin_state[uid]

        # TYPE SELECT
        if state["step"] == "type":
            if text.lower() == "credit":
                state["mode"] = "credit"
                state["step"] = "amount"
                await update.message.reply_text("💰 Kitna credit add karna hai?")
                return

            if text.lower() == "day":
                state["mode"] = "day"
                state["step"] = "amount"
                await update.message.reply_text("📅 Kitne din add karna hai?")
                return

        # AMOUNT
        if state["step"] == "amount":
            target = state["target"]

            if target not in data:
                data[target] = {"credit": 0, "days": 0, "name": "user"}

            if state["mode"] == "credit":
                data[target]["credit"] += int(text)
            else:
                data[target]["days"] += int(text)

            save_data(data)
            admin_state[uid] = "logged_in"

            await update.message.reply_text("✅ Updated Successfully")
            return

# ===== /ADD =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid != str(ADMIN_ID):
        await update.message.reply_text("❌ Not allowed")
        return

    await update.message.reply_text("👤 User ID bhejo jisko add karna hai")
    admin_state[uid] = "add_target"

# ===== APP =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
