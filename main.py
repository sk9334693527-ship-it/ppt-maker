import os
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from openai import OpenAI
import google.generativeai as genai

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ===== MEMORY =====
user_data_store = {}

# ===== AI FUNCTIONS =====
def try_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return res.text
    except:
        return None


def try_openai(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content
    except:
        return None


# ===== TEXT PROCESS =====
def process_text(text):
    prompt = f"Convert into MCQ format:\n\n{text}"

    res = try_gemini(prompt)
    if res:
        return res

    res = try_openai(prompt)
    if res:
        return res

    # fallback
    lines = text.split("\n")
    return "\n\n".join([
        f"Question: {l}\nA) ...\nB) ...\nC) ...\nD) ..."
        for l in lines if len(l.strip()) > 5
    ])


def split_questions(text):
    parts = re.split(r"Question:", text)
    return [p.strip() for p in parts if p.strip()]


# ===== PPT CREATE =====
def create_ppt(questions, filename):
    prs = Presentation()

    for i, q in enumerate(questions, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])

        lines = q.split("\n")
        title = slide.shapes.title
        content = slide.placeholders[1]

        title.text = f"{i}. {lines[0]}"
        content.text = "\n".join(lines[1:])

    prs.save(filename)
    return filename


# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    user_data_store.setdefault(user_id, "")

    await update.message.reply_text(
        "👋 Send text and then type 'make' to generate PPT"
    )


# ===== MAIN HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text or ""

    user_data_store.setdefault(user_id, "")

    if text.lower() == "make":
        data = user_data_store[user_id]

        if not data.strip():
            await update.message.reply_text("Send some text first")
            return

        await update.message.reply_text("Processing...")

        formatted = process_text(data)
        questions = split_questions(formatted)

        file = create_ppt(questions, "output.pptx")

        await update.message.reply_document(open(file, "rb"))

        user_data_store[user_id] = ""
        return

    # store text
    if text:
        user_data_store[user_id] += text + "\n"

    await update.message.reply_text("Saved. Send more or type 'make'")


# ===== RUN =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("✅ Bot Running...")
app.run_polling()
