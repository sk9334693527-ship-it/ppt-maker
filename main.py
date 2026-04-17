import os
import json
import io
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from pptx import Presentation
from pptx.util import Inches, Pt

# ---------------- ENV ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ---------------- LOCAL DB ----------------
DB_FILE = "users.json"


def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def get_user(user_id: str):
    db = load_db()
    return db.get(user_id)


def upsert_user(user_id: str, data: dict):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"credit": 0, "expiry": None, "name": ""}
    db[user_id].update(data)
    save_db(db)


# ---------------- PPT GENERATION ----------------
def create_ppt(text: str) -> io.BytesIO:
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]  # Title and Content layout

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    # Group into slides: first line = title, next lines = bullet points (up to 5 per slide)
    BULLETS_PER_SLIDE = 5
    title = lines[0] if lines else "Presentation"
    body_lines = lines[1:] if len(lines) > 1 else []

    # Split body into chunks for multiple slides
    chunks = [body_lines[i:i + BULLETS_PER_SLIDE] for i in range(0, max(len(body_lines), 1), BULLETS_PER_SLIDE)]
    if not chunks:
        chunks = [[]]

    for idx, chunk in enumerate(chunks):
        slide = prs.slides.add_slide(slide_layout)
        slide_title = slide.shapes.title
        slide_body = slide.placeholders[1]

        slide_title.text = title if idx == 0 else f"{title} (cont.)"
        tf = slide_body.text_frame
        tf.clear()

        for i, bullet in enumerate(chunk):
            if i == 0:
                tf.paragraphs[0].text = bullet
                tf.paragraphs[0].font.size = Pt(18)
            else:
                p = tf.add_paragraph()
                p.text = bullet
                p.font.size = Pt(18)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ---------------- STATE ----------------
admin_logged_in = set()
awaiting_ppt_text = set()


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    record = get_user(uid)
    if not record:
        upsert_user(uid, {"name": user.full_name, "credit": 0, "expiry": None})
        credit = 0
    else:
        credit = record.get("credit", 0)

    await update.message.reply_text(
        f"👋 Welcome {user.full_name}!\n"
        f"💳 Credits: {credit}\n\n"
        f"Send /makeppt to create a PowerPoint presentation."
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Send admin password:")


async def makeppt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    record = get_user(uid)
    credit = record.get("credit", 0) if record else 0

    if credit <= 0:
        await update.message.reply_text("❌ You have no credits. Contact admin to get credits.")
        return

    awaiting_ppt_text.add(uid)
    await update.message.reply_text(
        "📝 Send me the text for your presentation.\n"
        "• First line will be the slide title\n"
        "• Each following line becomes a bullet point\n"
        "• Long content is split across multiple slides automatically"
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    uid = str(user_id)

    # ADMIN LOGIN
    if text == ADMIN_PASSWORD and user_id == ADMIN_ID:
        admin_logged_in.add(user_id)
        await update.message.reply_text(
            "✅ Admin Login Successful\n\n"
            "Commands:\n"
            "/add <user_id> credit <amount>\n"
            "/add <user_id> day <days>"
        )
        return

    # ADMIN: /add command
    if text.startswith("/add") and user_id in admin_logged_in:
        try:
            parts = text.split()
            if len(parts) != 4:
                raise ValueError("Usage: /add <user_id> credit|day <value>")

            _, target_id, mode, value = parts
            record = get_user(target_id)

            if not record:
                await update.message.reply_text("❌ User not found. They must /start the bot first.")
                return

            if mode == "credit":
                new_credit = int(record.get("credit", 0)) + int(value)
                upsert_user(target_id, {"credit": new_credit})
                await update.message.reply_text(f"💰 Added {value} credit(s) to {target_id}. New total: {new_credit}")

            elif mode == "day":
                days = int(value)
                current_expiry = record.get("expiry")
                if current_expiry:
                    base = datetime.fromisoformat(current_expiry)
                    if base < datetime.utcnow():
                        base = datetime.utcnow()
                else:
                    base = datetime.utcnow()
                new_expiry = (base + timedelta(days=days)).isoformat()
                upsert_user(target_id, {"expiry": new_expiry})
                await update.message.reply_text(f"⏳ Added {days} day(s) to {target_id}. Expires: {new_expiry}")

            else:
                await update.message.reply_text("❌ Unknown mode. Use 'credit' or 'day'.")

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
        return

    # PPT TEXT INPUT
    if uid in awaiting_ppt_text:
        awaiting_ppt_text.discard(uid)
        record = get_user(uid)
        credit = record.get("credit", 0) if record else 0

        if credit <= 0:
            await update.message.reply_text("❌ No credits remaining.")
            return

        await update.message.reply_text("⏳ Generating your presentation...")

        try:
            ppt_buf = create_ppt(text)
            upsert_user(uid, {"credit": credit - 1})
            await update.message.reply_document(
                document=ppt_buf,
                filename="presentation.pptx",
                caption=f"✅ Here's your presentation! Credits remaining: {credit - 1}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to generate PPT: {e}")
        return

    # DEFAULT
    await update.message.reply_text(
        "ℹ️ Use /start to see your credits or /makeppt to create a presentation."
    )


# ---------------- APP ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("makeppt", makeppt))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()

