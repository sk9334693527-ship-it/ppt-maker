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
# 🔐 CONFIG
# =========================
BOT_TOKEN = "123456789:AAHkjsd98sdf98sdf98sdf9sdf"

ADMIN_ID = 123456789
PASSWORD = "YOUR_PASSWORD"
NUMBER = "YOUR_NUMBER"

GEMINI_API_KEYS = [
    "GEMINI1_API",
    "GEMINI2_API",
    "GEMINI3_API"
]

DATA_FILE = "data.json"

# OCR PATH (Windows only)
# Linux/Render/Railway users: install tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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
    key = random.choice(GEMINI_API_KEYS)
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash")

def call_ai(prompt):
    try:
        model = get_model()
        res = model.generate_content(prompt)
        return res.text
    except:
        return "AI ERROR"

# =========================
# 📄 IMAGE OCR (FIXED - NO CV2)
# =========================
def image_to_text(path):
    img = Image.open(path)
    text = pytesseract.image_to_string(img)
    return text

# =========================
# 📄 PDF TO TEXT
# =========================
def pdf_to_text(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

# =========================
# 🧠 AI PROMPT ENGINE
# =========================
def build_prompt(text, bilingual=False):
    if bilingual:
        return f"""
Convert into MCQ PPT format.

RULES:
- Hindi + English both
- One question per slide
- Format:

Q:
Hindi line
English line
A)
B)
C)
D)

TEXT:
{text}
"""
    else:
        return f"""
Convert into MCQ PPT format.

RULES:
- Only English
- One question per slide
- Format:

Q:
A)
B)
C)
D)

TEXT:
{text}
"""

# =========================
# 🎞 PPT GENERATOR
# =========================
def create_ppt(slides, filename):
    prs = Presentation()

    for s in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Question"
        slide.placeholders[1].text = s

        for p in slide.placeholders[1].text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(18)

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
/topic
/background
/dbackground
/admin

📞 {NUMBER}
""")

# =========================
# OBJECTIVE MODE
# =========================
async def objective(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send text / image / PDF → English MCQ PPT")

async def objective2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send → Hindi + English MCQ PPT")

# =========================
# BACKGROUND
# =========================
async def background(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Send background PPT file")

async def dbackground(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    data[uid]["background"] = False
    save_data(data)
    await update.message.reply_text("❌ Background removed")

# =========================
# ADMIN
# =========================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Send password:")

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == PASSWORD and update.message.from_user.id == ADMIN_ID:
        await update.message.reply_text("""
✅ ADMIN PANEL:
/add
/user
/history
/credit
""")
    else:
        await update.message.reply_text("❌ Not allowed")

# =========================
# 🧠 MAIN ENGINE (FULL AI FLOW)
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    init_user(user)
    uid = str(user.id)

    if data[uid]["credits"] <= 0:
        await update.message.reply_text("❌ No credits left")
        return

    text = ""

    # TEXT
    if update.message.text:
        text = update.message.text

    # IMAGE
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        path = f"{uid}.jpg"
        await file.download_to_drive(path)
        text = image_to_text(path)

    # PDF / FILE
    elif update.message.document:
        file = await update.message.document.get_file()
        path = f"{uid}_file"
        await file.download_to_drive(path)

        if path.lower().endswith(".pdf"):
            text = pdf_to_text(path)
        else:
            text = image_to_text(path)

    # AI PROCESS
    prompt = build_prompt(text, bilingual=False)
    ai_text = call_ai(prompt)

    slides = [s.strip() for s in ai_text.split("\n\n") if s.strip()]

    ppt_file = f"{uid}.pptx"
    create_ppt(slides, ppt_file)

    # CREDIT SYSTEM
    data[uid]["credits"] -= len(slides)
    data[uid]["history"].append({
        "time": str(datetime.now()),
        "slides": len(slides)
    })
    save_data(data)

    await update.message.reply_document(InputFile(ppt_file))

# =========================
# 🚀 MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("objective", objective))
    app.add_handler(CommandHandler("objective2", objective2))
    app.add_handler(CommandHandler("background", background))
    app.add_handler(CommandHandler("dbackground", dbackground))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(MessageHandler(filters.ALL, handle))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
