import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from supabase import create_client

# ---------------- ENV ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase ENV missing")
    exit()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY.strip())

admin_logged_in = set()


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    res = supabase.table("users").select("*").eq("user_id", str(user.id)).execute()

    if not res.data:
        supabase.table("users").insert({
            "user_id": str(user.id),
            "name": user.full_name,
            "credit": 0,
            "expiry": None
        }).execute()
        credit = 0
    else:
        credit = res.data[0]["credit"]

    await update.message.reply_text(
        f"👋 Welcome {user.full_name}\n💳 Credit: {credit}"
    )


# ---------------- ADMIN ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Send admin password")


# ---------------- MESSAGE HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # ADMIN LOGIN
    if text == ADMIN_PASSWORD and user_id == ADMIN_ID:
        admin_logged_in.add(user_id)
        await update.message.reply_text("✅ Admin Login Successful")
        return

    # ADMIN COMMAND
    if text.startswith("/add") and user_id in admin_logged_in:
        try:
            _, target_id, mode, value = text.split()

            res = supabase.table("users").select("*").eq("user_id", target_id).execute()

            if not res.data:
                await update.message.reply_text("❌ User not found")
                return

            user = res.data[0]

            # CREDIT ADD
            if mode == "credit":
                new_credit = int(user["credit"]) + int(value)

                supabase.table("users").update({
                    "credit": new_credit
                }).eq("user_id", target_id).execute()

                await update.message.reply_text(f"💰 Credit Added: {value}")

            # DAYS ADD
            elif mode == "day":
                days = int(value)
                expiry = datetime.utcnow() + timedelta(days=days)

                supabase.table("users").update({
                    "expiry": expiry.isoformat()
                }).eq("user_id", target_id).execute()

                await update.message.reply_text(f"⏳ Days Added: {days}")

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")


# ---------------- APP ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
