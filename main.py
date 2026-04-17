import os
from supabase import create_client
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    res = supabase.table("user").select("*").eq("id", str(user.id)).execute()

    if not res.data:
        supabase.table("user").insert({
            "id": str(user.id),
            "name": user.full_name,
            "credit": 0,
            "expire_at": "0"
        }).execute()
        credit = 0
    else:
        credit = res.data[0]["credit"]

    await update.message.reply_text(
        f"👋 Welcome {user.full_name}\n💰 Credit: {credit}"
    )

# ---------------- ADMIN ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id != ADMIN_ID:
        return

    if text.startswith("/add"):
        parts = text.split()

        if len(parts) < 3:
            await update.message.reply_text("Use: /add user_id credit")
            return

        target = parts[1]
        amount = int(parts[2])

        res = supabase.table("user").select("*").eq("id", target).execute()

        if res.data:
            new_credit = res.data[0]["credit"] + amount

            supabase.table("user").update({
                "credit": new_credit
            }).eq("id", target).execute()

            await update.message.reply_text("✅ Credit added")
        else:
            await update.message.reply_text("❌ User not found")

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
