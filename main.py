import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= ENV =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = str(os.getenv("ADMIN_ID", "0"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

DATA_FILE = "data.json"

# ================= DATA =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ================= STATE =================
state = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in data:
        data[uid] = {
            "name": user.first_name,
            "username": user.username or "",
            "credit": 0,
            "days": 0
        }
        save_data(data)

    u = data[uid]

    await update.message.reply_text(
        f"👋 Welcome {u['name']}\n"
        f"🆔 ID: {uid}\n"
        f"🔰 Username: @{u['username']}\n\n"
        f"💰 Credit: {u['credit']}\n"
        f"📅 Days: {u['days']}"
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    state[uid] = "password"
    await update.message.reply_text("🔐 Enter Admin Password:")

# ================= ADD COMMAND =================
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    state[uid] = "target"
    await update.message.reply_text("👤 User ID bhejo jisko update karna hai")

# ================= MESSAGE HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text

    # ---------- ADMIN LOGIN ----------
    if uid in state and state[uid] == "password":
        if text == ADMIN_PASSWORD:
            state[uid] = "logged"
            await update.message.reply_text("✅ Welcome Admin\n\nUse /add")
        else:
            await update.message.reply_text("❌ Wrong password")
            state.pop(uid, None)
        return

    # ---------- TARGET USER ----------
    if uid in state and state[uid] == "target":
        state[uid] = {"step": "type", "target": text}
        await update.message.reply_text("👉 Type: credit or day")
        return

    # ---------- ADD FLOW ----------
    if isinstance(state.get(uid), dict):
        s = state[uid]

        if s["step"] == "type":
            if text.lower() in ["credit", "day"]:
                s["mode"] = text.lower()
                s["step"] = "amount"
                await update.message.reply_text("💰 Kitna add karna hai?")
            else:
                await update.message.reply_text("❌ type only: credit or day")
            return

        if s["step"] == "amount":
            target = s["target"]

            if target not in data:
                data[target] = {
                    "name": "user",
                    "username": "",
                    "credit": 0,
                    "days": 0
                }

            # update logic
            if s["mode"] == "credit":
                data[target]["credit"] += int(text)
            else:
                data[target]["days"] += int(text)

            save_data(data)

            state.pop(uid, None)

            await update.message.reply_text("✅ Successfully Updated")
            return

# ================= APP =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
