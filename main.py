import os
import re
import google.generativeai as genai
from PIL import Image
import pytesseract

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

# ================= CLEAN =================
def clean_text(text):
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"`", "", text)
    text = re.sub(r"Explanation.*", "", text, flags=re.DOTALL)
    return text.strip()

# ================= MATH =================
def format_math(text):
    text = re.sub(r"sqrt\((.*?)\)", r"√\1", text)
    text = re.sub(r"(\d+)\^2", r"\1²", text)
    text = re.sub(r"(\d+)\^3", r"\1³", text)
    text = text.replace("/", "⁄")
    return text

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Image bhejo ya text bhejo\nMain MCQ PPT bana dunga 🎯"
    )

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_input(update, context, update.message.text)

# ================= IMAGE HANDLER =================
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Image process ho raha hai...")

    photo = update.message.photo[-1]
    file = await photo.get_file()

    file_path = "input.jpg"
    await file.download_to_drive(file_path)

    # OCR
    img = Image.open(file_path)
    extracted_text = pytesseract.image_to_string(img)

    os.remove(file_path)

    await process_input(update, context, extracted_text)

# ================= MAIN PROCESS =================
async def process_input(update, context, user_text):
    await update.message.reply_text("⏳ MCQ bana raha hu...")

    prompt = f"""
Niche diye gaye text me se sirf MCQ questions nikalo.

RULES:
- Sirf MCQ do
- No explanation
- Format:

Question
A)
B)
C)
D)

TEXT:
{user_text}
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

            p = tf.paragraphs[0]
            p.text = lines[0]
            p.font.size = Pt(32)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 0)

            for l in lines[1:]:
                p = tf.add_paragraph()
                p.text = l
                p.font.size = Pt(26)
                p.font.color.rgb = RGBColor(255, 255, 255)

        file_name = "mcq_output.pptx"
        prs.save(file_name)

        with open(file_name, "rb") as f:
            await update.message.reply_document(InputFile(f))

        os.remove(file_name)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # image
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    print("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
