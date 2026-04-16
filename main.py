import os
import re
import json
import time
from pptx import Presentation

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = "7906677916"   # ⚠️ apna Telegram ID daalo
ADMIN_PASSWORD = "sk72940"

DB_FILE = "users.json"

# ===== DATABASE =====
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = load_db()
user_db = db["users"]

# ===== USER INIT =====
def init_user(user_id):
    if user_id not in user_db:
        user_db[user_id] = {
            "credits": 5,
            "history": []
        }
        save_db()

# ===== MEMORY =====
user_data_store = {}
admin_sessions = {}

# ===== TEXT PROCESS =====
def process_text(text):
    lines = text.split("\n")
    return "\n\n".join([
        f"Question: {l}\nA) ...\nB) ...\nC) ...\nD) ..."
        for l in lines if len(l.strip()) > 5
    ])

def split_questions(text):
    parts = re.split(r"Question:", text)
    return [p.strip() for p in parts if p.strip()]

# ===== PPT =====
def create_ppt(questions, filename):
    prs = Presentation()

    for i, q in enumerate(questions, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        lines = q.split("\n")

        slide.shapes.title.text = f"{i}. {lines[0]}"
        slide.placeholders[1].text = "\n".join(lines[1:])

    prs.save(filename)
    return filename

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    init_user(user_id)

    credits = user_db[user_id]["credits"]

    user_data_store.setdefault(user_id, "")

    await update.message.reply_text(
        f"👋 Welcome!\n\n💰 Credits: {credits}\n\nSend text → then type 'make'"
    )

# ===== ADMIN =====
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    admin_sessions[user_id] = {"step": "password"}
    await update.message.reply_text("Enter Password:")

# ===== MAIN =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text or ""

    init_user(user_id)
    user_data_store.setdefault(user_id, "")

    # ===== ADMIN FLOW =====
    if user_id in admin_sessions:
        session = admin_sessions[user_id]

        if session["step"] == "password":
            if text == ADMIN_PASSWORD:
                session["step"] = "panel"
                await update.message.reply_text(
                    "Admin Panel:\nadd / view / exit"
                )
            else:
                await update.message.reply_text("Wrong password")
            return

        elif session["step"] == "panel":
            if text == "add":
                session["step"] = "user_id"
                await update.message.reply_text("Send User ID:")
                return

            elif text == "view":
                msg = "\n".join([
                    f"{uid} → {data['credits']}"
                    for uid, data in user_db.items()
                ]) or "No users"
                await update.message.reply_text(msg)
                return

            elif text == "exit":
                del admin_sessions[user_id]
                await update.message.reply_text("Exited")
                return

        elif session["step"] == "user_id":
            session["target"] = text
            session["step"] = "amount"
            await update.message.reply_text("Credits amount:")
            return

        elif session["step"] == "amount":
            target = session["target"]

            if target not in user_db:
                user_db[target] = {"credits": 0, "history": []}

            user_db[target]["credits"] += int(text)
            save_db()

            await update.message.reply_text("✅ Credits added")
            session["step"] = "panel"
            return

    # ===== MAKE PPT =====
    if text.lower() == "make":
        data = user_data_store[user_id]

        if not data.strip():
            await update.message.reply_text("Send text first")
            return

        questions = split_questions(process_text(data))
        slides = len(questions)

        credits = user_db[user_id]["credits"]

        if credits < slides:
            await update.message.reply_text(
                f"❌ Not enough credits\nNeed: {slides}, You have: {credits}"
            )
            return

        user_db[user_id]["credits"] -= slides

        ppt = create_ppt(questions, "output.pptx")

        user_db[user_id]["history"].append({
            "slides": slides,
            "time": time.strftime("%Y-%m-%d %H:%M")
        })

        save_db()

        await update.message.reply_document(open(ppt, "rb"))

        user_data_store[user_id] = ""
        return

    # ===== SAVE TEXT =====
    if text:
        user_data_store[user_id] += text + "\n"

    await update.message.reply_text("Saved. Type 'make'")

# ===== RUN =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_cmd))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("✅ Bot Running...")
app.run_polling()
