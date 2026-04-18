import os
import re
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ✅ CLEAN TEXT
def clean_text(text):
    text = re.sub(r"\*\*", "", text)  # remove **
    text = re.sub(r"`", "", text)     # remove `
    text = re.sub(r"Explanation.*", "", text, flags=re.DOTALL)  # remove explanation
    return text.strip()

# ✅ MATH FIX
def format_math(text):
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
    await update.message.reply_text("Send MCQ or topic 🎯")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ PPT bana raha hu...")

    prompt = f"""
{update.message.text}

STRICT RULES:
- Only MCQ do
- No explanation
- No markdown
- Format:

Question
A)
B)
C)
D)

Math use:
^ for power
sqrt() for root
"""

    try:
        response = model.generate_content(prompt)
        data = clean_text(response.text)

        questions = [q.strip() for q in data.split("\n\n") if q.strip()]

        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        for q in questions:
            lines = [format_math(l.strip()) for l in q.split("\n") if l.strip()]

            if len(lines) < 2:
                continue

            slide = prs.slides.add_slide(prs.slide_layouts[6])

            bg = slide.background.fill
            bg.solid()
            bg.fore_color.rgb = RGBColor(0, 0, 0)

            box = slide.shapes.add_textbox(Inches(2), Inches(1), Inches(10), Inches(5))
            tf = box.text_frame

            # Question
            p = tf.paragraphs[0]
            p.text = lines[0]
            p.font.size = Pt(32)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255,255,0)

            # Options
            for l in lines[1:]:
                p = tf.add_paragraph()
                p.text = l
                p.font.size = Pt(24)
                p.font.color.rgb = RGBColor(255,255,255)

        file = "final.pptx"
        prs.save(file)

        with open(file, "rb") as f:
            await update.message.reply_document(InputFile(f))

        os.remove(file)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
