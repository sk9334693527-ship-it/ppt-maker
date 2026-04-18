import os
import json
import random
from datetime import datetime

import pdfplumber
from PIL import Image
import pytesseract

import google.generativeai as genai

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from pptx import Presentation
from pptx.util import Pt

# =========================
# 🔐 ADMIN STATES
# =========================
admin_waiting = set()
admin_logged = set()

# =========================
# 🔐 CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

PASSWORD = os.getenv("PASSWORD") or "1234"
PASSWORD = str(PASSWORD).strip()

NUMBER = os.getenv("NUMBER", "Not Set")

GEMINI_API_KEYS = [
    os.getenv("GEMINI_API"),
    os.getenv("GEMINI1_API"),
    os.getenv("GEMINI2_API"),
    os.getenv("GEMINI3_API")
]

DATA_FILE = "data.json"

# =========================
# 💾 DATA SYSTEM
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def init_user(user):
    uid = str(user.id)
    if uid not in data:
        data[uid] = {
            "name": user.first_name,
            "credits": 20,
            "history": [],
            "background": False
        }
        save_data(data)

# =========================
# 🤖 GEMINI AI
# =========================
def get_model():
    keys = [k for k in GEMINI_API_KEYS if k]
    if not keys:
        raise Exception("No Gemini API found")

    key = random.choice(keys)
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash")

def call_ai(prompt):
    try:
        model = get_model()
        res = model.generate_content(prompt)
        return res.text if res.text else "No content generated"
    except Exception as e:
        print("AI ERROR:", e)
        return "Error generating content"

# =========================
# 🧹 CLEAN TEXT
# =========================
def clean_text(text):
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = text.replace("\r", "")
    text = text.encode("utf-8", "ignore").decode("utf-8")
    return text.strip()

# =========================
# 🧠 PROMPT
# =========================
def build_prompt(text, bilingual=False):
    if bilingual:
        return f"""
Create MCQ slides.

Rules:
- Plain text only
- Format:
Question
A) option
B) option
C) option
D) option

Hindi + English

{text}
"""
    else:
        return f"""
Create MCQ slides.

Rules:
- Plain text only
- Format:
Question
A) option
B) option
C) option
D) option

English only

{text}
"""

# =========================
# 🎞 PPT (FINAL FIX)
# =========================
def create_ppt(slides, filename):
    prs = Presentation()

    for s in slides:
        s = clean_text(s)
        if not s:
            continue

        # blank slide
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)

        # title box
        title_box = slide.shapes.add_textbox(Pt(20), Pt(20), Pt(900), Pt(50))
        title_tf = title_box.text_frame
        title_tf.text = "Question"

        # content box
        content_box = slide.shapes.add_textbox(Pt(20), Pt(100), Pt(900), Pt(400))
        tf = content_box.text_frame

        lines = s.split("\n")

        for i, line in enumerate(lines):
            line = clean_text(line)
            if not line:
                continue

            if i == 0:
                tf.text = line
            else:
                p = tf.add_paragraph()
                p.text = line

        # font size
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(20)

    prs.save(filename)
    return filename

# =========================
# /START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    init_user(user)
    uid = str(user.id)
    d = data[uid]

    await update.message.reply_text(f"""
👤 Name: {d['name']}
🆔 ID: {uid}
💳 Credits: {d['credits']}

📌 MENU:
/objective
/objective2
/make
/admin

📞 {NUMBER}
""")

# =========================
# COMMANDS
# =========================
async def objective(update, context):
    context.user_data["mode"] = "objective"
    context.user_data["buffer"] = []
    await update.message.reply_text("Send text then /make")

async def objective2(update, context):
    context.user_data["mode"] = "objective2"
    context.user_data["buffer"] = []
    await update.message.reply_text("Send Hindi+English text then /make")

async def make(update, context):
    user = update.message.from_user
    uid = str(user.id)

    if not context.user_data.get("buffer"):
        await update.message.reply_text("No data")
        return

    text = "\n".join(context.user_data["buffer"])
    mode = context.user_data.get("mode", "objective")

    prompt = build_prompt(text, bilingual=(mode == "objective2"))
    ai_text = call_ai(prompt)

    raw = ai_text.split("\n\n")
    slides = []

    for s in raw:
        s = clean_text(s)
        if len(s) > 10:
            slides.append(s)

    if not slides:
        await update.message.reply_text("Failed to generate")
        return

    ppt = f"{uid}_{int(datetime.now().timestamp())}.pptx"
    create_ppt(slides, ppt)

    data[uid]["credits"] -= len(slides)
    save_data(data)

    context.user_data["buffer"] = []

    await update.message.reply_document(
        document=InputFile(ppt, filename=ppt)
    )

async def admin(update, context):
    uid = update.message.from_user.id
    admin_waiting.add(uid)
    await update.message.reply_text("Send password")

# =========================
# HANDLE
# =========================
async def handle(update, context):
    user = update.message.from_user
    uid = user.id
    init_user(user)

    text_msg = update.message.text.strip() if update.message.text else ""

    if uid in admin_waiting:
        if text_msg == PASSWORD and uid == ADMIN_ID:
            admin_logged.add(uid)
            await update.message.reply_text("Admin login success")
        else:
            await update.message.reply_text("Wrong password")
        admin_waiting.remove(uid)
        return

    if update.message.text and context.user_data.get("mode"):
        if update.message.text != "/make":
            context.user_data.setdefault("buffer", []).append(update.message.text)
            await update.message.reply_text("Added")
            return

    if data[str(uid)]["credits"] <= 0:
        await update.message.reply_text("No credits")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("objective", objective))
    app.add_handler(CommandHandler("objective2", objective2))
    app.add_handler(CommandHandler("make", make))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(MessageHandler(filters.ALL, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
