import os
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

# ================= MATH FIX =================
def format_math_text(text):
    replacements = {
        "²": "^2",
        "³": "^3",
        "√": "sqrt",
        "√(": "sqrt(",
        "×": "x",
        "÷": "/",
        "–": "-",
        "—": "-",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "📌 Mujhe bhejo:\n"
        "1️⃣ MCQ questions\n"
        "2️⃣ Ya topic (e.g. 'Math MCQ')\n\n"
        "Main PPT bana ke de dunga 🎯"
    )

# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    prompt = f"""
{user_text}

MCQ format me do:
Question
A)
B)
C)
D)

IMPORTANT:
- Math ko simple text me likho
- Use ^ for power (e.g. x^2)
- Use sqrt() for root (e.g. sqrt(16))
- Special symbols (², √) use mat karo
"""

    await update.message.reply_text("⏳ PPT bana raha hu...")

    try:
        # GEMINI RESPONSE
        response = model.generate_content(prompt)
        formatted = response.text

        questions = [q.strip() for q in formatted.split("\n\n") if q.strip()]

        # PPT CREATE
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        blank_layout = prs.slide_layouts[6]

        for q in questions:
            slide = prs.slides.add_slide(blank_layout)

            # Background black
            bg = slide.background
            fill = bg.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(0, 0, 0)

            # Textbox
            left = Inches(3.5)
            top = Inches(1)
            width = Inches(9.8)
            height = Inches(5.5)

            textbox = slide.shapes.add_textbox(left, top, width, height)
            tf = textbox.text_frame
            tf.clear()

            # APPLY MATH FIX HERE
            lines = [format_math_text(l.strip()) for l in q.split("\n") if l.strip()]

            if lines and lines[0].lower().startswith("question"):
                lines = lines[1:]

            if not lines:
                continue

            # Question
            p = tf.paragraphs[0]
            p.text = lines[0]
            p.font.size = Pt(32)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 0)

            # Options
            for line in lines[1:]:
                p = tf.add_paragraph()
                p.text = line
                p.font.size = Pt(26)
                p.font.color.rgb = RGBColor(255, 255, 255)

        file_name = "mcq_questions.pptx"
        prs.save(file_name)

        # SEND FILE
        with open(file_name, "rb") as f:
            await update.message.reply_document(document=InputFile(f))

        os.remove(file_name)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ================= MAIN =================
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
