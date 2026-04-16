import os
import re
import time
import io
import json
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

from openai import OpenAI
import google.generativeai as genai

# ---------- CONFIG ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

ADMIN_PASSWORD = "sk72940"
ADMIN_ID = "123456789"  # apna Telegram ID string me daalo

DB_FILE = "users.json"

# ---------- DATABASE ----------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "users": {},
        "apis": {
            "groq": [],
            "openrouter": [],
            "gemini": []
        }
    }

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = load_db()
user_db = db["users"]
api_db = db["apis"]

# ---------- USER INIT ----------
def init_user(user_id):
    user_id = str(user_id)
    if user_id not in user_db:
        user_db[user_id] = {
            "credits": 0,
            "unlimited_until": 0,
            "history": []
        }
        save_db()

# ---------- AI ----------
def try_groq(prompt):
    for key in api_db["groq"]:
        try:
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content
        except:
            pass
    return None

def try_openrouter(prompt):
    for key in api_db["openrouter"]:
        try:
            client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
            res = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content
        except:
            pass
    return None

def try_gemini(prompt):
    for key in api_db["gemini"]:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)
            return res.text
        except:
            pass
    return None

# ---------- PROCESS ----------
def process_text(text):
    prompt = f"Convert into MCQ format:\n\n{text}"

    res = try_groq(prompt)
    if res:
        return res

    res = try_openrouter(prompt)
    if res:
        return res

    res = try_gemini(prompt)
    if res:
        return res

    # fallback
    lines = text.split("\n")
    return "\n\n".join([
        f"Question: {l}\nA) ...\nB) ...\nC) ...\nD) ..."
        for l in lines if len(l.strip()) > 5
    ])

def split_questions(text):
    parts = re.split(r'Question:', text)
    return [p.strip() for p in parts if p.strip()]

# ---------- PPT ----------
def create_ppt(questions, filename):
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    for i, q in enumerate(questions, start=1):
        lines = [l.strip() for l in q.split("\n") if l.strip()]
        if not lines:
            continue

        slide = prs.slides.add_slide(blank_layout)

        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0, 0, 0)

        textbox = slide.shapes.add_textbox(
            Inches(2.3),
            Inches(1.5),
            Inches(8.6),
            Inches(3)
        )

        tf = textbox.text_frame
        tf.clear()

        p = tf.paragraphs[0]
        p.text = f"{i:02d}. {lines[0]}"
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 0)

        for line in lines[1:]:
            p = tf.add_paragraph()
            p.text = line
            p.font.size = Pt(24)
            p.font.color.rgb = RGBColor(255, 255, 255)

    prs.save(filename)
    return filename

# ---------- GLOBAL ----------
admin_sessions = {}
user_data_store = {}

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    name = update.message.from_user.first_name

    init_user(user_id)
    user_data_store.setdefault(user_id, {"data": ""})

    await update.message.reply_text(
        f"👋 Welcome {name}\nSend text then type 'make'"
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != ADMIN_ID:
        await update.message.reply_text("Not allowed")
        return

    admin_sessions[str(update.message.chat_id)] = {"step": "password"}
    await update.message.reply_text("Password:")

# ---------- MAIN ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text if update.message.text else ""

    init_user(user_id)
    user_data_store.setdefault(user_id, {"data": ""})

    # ADMIN LOGIN
    if user_id in admin_sessions:
        if admin_sessions[user_id]["step"] == "password":
            if text == ADMIN_PASSWORD:
                await update.message.reply_text("Admin panel active")
                admin_sessions.pop(user_id)
            return

    # MAKE PPT
    if text.lower() == "make":
        data = user_data_store[user_id]["data"]

        if not data.strip():
            await update.message.reply_text("Send data first")
            return

        await update.message.reply_text("Processing...")

        formatted = process_text(data)
        questions = split_questions(formatted)

        ppt = create_ppt(questions, "output.pptx")

        await update.message.reply_document(open(ppt, "rb"))

        user_data_store[user_id] = {"data": ""}
        return

    # SAVE TEXT
    if text:
        user_data_store[user_id]["data"] += text + "\n"

    await update.message.reply_text("Saved. Send more or type make")

# ---------- RUN ----------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_cmd))
app.add_handler(MessageHandler(filters.ALL, handle_message))

print("Bot Running...")
app.run_polling()
