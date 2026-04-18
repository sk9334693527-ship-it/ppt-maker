import os
import asyncio
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def format_math_text(text):
    replacements = {
        "²": "^2",
        "³": "^3",
        "√": "sqrt",
        "×": "x",
        "÷": "/"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send MCQ or topic. I will make PPT 🎯")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Processing...")

    prompt = f"""
{update.message.text}

Make MCQ:
Question
A)
B)
C)
D)

Use ^ for power and sqrt() for root.
"""

    try:
        response = model.generate_content(prompt)
        data = response.text

        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        for q in data.split("\n\n"):
            lines = [format_math_text(x.strip()) for x in q.split("\n") if x.strip()]
            if not lines:
                continue

            slide = prs.slides.add_slide(prs.slide_layouts[6])

            bg = slide.background.fill
            bg.solid()
            bg.fore_color.rgb = RGBColor(0, 0, 0)

            box = slide.shapes.add_textbox(Inches(2), Inches(1), Inches(10), Inches(5))
            tf = box.text_frame

            p = tf.paragraphs[0]
            p.text = lines[0]
            p.font.size = Pt(32)
            p.font.color.rgb = RGBColor(255,255,0)

            for l in lines[1:]:
                p = tf.add_paragraph()
                p.text = l
                p.font.size = Pt(24)
                p.font.color.rgb = RGBColor(255,255,255)

        file = "out.pptx"
        prs.save(file)

        with open(file, "rb") as f:
            await update.message.reply_document(InputFile(f))

        os.remove(file)

    except Exception as e:
        await update.message.reply_text(str(e))

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    app.run_polling()

if __name__ == "__main__":
    main()
