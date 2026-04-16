import os
import re
import time
import io
import json
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pdf2image import convert_from_bytes

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

from openai import OpenAI
import google.generativeai as genai

# ---------- CONFIG ----------
TELEGRAM_TOKEN = os.getenv("8792376975:AAHkgmmlTGRVG08yogD2sJl3oHq-lStTEIo")

ADMIN_PASSWORD = "sk72940"
ADMIN_ID = 123456789  # apna ID

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

# ---------- OCR ----------
def extract_text_from_image(file_bytes):
    try:
        for key in api_db["gemini"]:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content([
                {"mime_type": "image/png", "data": file_bytes},
                "Extract text"
            ])
            return res.text
    except:
        return ""

def extract_text_from_pdf(file_bytes):
    text = ""
    try:
        images = convert_from_bytes(file_bytes)
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            text += extract_text_from_image(buf.getvalue())
    except:
        pass
    return text

# ---------- MULTI API ----------
def try_groq(prompt):
    for key in api_db["groq"]:
        try:
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content
        except Exception as e:
            print("Groq fail:", e)
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
        except Exception as e:
            print("OpenRouter fail:", e)
    return None

def try_gemini(prompt):
    for key in api_db["gemini"]:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            res = model.generate_content(prompt)
            return res.text
        except Exception as e:
            print("Gemini fail:", e)
    return None

# ---------- PROCESS ----------
def process_text(text):
    prompt = f"""
Convert into MCQ format:

{text}
"""

    res = try_groq(prompt)
    if res:
        print("Used GROQ")
        return res

    res = try_openrouter(prompt)
    if res:
        print("Used OPENROUTER")
        return res

    res = try_gemini(prompt)
    if res:
        print("Used GEMINI")
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
            Inches(2.35),
            Inches(1.5),
            Inches(8.63),
            Inches(2.56)
        )

        tf = textbox.text_frame
        tf.clear()

        p = tf.paragraphs[0]
        p.text = f"{i:02d}. {lines[0]}"
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 0)
        p.alignment = PP_ALIGN.LEFT

        for line in lines[1:]:
            p = tf.add_paragraph()
            p.text = line
            p.font.size = Pt(24)
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.LEFT

    prs.save(filename)
    return filename

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    name = update.message.from_user.first_name

    init_user(user_id)

    user_data_store[user_id] = {"data": ""}

    await update.message.reply_text(
        f"👋 Welcome {name}\n\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Credits: {user_db[user_id]['credits']}\n\n"
        "Send question / PDF / Image\nThen type: make\n\n"
        "💰 Credits ke liye call kare: 9876543210"
    )

# ---------- ADMIN ----------
admin_sessions = {}
user_data_store = {}

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_sessions[str(update.message.chat_id)] = {"step": "password"}
    await update.message.reply_text("Password:")

# ---------- MAIN ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text if update.message.text else ""

    init_user(user_id)

    # ADMIN FLOW
    if user_id in admin_sessions:
        session = admin_sessions[user_id]

        if session["step"] == "password":
            if text == ADMIN_PASSWORD:
                session["step"] = "panel"
                await update.message.reply_text(
                    "Admin Panel\n"
                    "open / addgroq / addopenrouter / addgemini / viewapi / exit"
                )
            return

        elif session["step"] == "panel":
            if text == "open":
                session["step"] = "open"
                await update.message.reply_text("User ID:")
                return

            elif text == "addgroq":
                session["step"] = "add_groq"
                await update.message.reply_text("Send Groq API key")
                return

            elif text == "addopenrouter":
                session["step"] = "add_or"
                await update.message.reply_text("Send OpenRouter key")
                return

            elif text == "addgemini":
                session["step"] = "add_gemini"
                await update.message.reply_text("Send Gemini key")
                return

            elif text == "viewapi":
                msg = f"Groq: {len(api_db['groq'])}\nOpenRouter: {len(api_db['openrouter'])}\nGemini: {len(api_db['gemini'])}"
                await update.message.reply_text(msg)
                return

            elif text == "exit":
                del admin_sessions[user_id]
                return

        elif session["step"] == "add_groq":
            api_db["groq"].append(text)
            save_db()
            await update.message.reply_text("Groq added")
            session["step"] = "panel"
            return

        elif session["step"] == "add_or":
            api_db["openrouter"].append(text)
            save_db()
            await update.message.reply_text("OpenRouter added")
            session["step"] = "panel"
            return

        elif session["step"] == "add_gemini":
            api_db["gemini"].append(text)
            save_db()
            await update.message.reply_text("Gemini added")
            session["step"] = "panel"
            return

        elif session["step"] == "open":
            session["target"] = text
            session["step"] = "user"
            u = user_db.get(text, {"credits": 0})
            await update.message.reply_text(
                f"Credits: {u['credits']}\nadd / unlimited / history"
            )
            return

        elif session["step"] == "user":
            if text == "add":
                session["step"] = "add"
                await update.message.reply_text("Credits?")
                return

            elif text == "unlimited":
                session["step"] = "unlimited_type"
                await update.message.reply_text("Type: day / month")
                return

            elif text == "history":
                h = user_db[session["target"]]["history"]
                msg = "\n".join([f"{x['time']} → {x['slides']}" for x in h]) or "No history"
                await update.message.reply_text(msg)
                return

        elif session["step"] == "add":
            user_db[session["target"]]["credits"] += int(text)
            save_db()
            await update.message.reply_text("Added")
            session["step"] = "panel"
            return

        elif session["step"] == "unlimited_type":
            session["type"] = text
            session["step"] = "unlimited_duration"
            await update.message.reply_text("Kitne?")
            return

        elif session["step"] == "unlimited_duration":
            val = int(text)
            target = session["target"]

            if session["type"] == "day":
                user_db[target]["unlimited_until"] = time.time() + val*86400
            else:
                user_db[target]["unlimited_until"] = time.time() + val*30*86400

            save_db()
            await update.message.reply_text("Unlimited set")
            session["step"] = "panel"
            return

    # USER FLOW
    if text.lower() == "make":
        data = user_data_store.get(user_id, {}).get("data", "")

        if not data.strip():
            await update.message.reply_text("Send data first")
            return

        await update.message.reply_text("Processing...")

        formatted = process_text(data)
        questions = split_questions(formatted)

        slides = len(questions)
        user = user_db[user_id]

        if time.time() < user["unlimited_until"]:
            pass
        elif user["credits"] >= slides:
            user["credits"] -= slides
        else:
            await update.message.reply_text("Not enough credits")
            return

        ppt = create_ppt(questions, "output.pptx")

        user_db[user_id]["history"].append({
            "slides": slides,
            "time": time.strftime("%Y-%m-%d %H:%M")
        })

        save_db()

        await update.message.reply_document(open(ppt, "rb"))

        user_data_store[user_id] = {"data": ""}
        return

    # INPUT
    if update.message.text:
        user_data_store.setdefault(user_id, {"data": ""})
        user_data_store[user_id]["data"] += text + "\n"

    elif update.message.photo:
        photo = await update.message.photo[-1].get_file()
        file_bytes = await photo.download_as_bytearray()
        user_data_store.setdefault(user_id, {"data": ""})
        user_data_store[user_id]["data"] += extract_text_from_image(file_bytes)

    elif update.message.document:
        doc = await update.message.document.get_file()
        file_bytes = await doc.download_as_bytearray()
        if update.message.document.mime_type == "application/pdf":
            user_data_store.setdefault(user_id, {"data": ""})
            user_data_store[user_id]["data"] += extract_text_from_pdf(file_bytes)

    await update.message.reply_text("Saved. Send more or type make")


# ---------- RUN ----------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_cmd))
app.add_handler(MessageHandler(filters.ALL, handle_message))

print("Bot Running...")
app.run_polling()
