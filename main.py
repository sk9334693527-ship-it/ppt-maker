import os
import re
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ================= CLEAN TEXT =================
def clean_text(text):
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"`", "", text)
    text = re.sub(r"Explanation.*", "", text, flags=re.DOTALL)
    return text.strip()

# ================= MATH FORMAT =================
def format_math(text):
    # sqrt(x) → √x
    text = re.sub(r"sqrt\((.*?)\)", r"√\1", text)

    # powers
    text = re.sub(r"(\d+)\^2", r"\1²", text)
    text = re.sub(r"(\d+)\^3", r"\1³", text)

    # fraction slash better
    text = text.replace("/", "⁄")

    return text

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send MCQ ya topic (Math / Science)\nMain PPT bana dunga 🎯"
    )

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ PPT bana raha hu...")

    prompt = f"""
{update.message.text}

STRICT RULES:
- Only MCQ
- No explanation
- No markdown
- Format:

Question
A)
B)
C)
D)

Math rules:
Use sqrt() and fractions like 3/4
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

            # Background
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
            p.font.color.rgb = RGBColor(255, 255, 0)

            # Options
            for l in lines[1:]:
                p = tf.add_paragraph()
                p.text = l
                p.font.size = Pt(26)
                p.font.color.rgb = RGBColor(255, 255, 255)

        file_name = "final.pptx"
        prs.save(file_name)

        with open(file_name, "rb") as f:
            await update.message.reply_document(InputFile(f))

        os.remove(file_name)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ================= MAIN =================
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
