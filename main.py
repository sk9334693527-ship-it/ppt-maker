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
            "credits": 10,   # default credits
            "history": []
        }
        save_db()

# ===== MEMORY =====
user_data_store = {}

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

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    init_user(user_id)

    credits = user_db[user_id]["credits"]

    user_data_store.setdefault(user_id, "")

    await update.message.reply_text(
        f"👋 Welcome!\n\n💰 Your Credits: {credits}\n\nSend text then type 'make'"
    )

# ===== MAIN =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text or ""

    init_user(user_id)
    user_data_store.setdefault(user_id, "")

    # MAKE PPT
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
                f"❌ Not enough credits\nNeeded: {slides}, You have: {credits}"
            )
            return

        # deduct credits
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

    # SAVE TEXT
    if text:
        user_data_store[user_id] += text + "\n"

    await update.message.reply_text("Saved. Type 'make'")

# ===== RUN =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("✅ Bot Running...")
app.run_polling()
